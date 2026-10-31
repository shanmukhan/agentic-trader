package com.shanmukhan.agentictrader

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Check
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import org.json.JSONObject

/** Display progress only. Server previews, revisions and readiness retain all authority. */
internal object DailyJourney {
    fun sessionReady(desk: JSONObject, setup: JSONObject): Boolean =
        desk.obj("preparation").obj("download_prerequisites").opt("session_verified") == true ||
            setup.opt("profile_verified_this_run") == true && todayIst(setup.text("profile_checked_at", "")) == todayIst(desk.text("observed_at", "")) &&
            todayIst(desk.text("observed_at", "")).isNotBlank() &&
            runCatching { parseInstant(setup.text("profile_checked_at")) <= parseInstant(desk.text("observed_at")) }.getOrDefault(false)

    // Invalidate at the reviewed close as well as midnight, job/source/policy changes.
    // No assumed market hours or device clock can make cached history current.
    fun auditKey(desk: JSONObject, setup: JSONObject): String {
        val job = desk.obj("preparation").obj("job")
        val date = todayIst(desk.text("observed_at", ""))
        val reviewedClose = setup.rows("sessions").firstOrNull { it.text("date") == date }?.text("close", "")
        // The server-generated CSV has fixed date/open/close leading columns; a
        // proposed close can invalidate history before installation grants any authority.
        val proposedClose = job.text("calendar_csv", "").lineSequence().map { it.split(',', limit = 4) }
            .firstOrNull { it.size >= 3 && it[0] == date }?.get(2)
        val closes = listOfNotNull(reviewedClose, proposedClose).filter { it.isNotBlank() }.distinct().sorted()
        val boundary = closes.joinToString(",") { close ->
            val normalized = if (close.length == 5) "$close:00" else close
            val passed = runCatching { parseInstant(desk.text("observed_at")) >= parseInstant("${date}T${normalized}+05:30") }.getOrDefault(true)
            "$close:$passed"
        }.ifBlank {
            // No usable calendar: bound memory reuse to five server-clock minutes.
            runCatching { (parseInstant(desk.text("observed_at")).epochSecond / 300).toString() }.getOrDefault("unknown")
        }
        return listOf(date, boundary, job.text("job_id", ""), job.text("state", ""),
            job.text("preview_sha256", ""), desk.text("strategy_mode", "")).joinToString("|")
    }

    fun dataReady(state: AppState): Boolean {
        val desk = state.data["desk"] ?: JSONObject()
        return state.journeyAuditKey == auditKey(desk, state.data["setup"] ?: JSONObject()) &&
            PreparationReuse.verified(state.data["dailyAudit"] ?: JSONObject(), "nifty50", desk.obj("preparation").obj("job"))
    }
    fun dataReason(state: AppState): String {
        val job = state.data["desk"]?.obj("preparation")?.obj("job") ?: JSONObject()
        val evidence = state.data["dailyAudit"]?.obj("source_validation") ?: JSONObject()
        return when {
            job.text("universe", "").isNotBlank() && job.text("universe") != "nifty50" -> "Your saved download covers ${universeName(job.text("universe"))}. This daily flow prepares the official Nifty 50."
            evidence.opt("hashes_valid") == false -> "Saved source files could not be verified. Fresh source evidence is needed."
            evidence.opt("same_ist_date") == false -> "Saved sources are from an earlier IST date. Today's sources need checking."
            evidence.opt("coverage_valid") == false -> "Saved history is missing completed session coverage. This can happen after today's reviewed close."
            else -> "Current Nifty 50 source and completed-history evidence is needed."
        }
    }
    fun installed(desk: JSONObject): Boolean {
        val job = desk.obj("preparation").obj("job")
        val receipt = desk.obj("guided_setup")
        val unfinished = receipt.obj("plan").text("job_id", "") == job.text("job_id", "") &&
            receipt.text("state") in listOf("applying", "stopped", "interrupted")
        return job.text("state") == "installed" && !unfinished &&
            desk.obj("readiness").rows("checks").any { it.text("key") == "strategy" && it.opt("ready") == true }
    }
    fun step(state: AppState): Int {
        val desk = state.data["desk"] ?: JSONObject()
        return when {
            !sessionReady(desk, state.data["setup"] ?: JSONObject()) -> 0
            !dataReady(state) -> 1
            !installed(desk) -> 2
            else -> 3
        }
    }
    fun policy(state: AppState): String = state.journeyPolicy.ifBlank {
        state.data["desk"]?.text("strategy_mode", "")?.takeIf { it in listOf("rules", "rules_ml") }.orEmpty()
    }
}

@Composable internal fun DailyJourneyCard(state: AppState, model: TraderViewModel) {
    val desk = model.data("desk"); val setup = model.data("setup")
    val job = desk.obj("preparation").obj("job")
    val step = DailyJourney.step(state)
    val labels = listOf("Access", "Data", "Review", "Trade")
    var details by remember { mutableStateOf(false) }
    var changePolicy by remember { mutableStateOf(false) }
    Section("Your day, step by step", "Official Nifty 50 · paper trading") {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            labels.forEachIndexed { index, label ->
                Column(Modifier.weight(1f).semantics(mergeDescendants = true) {
                    stateDescription = when { index < step -> "Completed"; index == step -> "Current step"; else -> "Upcoming" }
                }, horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Box(Modifier.size(32.dp).background(if (index <= step) Teal else Line, CircleShape), contentAlignment = Alignment.Center) {
                        if (index < step) Icon(Icons.Outlined.Check, null, tint = MaterialTheme.colorScheme.onPrimary, modifier = Modifier.size(18.dp))
                        else Text("${index + 1}", color = if (index == step) MaterialTheme.colorScheme.onPrimary else Ink)
                    }
                    Text(label, style = MaterialTheme.typography.labelMedium)
                }
            }
        }
        Text("Step ${step + 1} of 4 · ${labels[step]}", fontWeight = FontWeight.Bold,
            modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite })
        when {
            state.stale -> Text("Waiting for your server. Checks resume automatically when it responds.")
            state.reconcile -> Text("Inspect the previous instruction's saved outcome above before continuing.")
            state.journeyChecking -> Text("Checking saved access and data automatically…")
            step == 0 -> {
                Text(if (!setup.optBoolean("credentials_configured")) "Add your Kite app credentials once to get started."
                    else "Your saved Kite access needs verification. Continue checks it first; sign in only if verification fails.")
                state.journeyCheckError?.let { Hint(it, error = true) }
                Action(if (!setup.optBoolean("credentials_configured")) "Set up Kite access" else "Continue with Kite", model.canAct()) { model.continueDay() }
            }
            step == 1 -> {
                val running = job.text("state") == "downloading"
                if (running) {
                    Text(if (job.optInt("total") > 0) "Preparing your data · ${job.optInt("completed")} / ${job.optInt("total")} stocks read" else "Preparing sources and stock coverage…")
                    if (job.optInt("total") > 0) LinearProgressIndicator(progress = { (job.optInt("completed").toFloat() / job.optInt("total")).coerceIn(0f, 1f) }, modifier = Modifier.fillMaxWidth())
                    else LinearProgressIndicator(Modifier.fillMaxWidth())
                    Text(if (state.journeyRunning) "The setup review opens here when data is ready." else "Progress updates automatically. Continue to follow this download through to review.")
                    if (!state.journeyRunning) Action("Continue this preparation", model.canAct()) { model.continueDay() }
                } else {
                    Text(DailyJourney.dataReason(state))
                    Text("Missing catalog details are imported automatically. A current download is reused; otherwise we prepare fresh history for this basket.", style = MaterialTheme.typography.bodyMedium)
                    if (job.text("error", "").isNotBlank()) Hint("Preparation stopped: ${friendly(job.text("error"))}. Check the details before retrying.", error = true)
                    state.journeyCheckError?.let { Hint(it, error = true) }
                    if (desk.text("mode") != "manual") {
                        Text("Choose Manual before replacing strategy data. Existing holdings remain open.")
                        Action("Review Manual mode", model.canAct()) { model.chooseMode("manual") }
                    } else Action("Prepare & continue", model.canAct()) { model.continueDay() }
                }
            }
            step == 2 -> {
                Text("Your data is current. One review covers the strategy, stocks, exchange sessions, eligible price-basis reviews and market-data connection.")
                val policy = DailyJourney.policy(state)
                if (policy.isBlank() || changePolicy) Choice("Decision policy · choose once", policy, listOf("rules" to "Rules only · experimental paper policy") +
                    if (desk.obj("preparation").optBoolean("ml_configured")) listOf("rules_ml" to "Rules + validated ML") else emptyList(), { model.journeyPolicy(it); changePolicy = false })
                else {
                    Text("Using your saved choice: ${if (policy == "rules") "Rules only" else "Rules + validated ML"}.")
                    TextButton({ changePolicy = true }) { Text("Change decision policy") }
                }
                if (desk.text("mode") != "manual") Action("Review Manual mode", model.canAct()) { model.chooseMode("manual") }
                else Action("Review & continue", model.canAct() && policy.isNotBlank()) { model.continueDay() }
            }
            else -> {
                val guidance = tradeGuidance(desk)
                Text(guidance.text("title"), fontWeight = FontWeight.SemiBold)
                Text(guidance.text("summary"))
                val next = guidance.text("next_entry_at", "")
                if (next.isNotBlank()) Text("Next reviewed entry: ${istTime(next)}", color = Teal)
                when {
                    !setup.optBoolean("stream_requested") -> Action("Review market-data connection", model.canAct()) { model.journeyConnect() }
                    setup.obj("feed_diagnostics").text("state") == "failed" -> {
                        Hint("Market-data connection failed. Review the cause and recovery in Broker & data.", error = true)
                        Action("Resolve connection", !state.busy, secondary = true) { model.navigate(Page.BROKER) }
                    }
                    !setup.optBoolean("feed_connected") -> Text("Connecting to Zerodha… success or failure appears automatically.")
                    desk.text("mode") != "manual" -> {
                        Text("${friendly(desk.text("mode"))} selected · ${desk.rows("decisions").count { it.text("state") == "awaiting_approval" }} proposals awaiting review")
                        Action("Open trading activity", !state.busy) { model.navigate(Page.PAPER) }
                    }
                    modeIsReady(desk) -> {
                        var mode by remember { mutableStateOf("approval") }
                        Choice("How should paper trades be approved?", mode, listOf("approval" to "Approval · I review each proposal", "automatic" to "Automatic · use eligible signals"), { mode = it })
                        Action("Review ${friendly(mode)} mode", model.canAct()) { model.chooseMode(mode) }
                    }
                    else -> {
                        Text("Checks update automatically. A trading mode will need your confirmation when ready.")
                        Action("View remaining checks", !state.busy, secondary = true) { model.navigate(Page.PAPER) }
                    }
                }
            }
        }
        TextButton({ details = !details }, Modifier.fillMaxWidth()) { Text(if (details) "Hide setup details" else "Setup details & completed checks") }
        if (details) {
            Text("Access: ${if (DailyJourney.sessionReady(desk, setup)) "verified today" else "verification needed"}")
            Text("Data: ${if (DailyJourney.dataReady(state)) "sources and completed history verified" else "current evidence needed"}")
            Text("Setup: ${if (DailyJourney.installed(desk)) "installed" else "review needed"}")
            Text("Trading mode: ${friendly(desk.text("mode"))}")
            Text("Checked ${istTime(desk.text("observed_at", ""))} · automatic updates while unlocked", style = MaterialTheme.typography.bodySmall)
            Action("Broker & data", !state.busy, secondary = true) { model.navigate(Page.BROKER) }
            if (state.page == Page.HOME) Action("Advanced strategy controls", !state.busy, secondary = true) { model.navigate(Page.STRATEGY) }
        }
    }
}
