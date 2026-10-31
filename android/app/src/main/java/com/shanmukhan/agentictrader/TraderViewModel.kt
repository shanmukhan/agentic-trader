package com.shanmukhan.agentictrader

import android.app.Application
import android.os.SystemClock
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import org.json.JSONArray
import org.json.JSONObject
import java.net.URLEncoder
import java.time.Instant

class TraderViewModel @JvmOverloads constructor(application: Application, injectedTransport: Transport? = null) : AndroidViewModel(application) {
    private val vault = SecureVault(application)
    private val preferences = application.getSharedPreferences("recovery", 0)
    private val transport: Transport = injectedTransport ?: if (BuildConfig.DEMO) DemoTransport(application) else HttpsTransport()
    private fun recoveryPage(): Page = runCatching { Page.valueOf(preferences.getString("inspect_page", "HISTORY")!!) }.getOrDefault(Page.HISTORY)
    private fun instructionPage(path: String) = when {
        path.startsWith("/api/desk/watchlist") || path.startsWith("/api/desk/safety") -> Page.WATCHLIST
        path.startsWith("/api/investment-policies") -> Page.POLICY
        path.startsWith("/api/backtests") -> Page.BACKTEST
        path.startsWith("/api/desk/preparation") -> Page.STRATEGY
        path.startsWith("/api/setup") || path.startsWith("/api/mobile/broker") -> Page.BROKER
        path.startsWith("/api/mobile/devices") -> Page.SECURITY
        else -> Page.HISTORY
    }
    internal val api = Api(transport) { path, pending ->
        val editor = preferences.edit().putBoolean("inspect_activity", pending)
        if (pending) editor.putString("inspect_page", instructionPage(path).name)
        check(editor.commit()) { "Recovery status could not be saved. Inspect server state before another instruction." }
    }
    private val mutable = MutableStateFlow(AppState(paired = if (BuildConfig.DEMO) true else vault.paired(),
        reconcile = preferences.getBoolean("inspect_activity", false), reconcilePage = recoveryPage()))
    val state = mutable.asStateFlow()
    private var epoch = 0
    private var task: Job? = null
    private var operationSerial = 0
    private var lastTouch = SystemClock.elapsedRealtime()
    private var lastRefresh = 0L
    private var ownerAuthorization: String? = null
    private var sessionCheckDate = ""
    private var dailyAuditAttempt = ""

    init {
        if (BuildConfig.DEMO) {
            api.authorize("offline-demo")
            mutable.update { it.copy(unlocked = true) }
            work("Loading offline demonstration") { refreshSnapshot(checkDaily = false) }
        }
        viewModelScope.launch {
            while (true) {
                delay(1000)
                val value = state.value
                if (value.unlocked && !BuildConfig.DEMO &&
                    (SystemClock.elapsedRealtime() - lastTouch > 120_000 ||
                     value.expiresAt.isNotBlank() && Instant.now() >= parseInstant(value.expiresAt))) {
                    lock("Unlock again to keep your account private.")
                } else if (value.unlocked && !value.busy && value.review == null && !value.environmentDialog && value.pendingPage == null &&
                    SystemClock.elapsedRealtime() - lastRefresh >= 5000) {
                    refreshInBackground()
                }
            }
        }
    }

    fun touch() { lastTouch = SystemClock.elapsedRealtime() }
    fun alerts(enabled: Boolean) {
        preferences.edit().putBoolean("proposal_alerts", enabled).apply()
        mutable.update { it.copy(alertsEnabled = enabled, notice = if (enabled)
            "Proposal alerts are enabled while this app stays unlocked. Background push is unavailable."
            else "Proposal alerts are off. Android notification permission can be managed in system settings.") }
    }
    fun data(name: String) = state.value.data[name] ?: JSONObject()
    private fun save(name: String, value: JSONObject) { mutable.update { it.copy(data = it.data + (name to value)) } }
    fun dismissMessage() { mutable.update { it.copy(error = null, notice = null) } }
    fun reportError(text: String) { mutable.update { it.copy(error = text) } }

    private fun work(label: String, quiet: Boolean = false, action: suspend () -> Unit) {
        if (state.value.busy) return
        if (quiet && (task?.isActive == true || state.value.review != null || state.value.environmentDialog || state.value.pendingPage != null)) return
        if (!quiet) task?.cancel() // Only a quiet GET can be active while busy is false.
        val operation = ++operationSerial
        val version = epoch
        if (!quiet) mutable.update { it.copy(busy = true, progress = label, error = null) }
        task = viewModelScope.launch {
            try { action() }
            catch (_: CancellationException) { }
            catch (error: Exception) {
                if (version == epoch && operation == operationSerial) {
                    if (error is ApiFailure && error.status == 401) lock(error.message ?: "Unlock again.")
                    else {
                        val uncertain = state.value.unlocked && ((error is ApiFailure && error.uncertain) || preferences.getBoolean("inspect_activity", false))
                        val target = if (error is ApiFailure) instructionPage(error.endpoint) else recoveryPage()
                        if (uncertain) preferences.edit().putBoolean("inspect_activity", true).putString("inspect_page", target.name).apply()
                        mutable.update { it.copy(error = error.message ?: "Could not complete this request.",
                            stale = quiet || it.stale || error is ApiFailure && (error.status == 0 || error.status >= 500), reconcile = it.reconcile || uncertain,
                            reconcilePage = if (uncertain) target else it.reconcilePage,
                            formDirty = if (uncertain && target == Page.WATCHLIST) false else it.formDirty) }
                    }
                }
            } finally {
                if (version == epoch && operation == operationSerial) {
                    if (quiet) lastRefresh = SystemClock.elapsedRealtime()
                    else mutable.update { it.copy(busy = false, progress = "") }
                }
            }
        }
    }

    internal fun refreshInBackground() = work("", quiet = true) { refreshSnapshot() }
    private fun pauseQuietRead() {
        if (!state.value.busy && task?.isActive == true) { operationSerial++; task?.cancel(); task = null }
    }
    fun showEnvironment(show: Boolean) {
        if (!state.value.unlocked || state.value.busy || state.value.review != null) return
        pauseQuietRead()
        mutable.update { it.copy(environmentDialog = show) }
    }

    fun pair(owner: String, label: String, gate: BiometricGate) {
        if (BuildConfig.DEMO) return
        val cipher = try { vault.enrollmentCipher() } catch (error: Exception) {
            reportError(error.message ?: "Secure biometrics are unavailable."); return
        }
        val version = epoch
        work("Pairing your phone") {
            val credential = api.pair(owner.trim(), label.trim())
            gate.authenticate(cipher, "Protect this phone's access", { authorized ->
                if (version == epoch) work("Securing your phone") {
                    val bytes = credential.toString().toByteArray()
                    vault.save(authorized, bytes)
                    mutable.update { it.copy(paired = true) }
                    completeUnlock(credential)
                }
            }, { message -> if (version == epoch) reportError(message + " Pairing may remain registered; inspect it before retrying.") })
        }
    }

    fun unlock(gate: BiometricGate) {
        if (BuildConfig.DEMO) return
        val cipher = try { vault.decryptCipher() } catch (_: Exception) {
            reportError("Phone protection changed or the pairing cannot be read. Pair this phone again."); return
        }
        val version = epoch
        gate.authenticate(cipher, "Unlock Agentic Trader", { authorized ->
            if (version == epoch) work("Unlocking securely") {
                val bytes = vault.open(authorized)
                val credential = try { JSONObject(String(bytes, Charsets.UTF_8)) } finally { bytes.fill(0) }
                completeUnlock(credential)
            }
        }, { message -> if (version == epoch) reportError(message) })
    }

    private suspend fun completeUnlock(credential: JSONObject) {
        val session = try { api.unlock(credential) } finally { credential.remove("device_secret") }
        api.authorize(session.getString("access_token"))
        lastTouch = SystemClock.elapsedRealtime()
        mutable.update { AppState(unlocked = true, paired = true, busy = it.busy, progress = it.progress,
            reconcile = preferences.getBoolean("inspect_activity", false), reconcilePage = recoveryPage(), expiresAt = session.text("expires_at", ""),
            alertsEnabled = preferences.getBoolean("proposal_alerts", false)) }
        refreshSnapshot(checkDaily = false)
        val attempt = preferences.getString("broker_attempt", null)
        if (attempt != null) {
            val outcome = api.get("/api/mobile/broker/login/$attempt")
            if (outcome.text("state") != "waiting_for_login") preferences.edit().remove("broker_attempt").apply()
            if (outcome.text("state") == "verified" && preferences.getBoolean("resume_prepare", false)) {
                preferences.edit().remove("resume_prepare").apply()
                val journey = preferences.getBoolean("resume_journey", false)
                preferences.edit().remove("resume_journey").apply()
                mutable.update { it.copy(journeyRunning = journey) }
                prepareSteps(preferences.getString("resume_universe", "nifty50")!!, false, journey, true)
                refreshSnapshot()
            } else mutable.update { it.copy(notice = outcome.text("message")) }
        }
    }

    fun lock(message: String? = null) {
        if (BuildConfig.DEMO) return
        val oldSession = api.token
        epoch++; operationSerial++; task?.cancel(); task = null; api.lock(); ownerAuthorization = null
        sessionCheckDate = ""; dailyAuditAttempt = ""
        mutable.value = AppState(paired = vault.paired(), error = message,
            reconcile = preferences.getBoolean("inspect_activity", false), reconcilePage = recoveryPage())
        if (oldSession != null) viewModelScope.launch {
            // Best effort: local privacy never waits for network logout. Offline sessions expire.
            try { transport.request("DELETE", "/api/mobile/session", oldSession, null) }
            catch (_: Exception) { }
        }
    }
    fun forgetPhone() { if (!BuildConfig.DEMO) { lock(); vault.forget(); mutable.value = AppState(notice = "Pair this phone to restore access.") } }
    fun navigate(page: Page) {
        if (!state.value.unlocked || state.value.busy || state.value.review != null) return
        if (state.value.formDirty && page != state.value.page) { mutable.update { it.copy(pendingPage = page) }; return }
        pauseQuietRead()
        if (page != Page.SECURITY) { ownerAuthorization = null; mutable.update { it.copy(data = it.data - "ownerDevices") } }
        mutable.update { it.copy(page = page, error = null, report = null, compareReport = null) }
        val cached = when (page) {
            Page.HOME -> data("desk").has("account") && data("setup").length() > 0 && data("views").length() > 0
            Page.DISCOVER, Page.PORTFOLIO -> data("desk").has("account") && data("views").length() > 0
            Page.STRATEGY, Page.BROKER -> data("desk").has("account") && data("setup").length() > 0
            Page.PAPER, Page.MORE -> data("desk").has("account")
            else -> false
        }
        if (cached) refreshInBackground()
        else work("Loading ${page.title.lowercase()}") { refreshSnapshot() }
    }
    fun dirty(value: Boolean) { mutable.update { it.copy(formDirty = value) } }
    fun discardNavigation(discard: Boolean) {
        val page = state.value.pendingPage
        mutable.update { it.copy(pendingPage = null, formDirty = if (discard) false else it.formDirty) }
        if (discard && page != null) navigate(page)
    }
    fun direct(path: String, body: JSONObject = JSONObject(), label: String = "Checking server status") {
        if (!canAct()) return
        work(label) { api.post(path, body); refreshSnapshot(); mutable.update { it.copy(notice = "Updated. Review the saved status below.") } }
    }
    fun refresh() {
        if (state.value.page == Page.WATCHLIST && state.value.formDirty) {
            reportError("Review and save or discard your watchlist edits before refreshing."); return
        }
        work("Checking current status") { refreshSnapshot() }
    }
    fun acknowledgeReconciliation() {
        if (!state.value.stale && !state.value.busy && state.value.page == state.value.reconcilePage) {
            preferences.edit().putBoolean("inspect_activity", false).apply()
            mutable.update { it.copy(reconcile = false, notice = "Saved outcome reviewed. New instructions can be prepared.") }
        }
    }

    private suspend fun optional(path: String): JSONObject = try { api.get(path) } catch (error: ApiFailure) {
        if (error.status in listOf(404, 409)) json("unavailable" to true, "message" to error.message) else throw error
    }
    internal suspend fun refreshSnapshot(checkDaily: Boolean = true) {
        val version = epoch
        val operation = operationSerial
        val desk = api.get("/api/desk")
        val receivedAt = SystemClock.elapsedRealtime()
        if (!(desk.text("mode") in listOf("manual", "approval", "automatic") &&
            desk.text("revision").matches(Regex("[a-f0-9]{32}")) && desk.obj("account").length() > 0))
            throw ApiFailure(0, "Account response is incomplete. Recheck server status before taking action.", endpoint = "/api/desk")
        if (desk.obj("account").text("mode") != "paper")
            throw ApiFailure(0, "This app supports a paper account only. The server account environment is incompatible.", endpoint = "/api/desk")
        val snapshot = mutableMapOf("desk" to desk)
        val page = state.value.page
        if (data("environment").length() == 0) snapshot["environment"] = optional("/api/trading-environment")
        if (page in listOf(Page.HOME, Page.STRATEGY, Page.BROKER, Page.SETTINGS)) snapshot["setup"] = api.get("/api/setup")
        if (page in listOf(Page.HOME, Page.DISCOVER, Page.PORTFOLIO, Page.SETTINGS, Page.LEARN)) snapshot["views"] = api.get("/api/workspace/views")
        when (page) {
            Page.WATCHLIST -> if (!state.value.formDirty) snapshot["watchlist"] = api.get("/api/desk/watchlist")
            Page.ANALYSIS -> snapshot["analysis"] = fetchAnalysis()
            Page.PURCHASES -> snapshot["portfolio"] = optional("/api/paper/portfolio")
            Page.HISTORY -> snapshot["activity"] = api.get("/api/activity")
            Page.POLICY -> {
                val policies = api.get("/api/investment-policies"); snapshot["policies"] = policies
                val expected = preferences.getString("pending_policy_id", null)
                if (expected != null && policies.rows("drafts").any { it.text("draft_id") == expected }) {
                    preferences.edit().remove("pending_policy_id").apply(); reconcileKnown(Page.POLICY, "The earlier draft save is recorded. No duplicate snapshot was created.")
                    mutable.update { it.copy(formDirty = false) }
                }
            }
            Page.BACKTEST -> {
                snapshot["resources"] = api.get("/api/backtests/resources"); val jobs = api.get("/api/backtests/jobs"); snapshot["jobs"] = jobs
                pendingBacktest()?.let { pending -> if (jobs.rows("jobs").any { it.text("request_key") == pending.text("request_key") }) {
                    preferences.edit().remove("pending_backtest").apply(); reconcileKnown(Page.BACKTEST, "The earlier backtest request is recorded. No new run was submitted.")
                } }
            }
            Page.RISK -> snapshot["console"] = api.get("/api/console")
            Page.SECURITY -> snapshot["devices"] = api.get("/api/mobile/devices")
            else -> Unit
        }
        if (version != epoch || operation != operationSerial || !state.value.unlocked || state.value.page != page) return
        lastRefresh = SystemClock.elapsedRealtime()
        mutable.update { old ->
            val complete = snapshot.mapValues { (key, value) ->
                old.data[key]?.takeIf { it.toString() == value.toString() } ?: value
            }
            old.copy(data = old.data + complete, stale = false, error = if (old.stale) null else old.error,
                receivedAtElapsed = receivedAt)
        }
        if (checkDaily && page in listOf(Page.HOME, Page.STRATEGY)) {
            checkDailyEvidence(verifySession = !BuildConfig.DEMO)
            advanceDailyReview()
        }
        if (state.value.dailyPreparing) {
            val job = data("desk").obj("preparation").obj("job")
            when (job.text("state")) {
                "ready_for_review" -> mutable.update { it.copy(dailyPreparing = false, notice = "Your data is ready. Review the setup to finish.") }
                "failed", "cancelled", "interrupted" -> mutable.update { it.copy(dailyPreparing = false, error = friendly(job.text("error")) + ". Inspect the preparation details before retrying.") }
            }
        }
    }

    /** Bounded read-only checks. Failures do not log in, download or retry a mutation. */
    internal suspend fun checkDailyEvidence(verifySession: Boolean = true) {
        if (state.value.reconcile || state.value.stale) return
        var desk = data("desk")
        var setup = data("setup")
        val date = todayIst(desk.text("observed_at", ""))
        if (verifySession && date.isNotBlank() && !DailyJourney.sessionReady(desk, setup) &&
            setup.optBoolean("credentials_configured") && setup.optBoolean("access_token_available") && sessionCheckDate != date) {
            sessionCheckDate = date
            mutable.update { it.copy(journeyChecking = true, journeyCheckError = null) }
            try {
                save("setup", api.post("/api/setup/profile"))
                save("desk", api.get("/api/desk"))
            } catch (error: ApiFailure) {
                if (error.status != 409) throw error
                save("setup", api.get("/api/setup")); save("desk", api.get("/api/desk"))
                mutable.update { it.copy(journeyCheckError = "Saved Kite access could not be verified. Continue to check again or sign in. Check connectivity if sign-in is still current.") }
            } finally { mutable.update { it.copy(journeyChecking = false) } }
            desk = data("desk"); setup = data("setup")
        }
        val job = desk.obj("preparation").obj("job")
        val key = DailyJourney.auditKey(desk, setup)
        if (job.text("state") !in listOf("ready_for_review", "installed")) {
            dailyAuditAttempt = ""
            mutable.update { it.copy(journeyAuditKey = "") }
            return
        }
        if (key == dailyAuditAttempt) return
        dailyAuditAttempt = key
        mutable.update { it.copy(journeyChecking = true) }
        try {
            val audit = api.get("/api/desk/preparation/audit")
            val latest = api.get("/api/desk")
            save("desk", latest)
            if (key == DailyJourney.auditKey(latest, setup)) {
                save("dailyAudit", audit)
                mutable.update { it.copy(journeyAuditKey = key, journeyCheckError = null) }
            }
        } catch (error: CancellationException) {
            dailyAuditAttempt = ""
            throw error
        } catch (error: ApiFailure) {
            dailyAuditAttempt = "" // A subsequent quiet read can recover a failed read.
            if (error.status == 401) throw error
            mutable.update { it.copy(journeyAuditKey = "", journeyCheckError =
                "Saved data could not be checked. Retrying automatically; account status is shown separately. No download or trade was started.") }
        } finally { mutable.update { it.copy(journeyChecking = false) } }
    }

    fun journeyPolicy(policy: String) {
        if (policy in listOf("rules", "rules_ml") && canAct()) mutable.update { it.copy(journeyPolicy = policy) }
    }
    fun continueDay() {
        if (!canAct() || state.value.review != null) return
        work("Continuing your daily setup") {
            mutable.update { it.copy(journeyRunning = true, journeyCheckError = null) }
            // Explicit Continue can retry a failed read; successful current evidence remains reusable.
            if (!DailyJourney.sessionReady(data("desk"), data("setup"))) sessionCheckDate = ""
            refreshSnapshot()
            checkDailyEvidence()
            when (DailyJourney.step(state.value)) {
                0 -> {
                    val setup = data("setup")
                    check(!setup.optBoolean("stream_requested")) { "Review Disconnect in Broker & data before replacing Kite access. Fills and exits can depend on this feed." }
                    if (!setup.optBoolean("credentials_configured")) mutable.update { it.copy(page = Page.BROKER, journeyRunning = false) }
                    else {
                        preferences.edit().putBoolean("resume_prepare", true).putBoolean("resume_journey", true).putString("resume_universe", "nifty50").apply()
                        startBrokerLogin()
                    }
                }
                1 -> {
                    if (data("desk").text("mode") != "manual") mutable.update { it.copy(journeyRunning = false,
                        notice = "Access verified. Review Manual mode below before replacing strategy data.") }
                    else {
                        prepareSteps("nifty50", false, stayHome = true, skipVerifiedProfile = true)
                        refreshSnapshot()
                    }
                }
                2 -> if (state.value.review == null) {
                    val policy = DailyJourney.policy(state.value)
                    if (policy.isNotBlank()) { mutable.update { it.copy(journeyRunning = false) }; openGuidedReview(policy) }
                }
                else -> mutable.update { it.copy(journeyRunning = false) }
            }
        }
    }
    private suspend fun advanceDailyReview() {
        if (!state.value.journeyRunning || state.value.review != null || state.value.formDirty || state.value.pendingPage != null ||
            state.value.environmentDialog || state.value.reconcile || state.value.stale || state.value.page !in listOf(Page.HOME, Page.STRATEGY) ||
            data("desk").text("mode") != "manual" || DailyJourney.step(state.value) != 2) return
        val policy = DailyJourney.policy(state.value)
        if (policy.isBlank()) return // First policy choice stays explicit.
        mutable.update { it.copy(journeyRunning = false) } // Cancel/failure never reopens the review in a loop.
        openGuidedReview(policy)
    }
    fun journeyConnect() {
        val setup = data("setup")
        if (!DailyJourney.dataReady(state.value) || !DailyJourney.installed(data("desk")) || setup.optBoolean("stream_requested")) return
        reviewPost("Connect market data?", "Fresh quotes can resume pending paper fills and protective exits. Your trading mode stays unchanged.",
            "/api/setup/connect", JSONObject(), json("selected" to setup.optJSONArray("selected"), "connection_effect" to "Pending fills and exits can resume"))
    }

    fun prepareToday(universe: String, force: Boolean = false) = work("Preparing today's account") { prepareSteps(universe, force) }
    private suspend fun prepareSteps(universe: String, force: Boolean, stayHome: Boolean = false, skipVerifiedProfile: Boolean = false) {
        val desk = api.get("/api/desk"); save("desk", desk)
        check(desk.text("mode") == "manual") { "Choose Manual before preparing today's data. Review the mode change in Paper trading." }
        if (desk.obj("preparation").obj("job").text("state") == "downloading") {
            mutable.update { it.copy(page = if (stayHome) Page.HOME else Page.STRATEGY, dailyPreparing = true,
                notice = "Showing the existing download. No second download was started.") }; return
        }
        mutable.update { it.copy(progress = "Checking the saved Kite session") }
        if (!skipVerifiedProfile || !DailyJourney.sessionReady(desk, data("setup"))) try { save("setup", api.post("/api/setup/profile")) } catch (error: ApiFailure) {
            if (error.status != 409) throw error
            val setup = api.get("/api/setup"); save("setup", setup)
            check(!setup.optBoolean("stream_requested")) { "The saved session needs login. Review Disconnect in Broker & data first; existing fills and exits can depend on the feed." }
            preferences.edit().putBoolean("resume_prepare", true).putString("resume_universe", universe).apply()
            preferences.edit().putBoolean("resume_journey", stayHome).apply()
            startBrokerLogin(); return
        }
        var fresh = api.get("/api/desk")
        if (fresh.obj("preparation").obj("download_prerequisites").optInt("catalog_count") == 0) {
            mutable.update { it.copy(progress = "Importing the NSE symbol catalog") }
            save("setup", api.post("/api/setup/catalog"))
            fresh = api.get("/api/desk")
        }
        if (!force) {
            mutable.update { it.copy(progress = "Checking the saved download's date, sources and coverage") }
            // Lightweight status deliberately omits source validation; only an explicit audit can authorize reuse.
            val audit = api.get("/api/desk/preparation/audit")
            fresh = api.get("/api/desk")
            val currentJob = fresh.obj("preparation").obj("job")
            if (currentJob.text("state") == "downloading") {
                save("desk", fresh)
                mutable.update { it.copy(page = if (stayHome) Page.HOME else Page.STRATEGY, dailyPreparing = true,
                    notice = "Showing the existing download. No second download was started.") }; return
            }
            check(audit.obj("preparation").text("job_id", "") == currentJob.text("job_id", "")) {
                "Preparation changed while checking it. Check & prepare again to inspect the latest download."
            }
            if (PreparationReuse.verified(audit, universe, currentJob)) {
                save("desk", fresh)
                mutable.update { it.copy(page = if (stayHome) Page.HOME else Page.STRATEGY, dailyPreparing = false,
                    notice = "Reusing today's ${universeName(universe)} data downloaded ${istTime(currentJob.text("snapshot_at", ""))}. No daily candles were downloaded. Review the setup to finish.") }; return
            }
        }
        mutable.update { it.copy(progress = "Starting completed-history download") }
        val id = if (preferences.getBoolean("download_unknown", false))
            preferences.getString("download_request", null) ?: newIdentity() else newIdentity()
        preferences.edit().putString("download_request", id).apply()
        val result = try { api.post("/api/desk/preparation/download", json("universe" to universe,
            "request_id" to id, "revision" to fresh.text("revision"), "acknowledged" to true)) }
        catch (error: ApiFailure) { if (error.uncertain) preferences.edit().putBoolean("download_unknown", true).apply(); throw error }
        preferences.edit().putBoolean("download_unknown", false).apply()
        save("desk", JSONObject(fresh.toString()).put("preparation", result))
        mutable.update { it.copy(page = if (stayHome) Page.HOME else Page.STRATEGY, dailyPreparing = true,
            notice = "Download started. Progress updates automatically; reviews remain yours to confirm.") }
    }

    private suspend fun startBrokerLogin() {
        val value = api.post("/api/mobile/broker/login")
        val url = java.net.URI(value.getString("login_url"))
        check(url.scheme == "https" && url.host == "kite.zerodha.com") { "Unexpected broker login destination." }
        preferences.edit().putString("broker_attempt", value.getString("attempt_id")).apply()
        mutable.update { it.copy(brokerUrl = url.toString(), notice = "Complete Zerodha login, return here and unlock to continue.") }
    }
    fun brokerLogin() = work("Opening secure Zerodha sign-in") { preferences.edit().remove("resume_prepare").apply(); startBrokerLogin() }
    fun manualExchange(token: String) = work("Exchanging the one-time broker token") {
        val attempt = preferences.getString("broker_attempt", null)
        check(attempt != null) { "Start a fresh Zerodha login in this app first." }
        api.post("/api/mobile/broker/login/$attempt/exchange", json("request_token" to token.trim()))
        preferences.edit().remove("broker_attempt").apply()
        refreshSnapshot()
        if (preferences.getBoolean("resume_prepare", false)) {
            val journey = preferences.getBoolean("resume_journey", false)
            preferences.edit().remove("resume_prepare").remove("resume_journey").apply()
            mutable.update { it.copy(journeyRunning = journey) }
            prepareSteps(preferences.getString("resume_universe", "nifty50")!!, false, journey, true)
            refreshSnapshot()
        }
    }
    fun brokerOpened() { mutable.update { it.copy(brokerUrl = null) } }

    fun cancelReview() { mutable.update { it.copy(review = null, journeyRunning = false) } }
    fun confirmReview(acknowledged: Boolean) {
        val review = state.value.review ?: return
        if (!acknowledged || state.value.busy || state.value.stale || state.value.reconcile) return
        mutable.update { it.copy(review = null) }
        work(review.confirmLabel) { review.submit(); refreshSnapshot() }
    }
    fun reviewPost(title: String, explanation: String, path: String, body: JSONObject, details: JSONObject = body) {
        if (!canAct()) return
        pauseQuietRead()
        val frozen = JSONObject(body.toString())
        mutable.update { it.copy(review = Review(title, explanation, details, "Confirm") {
            if (path == "/api/backtests/jobs") preferences.edit().putString("pending_backtest", frozen.toString()).apply()
            val result = try { api.post(path, frozen) } catch (error: ApiFailure) {
                if (path == "/api/backtests/jobs" && !error.uncertain) preferences.edit().remove("pending_backtest").apply()
                throw error
            }
            if (path == "/api/backtests/jobs") preferences.edit().remove("pending_backtest").apply()
            mutable.update { old -> old.copy(notice = result.text("message", "Action recorded. Inspect saved status and fills."),
                formDirty = if (path == "/api/desk/watchlist") false else old.formDirty) }
        }) }
    }
    fun canAct() = state.value.unlocked && !state.value.busy && !state.value.stale && !state.value.reconcile && data("desk").obj("account").text("mode") == "paper"

    fun searchWatchlist(symbol: String) {
        if (!state.value.unlocked || state.value.review != null) return
        work("Searching the NSE catalog") {
            save("watchlistCatalog", api.get("/api/desk/watchlist/catalog?q=" + URLEncoder.encode(symbol.trim(), "UTF-8")))
        }
    }
    fun reviewWatchlist(symbols: List<String>) {
        val safety = data("watchlist").obj("safety")
        if (!safety.has("revision")) return
        reviewPost("Replace permitted stocks?", "Cancel all pending buys and pause strategy decisions. Existing holdings and protective exits remain. Only this saved list may be bought. An empty list blocks every purchase.",
            "/api/desk/watchlist", json("symbols" to JSONArray(symbols.sorted()), "revision" to safety.getInt("revision"), "acknowledged" to true))
    }
    fun reviewSafetyResume() {
        val value = data("watchlist"); val safety = value.obj("safety")
        if (state.value.formDirty || !safety.optBoolean("paused") || value.text("mode") != "manual") return
        reviewPost("Reset drawdown reference?", "Acknowledge the drawdown and set current equity as a new peak reference. Trading stays manual. Kill switch, daily loss, five-entry limit and today's data block still apply.",
            "/api/desk/safety/resume", json("revision" to safety.getInt("revision"), "acknowledged" to true), safety)
    }

    fun guidedReview(policy: String) = work("Preparing your setup summary") { openGuidedReview(policy) }
    private suspend fun openGuidedReview(policy: String) {
        check(policy in listOf("rules", "rules_ml")) { "Choose a decision policy explicitly first." }
        val desk = api.get("/api/desk"); save("desk", desk)
        val value = api.post("/api/desk/preparation/guided/preview", json("revision" to desk.text("revision"), "strategy_mode" to policy))
        val body = json("preview_sha256" to value.text("preview_sha256"), "acknowledged" to true)
        mutable.update { it.copy(review = Review("Review today's paper setup",
            "Review every stock, source, session and policy below. Confirmation installs this selection, applies eligible reviews and requests market data. It keeps Manual selected; fresh quotes and session safeguards still apply.",
            value.obj("plan"), "Confirm and prepare") {
            val result = api.post("/api/desk/preparation/guided/confirm", body)
            mutable.update { old -> old.copy(journeyPolicy = "", notice = result.text("message")) }
        }) }
    }

    fun chooseMode(mode: String) {
        if (!canAct() || mode !in listOf("manual", "approval", "automatic") || state.value.review != null) return
        work("Checking ${friendly(mode)} readiness") {
            refreshSnapshot()
            val desk = data("desk")
            if (desk.text("mode") == mode) { mutable.update { it.copy(modeHelp = null, notice = "${friendly(mode)} is already selected.") }; return@work }
            if (mode != "manual" && !modeIsReady(desk)) {
                mutable.update { it.copy(modeHelp = mode) }
            } else {
                val body = json("mode" to mode, "revision" to desk.text("revision"), "acknowledged" to true)
                mutable.update { it.copy(modeHelp = null, review = Review("${friendly(mode)} paper mode?",
                    "Approval requires each proposal to be reviewed. Automatic can submit eligible paper orders without another proposal approval. Fresh later quotes can fill accepted orders. This affects virtual holdings only; all risk checks remain active.",
                    json("requested_mode" to mode, "current_mode" to desk.text("mode"), "readiness" to desk.obj("readiness")), "Confirm") {
                    try {
                        api.post("/api/desk/mode", body)
                        mutable.update { old -> old.copy(notice = "${friendly(mode)} selected. Review saved status and proposals below.") }
                    } catch (error: ApiFailure) {
                        if (error.status != 409 || mode == "manual") throw error
                        refreshSnapshot()
                        if (modeIsReady(data("desk"))) throw error
                        mutable.update { old -> old.copy(modeHelp = mode,
                            notice = "Readiness changed before confirmation. Review the current mode and checks; no retry was sent.") }
                    }
                }) }
            }
        }
    }
    fun dismissModeHelp() { mutable.update { it.copy(modeHelp = null) } }
    fun previewDecision(identity: String) = work("Checking the proposal") {
        val value = api.post("/api/desk/decisions/$identity/preview")
        check(value.obj("review").optBoolean("allowed")) { "Proposal is blocked: " + value.obj("review").strings("reasons").joinToString { friendly(it) } }
        mutable.update { it.copy(review = Review("Approve this paper proposal?", "Review quantity, fees, cash and price drift. Acceptance reserves virtual cash; a later usable quote determines any fill.",
            value, "Approve paper proposal") { api.post("/api/desk/decisions/$identity/approve", json("preview_sha256" to value.text("preview_sha256"))) }) }
    }
    fun rejectDecision(identity: String) = reviewPost("Reject this proposal?", "No new order will be created for this proposal.", "/api/desk/decisions/$identity/reject", JSONObject())
    fun inspectFills(identity: String, before: String = "") = work("Loading recorded fills") {
        save("fills", api.get("/api/activity/orders/${encode(identity)}/fills" + if (before.isBlank()) "" else "?before=$before"))
    }
    fun olderActivity(before: String) = work("Loading earlier activity") { save("activity", api.get("/api/activity?before=${encode(before)}")) }

    fun selectSymbol(symbol: String, timeframe: String = state.value.timeframe) {
        mutable.update { it.copy(symbol = symbol, timeframe = timeframe, page = Page.ANALYSIS) }
        work("Loading saved price research") { loadAnalysis() }
    }
    private suspend fun loadAnalysis() { save("analysis", fetchAnalysis()) }
    private suspend fun fetchAnalysis(): JSONObject {
        val v = state.value
        val query = "?timeframe=${encode(v.timeframe)}" + if (v.symbol.isBlank()) "" else "&symbol=${encode(v.symbol)}"
        return optional((if (v.timeframe in listOf("1d", "1w", "1mo")) "/api/research/series" else "/api/analysis") + query)
    }
    fun loadDraft(identity: String) = work("Loading a saved policy") { save("draft", api.get("/api/investment-policies/${encode(identity)}")) }
    fun previewPolicy(draft: JSONObject) = work("Checking policy choices") {
        val value = api.post("/api/investment-policies/preview", json("draft" to draft))
        mutable.update { it.copy(review = Review("Save this policy draft?", "This saves an immutable research specification. It does not replace the installed strategy, invest money or change trading mode. Blank fields remain unresolved.", value.obj("draft"), "Save draft") {
            preferences.edit().putString("pending_policy_id", "draft-" + value.text("preview_sha256")).apply()
            val saved = try { api.post("/api/investment-policies", json("draft" to draft, "preview_sha256" to value.text("preview_sha256"), "acknowledged" to true)) }
                catch (error: ApiFailure) { if (!error.uncertain) preferences.edit().remove("pending_policy_id").apply(); throw error }
            preferences.edit().remove("pending_policy_id").apply()
            save("draft", saved); mutable.update { old -> old.copy(formDirty = false, notice = "Policy draft saved. Your installed strategy and trading mode are unchanged.") }
        }) }
    }

    fun previewPurchase(request: JSONObject) = work("Calculating an exact purchase preview") {
        val value = api.post("/api/paper/portfolio/preview", request)
        check(value.obj("decision").optBoolean("allowed")) { "Purchase blocked: " + value.obj("decision").strings("reasons").joinToString { friendly(it) } }
        mutable.update { it.copy(review = Review("Confirm this virtual-share purchase?", "Review maximum cash debit including fees, quantity and holding protections. This reserves existing virtual cash. A later fresh reviewed quote and available liquidity determine fills. There is no automatic retry.", value, "Confirm paper purchase") {
            api.post("/api/paper/portfolio/contributions", json("request" to request, "preview_sha256" to value.text("preview_sha256")))
        }) }
    }
    fun runBacktest(resource: JSONObject) {
        if (!data("resources").obj("capability").optBoolean("available")) { reportError("The server's isolated runner is unavailable."); return }
        reviewPost("Start this isolated backtest?", "This runs the exact registered inputs and costs in a separate research account. It does not alter your connected paper account or establish future profitability.",
            "/api/backtests/jobs", json("resource_id" to resource.text("resource_id"), "resource_sha256" to resource.text("resource_sha256"),
                "request_key" to newIdentity(), "acknowledged" to true), resource)
    }
    fun pendingBacktest(): JSONObject? = preferences.getString("pending_backtest", null)?.let { runCatching { JSONObject(it) }.getOrNull() }
    fun retryBacktest() {
        val pending = pendingBacktest() ?: return
        reviewPost("Retry the same research request?", "This reuses the original request key and resource hash after inspecting saved jobs. It cannot create a second run for the same key.", "/api/backtests/jobs", pending)
    }
    private fun reconcileKnown(page: Page, message: String) {
        if (state.value.reconcile && state.value.reconcilePage == page) {
            preferences.edit().putBoolean("inspect_activity", false).apply()
            mutable.update { it.copy(reconcile = false, notice = message) }
        }
    }
    fun loadReport(identity: String, compare: Boolean = false) = work("Loading the recorded report") {
        val value = api.get("/api/backtests/reports/${encode(identity)}")
        mutable.update { if (compare) it.copy(compareReport = value) else it.copy(report = value) }
    }
    fun revokePhone(identity: String) {
        if (!canAct()) return
        pauseQuietRead()
        mutable.update { it.copy(review = Review("Revoke this phone?", "Its stored credential and sessions will stop working. Pairing again requires the owner token. This does not stop the server, close holdings or cancel orders.", json("phone" to identity), "Revoke pairing") {
            api.delete("/api/mobile/devices/${encode(identity)}"); forgetPhone()
        }) }
    }
    fun ownerPhones(token: String) = work("Checking paired-phone records") {
        val result = transport.request("GET", "/api/mobile/devices", token.trim(), null)
        ownerAuthorization = token.trim(); save("ownerDevices", result)
    }
    fun revokeOwnedPhone(device: JSONObject) {
        val token = ownerAuthorization ?: return
        if (!canAct()) return
        pauseQuietRead()
        mutable.update { it.copy(review = Review("Revoke ${device.text("label")}?", "The selected phone's credential and sessions will stop working. This does not stop the server or close holdings. Pairing it again needs the owner token.", device, "Revoke phone") {
            check(preferences.edit().putBoolean("inspect_activity", true).putString("inspect_page", Page.SECURITY.name).commit()) { "Recovery status could not be saved." }
            transport.request("DELETE", "/api/mobile/devices/${encode(device.text("id"))}", token, null)
            preferences.edit().putBoolean("inspect_activity", false).commit()
            if (data("devices").rows("devices").any { it.text("id") == device.text("id") }) forgetPhone()
            else save("ownerDevices", transport.request("GET", "/api/mobile/devices", token, null))
        }) }
    }
    private fun encode(value: String) = URLEncoder.encode(value, "UTF-8")
    override fun onCleared() { api.lock(); super.onCleared() }
}
