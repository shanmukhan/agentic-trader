package com.shanmukhan.agentictrader

import android.app.Application
import android.graphics.Bitmap
import androidx.activity.compose.setContent
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.lifecycle.ViewModelStore
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import java.io.File
import java.util.concurrent.CopyOnWriteArrayList
import kotlinx.coroutines.awaitCancellation
import kotlinx.coroutines.CompletableDeferred
import androidx.compose.ui.semantics.SemanticsProperties

/** Invented, offline app tests. They do not establish broker or device-biometric acceptance. */
class NativeWorkflowTest {
    @get:Rule val ui = createAndroidComposeRule<MainActivity>()
    private lateinit var model: TraderViewModel
    private lateinit var transport: FixtureTransport
    private val store = ViewModelStore()

    @Before fun setup() {
        org.junit.Assume.assumeTrue("Offline demo flavor only", BuildConfig.DEMO)
        ui.runOnUiThread {
            val app = ui.activity.application
            app.getSharedPreferences("recovery", 0).edit().clear().commit()
            transport = FixtureTransport(app)
            model = TraderViewModel(app, transport)
            store.put("native-qa", model)
            ui.activity.setContent { TraderTheme { TraderApp(model, BiometricGate(ui.activity), {}) } }
        }
        ready()
    }

    @After fun cleanup() { if (::model.isInitialized) ui.runOnUiThread { store.clear() } }
    private fun ready() { ui.waitUntil(15_000) { !model.state.value.busy && model.data("desk").has("account") }; ui.waitForIdle() }
    private fun act(action: () -> Unit) { ui.runOnUiThread(action); ready() }
    private fun screenshot(name: String) {
        ui.waitForIdle()
        Thread.sleep(300) // Allow Android dialog-window transitions to finish before visual capture.
        ui.waitForIdle()
        val dir = File(ui.activity.getExternalFilesDir(null), "native-qa").apply { mkdirs() }
        File(dir, "$name.png").outputStream().use { ui.onRoot().captureToImage().asAndroidBitmap().compress(Bitmap.CompressFormat.PNG, 100, it) }
    }

    @Test fun everyDestinationRendersNativeContentAndExactInventedBalances() {
        ui.onNodeWithText("₹25,018.77").assertExists()
        screenshot("home")
        Page.entries.forEach { page ->
            if (page == Page.ANALYSIS) act { model.selectSymbol("NSE:DEMO") } else act { model.navigate(page) }
            assertEquals(page, model.state.value.page)
            assertTrue(page.title, ui.onAllNodesWithText(page.title).fetchSemanticsNodes().isNotEmpty())
            assertNull("No crash/error on $page", model.state.value.error)
            if (page in listOf(Page.ANALYSIS, Page.STRATEGY, Page.POLICY, Page.BROKER, Page.PORTFOLIO)) screenshot(page.name.lowercase())
        }
        val permissions = ui.activity.packageManager.getPackageInfo(ui.activity.packageName, android.content.pm.PackageManager.GET_PERMISSIONS).requestedPermissions.orEmpty()
        assertFalse("Offline tests must not have Internet permission", permissions.contains("android.permission.INTERNET"))
        assertTrue(transport.posts.isEmpty())
    }

    @Test fun watchlistGuardsEditsAndRequiresAcknowledgedConfirmation() {
        act { model.navigate(Page.WATCHLIST) }
        val equity = model.data("desk").obj("account").text("equity")
        act { model.searchWatchlist("SECOND") }
        ui.onNodeWithText("Add NSE:SECOND").performScrollTo().performClick()
        assertTrue(model.state.value.formDirty)
        assertTrue(transport.posts.isEmpty())
        act { model.navigate(Page.BROKER) }
        assertEquals(Page.WATCHLIST, model.state.value.page)
        assertEquals(Page.BROKER, model.state.value.pendingPage)
        act { model.discardNavigation(false) }
        act { model.reviewWatchlist(listOf("NSE:DEMO", "NSE:SECOND")) }
        assertNotNull(model.state.value.review)
        act { model.confirmReview(false) }
        assertTrue(transport.posts.isEmpty())
        act { model.cancelReview() }
        assertTrue(transport.posts.isEmpty())
        act { model.reviewWatchlist(listOf("NSE:DEMO", "NSE:SECOND")) }
        act { model.confirmReview(true) }
        assertEquals(listOf("/api/desk/watchlist"), transport.posts.map { it.first })
        val body = transport.posts.single().second
        assertEquals(listOf("NSE:DEMO", "NSE:SECOND"), body.strings("symbols"))
        assertEquals(1, body.getInt("revision"))
        assertTrue(body.getBoolean("acknowledged"))
        assertFalse(model.state.value.formDirty)
        assertEquals(equity, model.data("desk").obj("account").text("equity"))
        assertEquals("manual", model.data("desk").text("mode"))
    }

    @Test fun dailyPreparationChecksProfileThenDownloadsWithoutInstallingOrChangingMode() {
        transport.recentDownload()
        act { model.prepareToday("nifty100", true) }
        assertEquals(listOf("/api/setup/profile", "/api/desk/preparation/download"), transport.posts.map { it.first })
        val body = transport.posts.last().second
        assertEquals("nifty100", body.getString("universe"))
        assertTrue(body.getString("request_id").matches(Regex("[a-f0-9]{32}")))
        assertTrue(body.getBoolean("acknowledged"))
        assertEquals(Page.STRATEGY, model.state.value.page)
        assertEquals("manual", model.data("desk").text("mode"))
        assertTrue(model.state.value.dailyPreparing)
        assertFalse(transport.gets.any { it == "/api/desk/preparation/audit" })
    }

    @Test fun repeatedPrepareReusesFiveMinuteOldAuditedHistoryWithoutAnotherDownload() {
        val identity = transport.recentDownload()
        act { model.prepareToday("nifty100") }
        act { model.prepareToday("nifty100") }
        assertEquals(listOf("/api/setup/profile", "/api/setup/profile"), transport.posts.map { it.first })
        assertEquals(2, transport.gets.count { it == "/api/desk/preparation/audit" })
        assertEquals(identity, model.data("desk").obj("preparation").obj("job").text("job_id"))
        assertEquals("manual", model.data("desk").text("mode"))
        assertEquals("23998.77", model.data("desk").obj("account").text("cash"))
        assertTrue(model.state.value.notice!!.contains("Reusing today's Nifty 100 data"))
        assertTrue(model.state.value.notice!!.contains("No daily candles were downloaded"))
        ui.onNodeWithText("Reusing today's Nifty 100 data", substring = true).assertIsDisplayed()
        assertFalse(model.state.value.dailyPreparing)
        assertNull(model.state.value.review)
    }

    @Test fun anotherUniverseRequiresItsOwnDownloadEvenWhenTheExistingAuditPasses() {
        transport.recentDownload()
        act { model.prepareToday("nifty500") }
        assertEquals(1, transport.posts.count { it.first == "/api/desk/preparation/download" })
        assertEquals("nifty500", transport.posts.last().second.getString("universe"))
        assertTrue(transport.gets.contains("/api/desk/preparation/audit"))
        assertFalse(transport.posts.any { it.first.contains("install") || it.first == "/api/desk/mode" })
    }

    @Test fun changedSourceEvidenceRequiresFreshData() {
        transport.recentDownload()
        transport.auditReport!!.obj("source_validation").put("hashes_valid", false)
        act { model.prepareToday("nifty100") }
        assertEquals(1, transport.posts.count { it.first == "/api/desk/preparation/download" })
    }

    @Test fun aFirstPreparationWithoutSavedEvidenceDownloadsOnce() {
        act { model.prepareToday("nifty100") }
        assertEquals(1, transport.posts.count { it.first == "/api/desk/preparation/download" })
        assertTrue(transport.gets.contains("/api/desk/preparation/audit"))
    }

    @Test fun reviewRequiresAcknowledgementAndDuplicateTapSendsOnlyOneFrozenInstruction() {
        transport.allowPaperModes()
        act { model.chooseMode("approval") }
        assertTrue(transport.posts.isEmpty())
        ui.onNodeWithText("Confirm").assertIsNotEnabled()
        ui.runOnUiThread { model.confirmReview(false) }
        assertTrue(transport.posts.isEmpty())
        ui.onNodeWithText("I reviewed the displayed values, effects and limitations.").performScrollTo().performClick()
        ui.onNodeWithText("Confirm").assertIsEnabled()
        ui.runOnUiThread { model.confirmReview(true); model.confirmReview(true) }
        ready()
        assertEquals(1, transport.posts.size)
        assertEquals("approval", transport.posts.single().second.getString("mode"))
        assertEquals("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", transport.posts.single().second.getString("revision"))
    }

    @Test fun uncertainWriteBlocksNewInstructionsUntilFreshSavedStateIsInspected() {
        transport.failMode = true
        transport.allowPaperModes()
        act { model.chooseMode("approval") }
        act { model.confirmReview(true) }
        assertTrue(model.state.value.stale)
        assertTrue(model.state.value.reconcile)
        assertFalse(model.canAct())
        act { model.navigate(Page.HISTORY) }
        assertFalse(model.state.value.stale)
        assertTrue(model.state.value.reconcile)
        assertEquals(1, transport.posts.size)
        act { model.acknowledgeReconciliation() }
        assertFalse(model.state.value.reconcile)
        assertTrue(model.canAct())
        assertEquals(1, transport.posts.size)
    }

    @Test fun policyEditsRequireAnExplicitDiscardBeforeNavigation() {
        act { model.navigate(Page.POLICY) }
        ui.onNodeWithText("Draft name").performTextInput("Invented long term policy")
        assertTrue(model.state.value.formDirty)
        act { model.navigate(Page.HOME) }
        assertEquals(Page.POLICY, model.state.value.page)
        ui.onNodeWithText("Discard unsaved policy choices?").assertExists()
        ui.onNodeWithText("Keep editing").performClick()
        assertTrue(model.state.value.formDirty)
        act { model.navigate(Page.HOME) }
        ui.onNodeWithText("Discard and leave").performClick()
        ready()
        assertEquals(Page.HOME, model.state.value.page)
        assertFalse(model.state.value.formDirty)
        assertTrue(transport.posts.isEmpty())
    }

    @Test fun cancelledInFlightInstructionRetainsDurableRecoveryAcrossViewModelRecreation() {
        transport.suspendMode = true
        transport.allowPaperModes()
        act { model.chooseMode("approval") }
        ui.runOnUiThread { model.confirmReview(true) }
        ui.waitUntil(5000) { transport.posts.size == 1 }
        val preferences = ui.activity.getSharedPreferences("recovery", 0)
        assertTrue(preferences.getBoolean("inspect_activity", false))
        ui.runOnUiThread {
            store.clear()
            model = TraderViewModel(ui.activity.application, transport)
            store.put("native-qa", model)
        }
        ready()
        assertTrue(model.state.value.reconcile)
        assertEquals(Page.HISTORY, model.state.value.reconcilePage)
        assertEquals(1, transport.posts.size)
        assertFalse(model.canAct())
    }

    @Test fun androidOffsetTimestampsRenderInIstAndPreserveExpiryChronology() {
        assertEquals("2026-10-28T03:30:00Z", parseInstant("2026-10-28T03:30:00+00:00").toString())
        assertEquals("2026-10-28", todayIst("2026-10-27T23:30:00+00:00"))
        assertTrue(istTime("2026-10-28T03:30:00+00:00"), istTime("2026-10-28T03:30:00+00:00").contains("9:00"))
    }

    @Test fun quietRefreshKeepsControlsSteadyAndPublishesOneCompleteSnapshot() {
        val oldDesk = model.data("desk")
        val before = ui.onNodeWithText("Continue with Kite").fetchSemanticsNode().boundsInRoot
        val release = CompletableDeferred<Unit>()
        transport.blockSetup = release
        transport.desk().put("mode_reason", "INVENTED refreshed account")
        ui.runOnUiThread { model.refreshInBackground() }
        ui.waitUntil(5000) { transport.setupEntered }
        assertFalse(model.state.value.busy)
        assertSame(oldDesk, model.data("desk"))
        ui.onNodeWithText("Continue with Kite").assertIsEnabled()
        assertEquals(before, ui.onNodeWithText("Continue with Kite").fetchSemanticsNode().boundsInRoot)
        ui.onAllNodes(SemanticsMatcher.keyIsDefined(SemanticsProperties.ProgressBarRangeInfo)).assertCountEquals(0)
        release.complete(Unit)
        ui.waitUntil(5000) { model.data("desk").text("mode_reason") == "INVENTED refreshed account" }
        assertTrue(transport.posts.isEmpty())
        assertEquals("23998.77", model.data("desk").obj("account").text("cash"))
    }

    @Test fun openingAReviewCancelsQuietReadWithoutDisablingOrReplacingTheReview() {
        transport.blockSetup = CompletableDeferred()
        ui.runOnUiThread { model.refreshInBackground() }
        ui.waitUntil(5000) { transport.setupEntered }
        val release = transport.blockSetup!!
        transport.blockSetup = null
        transport.allowPaperModes()
        act { model.chooseMode("approval") }
        assertNotNull(model.state.value.review)
        assertFalse(model.state.value.busy)
        release.complete(Unit)
        ui.waitForIdle()
        assertNotNull(model.state.value.review)
        assertTrue(transport.posts.isEmpty())
    }

    @Test fun environmentSelectorExplainsUnavailableRealAndCannotChangeAccount() {
        val before = model.data("desk").toString()
        ui.onNodeWithText("Paper", useUnmergedTree = true).performClick()
        ui.onNodeWithText("Trading environment").assertIsDisplayed()
        ui.onNodeWithText("Paper · active").assertIsDisplayed()
        ui.onNodeWithText("Real · unavailable").assertIsDisplayed()
        ui.onNodeWithContentDescription("Real trading unavailable").assertIsNotEnabled()
        ui.onNodeWithText("Real-order execution", substring = true).assertIsDisplayed()
        screenshot("environment")
        ui.onNodeWithText("Done").performClick()
        assertEquals(before, model.data("desk").toString())
        assertEquals("manual", model.data("desk").text("mode"))
        assertTrue(transport.posts.isEmpty())
    }

    @Test fun lockAndInitialLoadingUseTheSameBrandWithoutInventingBalances() {
        ui.runOnUiThread { ui.activity.setContent { TraderTheme {
            UnlockScreen(AppState(paired = true), model, BiometricGate(ui.activity))
        } } }
        ui.onNodeWithText("Agentic Trader").assertIsDisplayed()
        ui.onNodeWithText("Unlock with biometrics").assertIsDisplayed()
        ui.onNodeWithContentDescription("Agentic Trader logo").assertIsDisplayed()
        screenshot("lock-brand")
        ui.runOnUiThread { ui.activity.setContent { TraderTheme { WorkspaceLoadingScreen(true) } } }
        ui.onNodeWithText("Opening your workspace").assertIsDisplayed()
        ui.onNodeWithText("Available cash").assertDoesNotExist()
        screenshot("loading-brand")
    }

    @Test fun initialReadShowsBrandedLoadingUntilTheWholeAccountArrives() {
        val release = CompletableDeferred<Unit>()
        ui.runOnUiThread {
            store.clear()
            transport = FixtureTransport(ui.activity.application)
            transport.blockSetup = release
            model = TraderViewModel(ui.activity.application, transport)
            store.put("native-qa", model)
            ui.activity.setContent { TraderTheme { TraderApp(model, BiometricGate(ui.activity), {}) } }
        }
        ui.waitUntil(5000) { transport.setupEntered }
        assertTrue(model.state.value.busy)
        assertFalse(model.data("desk").has("account"))
        ui.onNodeWithText("Opening your workspace").assertIsDisplayed()
        ui.onNodeWithText("Available cash").assertDoesNotExist()
        release.complete(Unit)
        ready()
        ui.onNodeWithText("₹25,018.77").assertExists()
        assertTrue(transport.posts.isEmpty())
    }

    @Test fun unsupportedRealAccountCannotPublishDataOrAuthorizeActions() {
        val before = model.data("desk")
        transport.desk().getJSONObject("account").put("mode", "real")
        act { model.refresh() }
        assertSame(before, model.data("desk"))
        assertTrue(model.state.value.stale)
        assertFalse(model.canAct())
        assertTrue(model.state.value.error!!.contains("paper account only"))
        assertTrue(transport.posts.isEmpty())
    }

    @Test fun blockedApprovalShowsTimeAndNextStepsWithoutSubmittingAnInstruction() {
        transport.waitingForEntry()
        act { model.navigate(Page.PAPER) }
        ui.onNodeWithText("Approval · review every proposal").performScrollTo().assertIsEnabled().performClick()
        ready()
        ui.onNodeWithText("Before choosing Approval").assertIsDisplayed()
        ui.onNode(hasText("Next reviewed entry start:", substring = true) and hasAnyAncestor(isDialog())).assertIsDisplayed()
        ui.onNode(hasText("Wait for fresh usable prices") and hasAnyAncestor(isDialog())).performScrollTo().assertIsDisplayed()
        assertEquals("manual", model.data("desk").text("mode"))
        assertNull(model.state.value.review)
        assertTrue(transport.posts.isEmpty())
        screenshot("approval-waiting")
        ui.onNodeWithText("Got it").performClick()
    }

    @Test fun readinessDialogUpdatesQuietlyAndStillRequiresReviewAndConfirmation() {
        transport.waitingForEntry()
        act { model.navigate(Page.PAPER) }
        act { model.chooseMode("approval") }
        assertNotNull(model.state.value.modeHelp)
        transport.allowPaperModes()
        ui.runOnUiThread { model.refreshInBackground() }
        ui.waitUntil(5000) { modeIsReady(model.data("desk")) }
        ui.onNodeWithText("Approval is ready to review").assertIsDisplayed()
        assertNull(model.state.value.review)
        assertTrue(transport.posts.isEmpty())
        ui.onNodeWithText("Review Approval mode").performClick()
        ready()
        ui.onNodeWithText("Confirm").assertIsNotEnabled()
        ui.onNodeWithText("I reviewed the displayed values, effects and limitations.").performScrollTo().performClick()
        ui.onNodeWithText("Confirm").performClick()
        ready()
        assertEquals(listOf("/api/desk/mode"), transport.posts.map { it.first })
        assertEquals("approval", transport.posts.single().second.text("mode"))
        assertEquals("23998.77", model.data("desk").obj("account").text("cash"))
    }

    @Test fun blockedModeOffersTheRelevantSetupScreenWithoutActivatingAnything() {
        transport.waitingForEntry(actionRequired = true)
        act { model.navigate(Page.PAPER) }
        act { model.chooseMode("approval") }
        ui.onNode(hasText("Open Broker & data") and hasAnyAncestor(isDialog())).performScrollTo().performClick()
        ready()
        assertEquals(Page.BROKER, model.state.value.page)
        assertNull(model.state.value.modeHelp)
        assertTrue(transport.posts.isEmpty())
    }

    @Test fun failedFreshReadCannotOpenAModeConfirmationUsingOldReadyData() {
        transport.allowPaperModes()
        act { model.navigate(Page.PAPER) }
        transport.failDesk = true
        act { model.chooseMode("approval") }
        assertTrue(model.state.value.stale)
        assertNull(model.state.value.review)
        assertTrue(transport.posts.isEmpty())
    }

    @Test fun changedReadinessAtConfirmationShowsCurrentReasonsWithoutRetryingTheWrite() {
        transport.allowPaperModes()
        act { model.navigate(Page.PAPER) }
        act { model.chooseMode("approval") }
        transport.blockModeOnConfirm = true
        act { model.confirmReview(true) }
        assertEquals(1, transport.posts.count { it.first == "/api/desk/mode" })
        assertEquals("manual", model.data("desk").text("mode"))
        assertNotNull(model.state.value.modeHelp)
        assertNull(model.state.value.review)
        ui.onNodeWithText("Before choosing Approval").assertIsDisplayed()
        assertEquals("23998.77", model.data("desk").obj("account").text("cash"))
    }

    @Test fun officialBasketCoversFiftyAndDoesNotAskForManualStockNames() {
        transport.officialBasket()
        act { model.navigate(Page.BROKER) }
        ui.onNodeWithText("Automatic Nifty 50 basket").performScrollTo().assertIsDisplayed()
        ui.onNodeWithText("Following the official Nifty 50 basket · 50 subscribed stocks.").performScrollTo().assertIsDisplayed()
        ui.onNodeWithText("NSE symbols, comma separated").assertDoesNotExist()
        assertTrue(transport.posts.isEmpty())
        screenshot("nifty50-basket")
        act { model.navigate(Page.PAPER) }
        ui.onNodeWithText("Nifty 50 · 50 stocks monitored").performScrollTo().assertIsDisplayed()
        ui.onNodeWithText("50 stocks checked · 50 history states ready · 0 warming up").performScrollTo().assertIsDisplayed()
        assertTrue(transport.posts.isEmpty())
    }

    @Test fun officialBasketChangeHasOneConfirmationAndNeverRequestsAChosenTen() {
        act { model.navigate(Page.BROKER) }
        ui.onNodeWithText("Use / refresh official Nifty 50").performScrollTo().performClick()
        ui.onNodeWithText("Use the official Nifty 50 basket?").assertIsDisplayed()
        ui.onNodeWithText("Confirm").assertIsNotEnabled()
        assertTrue(transport.posts.isEmpty())
        ui.onNodeWithText("I reviewed the displayed values, effects and limitations.").performScrollTo().performClick()
        ui.onNodeWithText("Confirm").performClick()
        ready()
        assertEquals(listOf("/api/desk/universe/nifty50"), transport.posts.map { it.first })
        assertFalse(transport.posts.single().second.has("symbols"))
        assertEquals("23998.77", model.data("desk").obj("account").text("cash"))
    }

    @Test fun dailyFlowSkipsAuditedDataAndOpensOnlyOneReviewWithSavedPolicy() {
        transport.dailyData()
        act { model.refresh() }
        assertEquals(2, DailyJourney.step(model.state.value))
        ui.onNodeWithText("Step 3 of 4 · Review").assertIsDisplayed()
        ui.onNodeWithText("Review & continue").assertIsEnabled().performClick()
        ready()
        assertEquals("Review today's paper setup", model.state.value.review!!.title)
        ui.onNodeWithText("Confirm and prepare").assertIsNotEnabled()
        assertEquals(listOf("/api/desk/preparation/guided/preview"), transport.posts.map { it.first })
        act { model.cancelReview() }
        act { model.refresh() }
        assertNull(model.state.value.review)
        assertEquals(1, transport.posts.size)
        screenshot("daily-review")
    }

    @Test fun dailyFlowWaitsForDownloadThenAdvancesHereAndNeverArmsTrading() {
        transport.dailyData()
        transport.auditReport!!.obj("source_validation").put("coverage_valid", false)
        act { model.refresh() }
        ui.onNodeWithText("Prepare & continue").assertIsEnabled().performClick()
        ready()
        assertEquals(Page.HOME, model.state.value.page)
        assertEquals(1, transport.posts.count { it.first == "/api/desk/preparation/download" })
        assertFalse(transport.posts.any { it.first == "/api/setup/profile" })
        assertTrue(model.state.value.journeyRunning)
        screenshot("daily-downloading")
        transport.finishDailyDownload()
        act { model.refresh() }
        assertEquals("Review today's paper setup", model.state.value.review!!.title)
        act { model.confirmReview(false) }
        assertFalse(transport.posts.any { it.first.endsWith("/confirm") })
        act { model.confirmReview(true) }
        assertEquals(Page.HOME, model.state.value.page)
        assertEquals(3, DailyJourney.step(model.state.value))
        ui.onNodeWithText("Connecting to Zerodha…", substring = true).assertIsDisplayed()
        assertEquals("manual", model.data("desk").text("mode"))
        assertEquals("23998.77", model.data("desk").obj("account").text("cash"))
        assertFalse(transport.posts.any { it.first == "/api/desk/mode" })
        screenshot("daily-trade")
        assertEquals("", model.state.value.journeyPolicy)
        transport.desk().put("strategy_mode", "rules_ml")
        act { model.refresh() }
        assertEquals("rules_ml", DailyJourney.policy(model.state.value))
    }

    @Test fun firstPolicyChoiceIsRequiredAndAdvancedControlsRemainAvailable() {
        transport.dailyData()
        transport.desk().put("strategy_mode", "unconfigured")
        act { model.refresh() }
        ui.onNodeWithText("Decision policy · choose once").assertExists()
        ui.onNodeWithText("Review & continue").assertIsNotEnabled()
        act { model.journeyPolicy("rules") }
        ui.onNodeWithText("Review & continue").assertIsEnabled()
        act { model.navigate(Page.STRATEGY) }
        ui.onNodeWithText("Discovery universe").assertDoesNotExist()
        ui.onNodeWithText("Advanced preparation & sources").performScrollTo().performClick()
        ui.onNodeWithText("Discovery universe").performScrollTo().assertIsDisplayed()
        assertTrue(transport.posts.isEmpty())
    }

    @Test fun dailyAuditIsReadOnlyCachedAndInvalidatedAtReviewedClose() {
        transport.dailyData(installed = true)
        act { model.refresh() }
        val before = transport.gets.count { it == "/api/desk/preparation/audit" }
        repeat(2) { act { model.refresh() } }
        assertEquals(before, transport.gets.count { it == "/api/desk/preparation/audit" })
        transport.desk().put("observed_at", "2026-10-28T10:00:00+00:00")
        act { model.refresh() }
        assertEquals(before + 1, transport.gets.count { it == "/api/desk/preparation/audit" })
        assertTrue(transport.posts.isEmpty())
        assertEquals("23998.77", model.data("desk").obj("account").text("cash"))
    }

    @Test fun continueChecksSavedAccessOnceAndAttachesExistingDownloadWithoutDuplicatingIt() {
        ui.onNodeWithText("Step 1 of 4 · Access").assertIsDisplayed()
        act { model.continueDay() }
        assertEquals(1, transport.posts.count { it.first == "/api/setup/profile" })
        assertEquals(1, transport.posts.count { it.first == "/api/desk/preparation/download" })
        assertEquals(Page.HOME, model.state.value.page)
        act { model.continueDay() }
        assertEquals(1, transport.posts.count { it.first == "/api/setup/profile" })
        assertEquals(1, transport.posts.count { it.first == "/api/desk/preparation/download" })
        assertFalse(transport.posts.any { it.first.contains("/mode") || it.first.contains("/guided/") })
        assertEquals("23998.77", model.data("desk").obj("account").text("cash"))
    }

    @Test fun installedSetupNeedsOnlyOneConnectionReviewAndShowsFailureWithoutRetry() {
        transport.dailyData(installed = true)
        act { model.refresh() }
        ui.onNodeWithText("Review market-data connection").performClick()
        ready()
        assertEquals("Connect market data?", model.state.value.review!!.title)
        act { model.confirmReview(false) }
        assertTrue(transport.posts.isEmpty())
        act { model.confirmReview(true) }
        assertEquals(listOf("/api/setup/connect"), transport.posts.map { it.first })
        transport.failConnection()
        act { model.refresh() }
        ui.onNodeWithText("Resolve connection").assertIsDisplayed()
        assertEquals(1, transport.posts.size)
        assertEquals(3, DailyJourney.step(model.state.value))
        assertEquals("manual", model.data("desk").text("mode"))
        screenshot("daily-connection-failure")
    }

    @Test fun slowAutomaticSourceCheckNeverShowsGlobalBusyBarOrHidesLoadedAccount() {
        val release = CompletableDeferred<Unit>()
        ui.runOnUiThread {
            store.clear()
            transport = FixtureTransport(ui.activity.application)
            transport.dailyData(installed = true)
            transport.blockAudit = release
            model = TraderViewModel(ui.activity.application, transport)
            store.put("native-qa", model)
            ui.activity.setContent { TraderTheme { TraderApp(model, BiometricGate(ui.activity), {}) } }
        }
        ready()
        assertFalse(transport.auditEntered)
        ui.runOnUiThread { model.refreshInBackground() }
        ui.waitUntil(5000) { transport.auditEntered }
        assertFalse(model.state.value.busy)
        assertTrue(model.state.value.journeyChecking)
        ui.onNodeWithText("₹25,018.77").assertExists()
        ui.onAllNodes(SemanticsMatcher.keyIsDefined(SemanticsProperties.ProgressBarRangeInfo)).assertCountEquals(0)
        act { model.showEnvironment(true) } // Cancel the quiet audit without poisoning reuse checks.
        assertFalse(model.state.value.busy)
        release.complete(Unit)
        act { model.showEnvironment(false) }
        ui.runOnUiThread { model.refreshInBackground() }
        ui.waitUntil(5000) { !model.state.value.journeyChecking && DailyJourney.dataReady(model.state.value) }
        assertFalse(model.state.value.stale)
        assertNull(model.state.value.error)
    }

    @Test fun sourceCheckFailureKeepsFreshAccountAndRecoversWithoutDownloadOrTrade() {
        transport.dailyData(installed = true)
        transport.failAudit = true
        ui.runOnUiThread { model.refreshInBackground() }
        ui.waitUntil(5000) { model.state.value.journeyCheckError != null }
        assertFalse(model.state.value.stale)
        assertNull(model.state.value.error)
        assertFalse(DailyJourney.dataReady(model.state.value))
        assertEquals("23998.77", model.data("desk").obj("account").text("cash"))
        assertTrue(transport.posts.isEmpty())
        transport.failAudit = false
        ui.runOnUiThread { model.refreshInBackground() }
        ui.waitUntil(5000) { DailyJourney.dataReady(model.state.value) }
        assertNull(model.state.value.journeyCheckError)
        assertTrue(transport.posts.isEmpty())
    }

    @Test fun discoverShowsSavedResearchImmediatelyAndRefreshesWithoutATopLoadingBar() {
        val oldDesk = model.data("desk")
        val release = CompletableDeferred<Unit>()
        transport.blockDesk = release
        transport.desk().put("mode_reason", "INVENTED quietly updated Discover")
        act { model.navigate(Page.DISCOVER) }
        ui.waitUntil(5000) { transport.deskEntered }
        assertEquals(Page.DISCOVER, model.state.value.page)
        assertFalse(model.state.value.busy)
        assertEquals("", model.state.value.progress)
        assertSame(oldDesk, model.data("desk"))
        ui.onNodeWithText("Find stocks to research").assertExists()
        ui.onAllNodes(SemanticsMatcher.keyIsDefined(SemanticsProperties.ProgressBarRangeInfo)).assertCountEquals(0)
        release.complete(Unit)
        ui.waitUntil(5000) { model.data("desk").text("mode_reason") == "INVENTED quietly updated Discover" }
        assertFalse(model.state.value.stale)
        assertTrue(transport.posts.isEmpty())
    }

    private class FixtureTransport(app: Application) : Transport {
        private val fixtures = JSONObject(app.assets.open("demo.json").bufferedReader().use { it.readText() })
        val posts = CopyOnWriteArrayList<Pair<String, JSONObject>>()
        val gets = CopyOnWriteArrayList<String>()
        var blockSetup: CompletableDeferred<Unit>? = null
        var blockDesk: CompletableDeferred<Unit>? = null
        @Volatile var deskEntered = false
        @Volatile var setupEntered = false
        fun desk(): JSONObject = fixtures.getJSONObject("/api/desk")
        var auditReport: JSONObject? = null
        var blockAudit: CompletableDeferred<Unit>? = null
        @Volatile var auditEntered = false
        var failAudit = false
        fun officialBasket() {
            val stocks = org.json.JSONArray((0 until 50).map { json("symbol" to "NSE:DEMO$it", "token" to 257 + it * 256) })
            fixtures.getJSONObject("/api/setup").put("automatic_universe", "nifty50").put("selected", stocks).put("stream_limit", 50)
            desk().put("monitoring", json("universe" to "nifty50", "monitored_count" to 50, "execution_covered_count" to 50))
            desk().put("analysis_status", json("tracked" to 50, "seeded" to 50, "warming_up" to 0, "symbols" to org.json.JSONArray()))
        }
        var blockModeOnConfirm = false
        var failDesk = false
        fun allowPaperModes() {
            desk().put("blockers", org.json.JSONArray())
            desk().obj("readiness").put("can_start", true).put("mode_guidance", json(
                "schema_version" to 1, "state" to "ready", "title" to "Ready to review a paper mode",
                "summary" to "Review and confirm a paper mode.", "now_ist" to "2026-10-29T09:30:00+05:30",
                "items" to org.json.JSONArray()))
        }
        fun waitingForEntry(actionRequired: Boolean = false) {
            desk().put("blockers", org.json.JSONArray(listOf(if (actionRequired) "FEED_DISCONNECTED" else "OUTSIDE_ENTRY_WINDOW")))
            val item = if (actionRequired) json("title" to "Connect market data", "detail" to "Review the saved session and connection.", "target" to "broker")
                else json("title" to "Wait for fresh usable prices", "detail" to "Wait for new valid quotes after the reviewed entry start.")
            desk().obj("readiness").put("can_start", false).put("mode_guidance", json(
                "schema_version" to 1, "state" to if (actionRequired) "action_required" else "waiting",
                "title" to "Waiting for the next entry session", "summary" to "Your setup can stay in place. Status updates automatically.",
                "now_ist" to "2026-10-29T07:45:00+05:30", "next_entry_at" to "2026-10-29T09:30:00+05:30",
                "entry_window" to "09:30–14:30 IST", "items" to org.json.JSONArray(listOf(item))))
        }
        fun dailyData(installed: Boolean = false) {
            recentDownload()
            desk().put("strategy_mode", "rules")
            desk().obj("preparation").obj("download_prerequisites").put("session_verified", true)
            val setup = fixtures.getJSONObject("/api/setup")
            setup.put("profile_verified_this_run", true).put("profile_checked_at", desk().text("observed_at"))
            val job = desk().obj("preparation").obj("job")
            job.put("universe", "nifty50").put("state", if (installed) "installed" else "ready_for_review")
            auditReport!!.put("preparation", JSONObject(job.toString()))
            desk().obj("readiness").put("checks", org.json.JSONArray(listOf(json("key" to "strategy", "ready" to installed))))
        }
        fun finishDailyDownload() { dailyData() }
        fun failConnection() {
            fixtures.getJSONObject("/api/setup").put("stream_requested", true).put("feed_connected", false)
                .put("feed_diagnostics", json("state" to "failed", "failures" to 3))
        }
        var failMode = false
        var suspendMode = false
        fun recentDownload(): String {
            val identity = "c".repeat(32)
            val job = json("job_id" to identity, "state" to "ready_for_review", "universe" to "nifty100",
                "snapshot_at" to "2026-10-28T03:25:00+00:00", "history_end" to "2026-10-27")
            fixtures.getJSONObject("/api/desk").getJSONObject("preparation").put("job", job)
            auditReport = json("preparation" to JSONObject(job.toString()), "source_validation" to json(
                "hashes_valid" to true, "same_ist_date" to true, "coverage_valid" to true))
            return identity
        }
        override suspend fun request(method: String, path: String, token: String?, body: JSONObject?): JSONObject {
            if (method == "GET") {
                gets.add(path)
                if (path == "/api/desk" && blockDesk != null) { deskEntered = true; blockDesk!!.await() }
                if (path == "/api/desk" && failDesk) throw ApiFailure(0, "INVENTED read failed", endpoint = path)
                if (path == "/api/setup" && blockSetup != null) { setupEntered = true; blockSetup!!.await() }
                if (path == "/api/desk/preparation/audit") {
                    auditEntered = true
                    blockAudit?.await()
                    if (failAudit) throw ApiFailure(0, "INVENTED source check timeout", endpoint = path)
                    return JSONObject((auditReport ?: json(
                    "source_validation" to JSONObject.NULL, "preparation" to fixtures.getJSONObject("/api/desk").obj("preparation").obj("job"))).toString())
                }
                return JSONObject((fixtures.optJSONObject(path.substringBefore('?')) ?: JSONObject()).toString())
            }
            posts.add(path to JSONObject((body ?: JSONObject()).toString()))
            if (path == "/api/desk/mode" && blockModeOnConfirm) { waitingForEntry(); throw ApiFailure(409, "INVENTED readiness changed", endpoint = path) }
            if (path == "/api/desk/mode" && suspendMode) awaitCancellation()
            if (path == "/api/desk/mode" && failMode) throw ApiFailure(0, "Invented lost response", true, path)
            return when (path) {
                "/api/setup/profile" -> {
                    fixtures.getJSONObject("/api/setup").put("profile_verified_this_run", true).put("profile_checked_at", desk().text("observed_at"))
                    desk().obj("preparation").obj("download_prerequisites").put("session_verified", true)
                    JSONObject(fixtures.getJSONObject("/api/setup").toString())
                }
                "/api/desk/preparation/download" -> {
                    val job = json("job_id" to "d".repeat(32), "universe" to body!!.text("universe"), "state" to "downloading")
                    desk().obj("preparation").put("job", job)
                    json("job" to job)
                }
                "/api/desk/preparation/guided/preview" -> json("preview_sha256" to "f".repeat(64), "plan" to json("job_id" to desk().obj("preparation").obj("job").text("job_id"), "strategy_mode" to body!!.text("strategy_mode")))
                "/api/setup/connect" -> {
                    fixtures.getJSONObject("/api/setup").put("stream_requested", true)
                    json("message" to "INVENTED connecting")
                }
                "/api/desk/preparation/guided/confirm" -> {
                    dailyData(installed = true)
                    fixtures.getJSONObject("/api/setup").put("stream_requested", true)
                    json("message" to "INVENTED setup installed; connecting")
                }
                else -> json("message" to "INVENTED test instruction recorded")
            }
        }
        override fun cancel() = Unit
    }
}
