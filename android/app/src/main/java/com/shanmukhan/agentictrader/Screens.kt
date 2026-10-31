package com.shanmukhan.agentictrader

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import org.json.JSONArray
import org.json.JSONObject
import android.os.SystemClock
import kotlinx.coroutines.delay
import java.time.Duration
import java.time.Instant

@Composable fun NativeScreen(state: AppState, model: TraderViewModel, external: (String) -> Unit) {
    when (state.page) {
        Page.HOME -> HomeScreen(state, model)
        Page.DISCOVER -> DiscoveryScreen(state, model)
        Page.WATCHLIST -> WatchlistScreen(state, model)
        Page.ANALYSIS -> AnalysisScreen(state, model, external)
        Page.STRATEGY -> StrategyScreen(state, model, external)
        Page.PAPER -> PaperScreen(state, model)
        Page.PORTFOLIO -> PortfolioScreen(state, model)
        Page.PURCHASES -> PurchasesScreen(state, model)
        Page.HISTORY -> HistoryScreen(state, model)
        Page.POLICY -> PolicyScreen(state, model)
        Page.BACKTEST -> BacktestScreen(state, model, external)
        Page.RISK -> RiskScreen(state, model, external)
        Page.BROKER -> BrokerScreen(state, model, external)
        Page.SETTINGS -> SettingsScreen(state, model)
        Page.LEARN -> LearnScreen(model, external)
        Page.SECURITY -> SecurityScreen(state, model)
        Page.MORE -> MoreScreen(state, model)
    }
}

@Composable private fun HomeScreen(state: AppState, model: TraderViewModel) {
    val desk = model.data("desk"); val account = desk.obj("account")
    DailyJourneyCard(state, model)
    Section("Your paper account", if (desk.text("horizon") == "long_term") "Long-term · virtual INR" else "Intraday · virtual INR") {
        Metric("Portfolio value", decimalMoney(account.text("equity")))
        HorizontalDivider(color = Line)
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(18.dp)) {
            Metric("Available cash", decimalMoney(account.text("available_cash")), Modifier.weight(1f))
            Metric("Today's P&L", decimalMoney(account.text("day_pnl")), Modifier.weight(1f))
        }
        if (!account.optBoolean("valuation_fresh")) Hint("Some holding prices are stale or unavailable. Inspect valuation coverage before using this estimate.")
        Text("Checked ${istTime(desk.text("observed_at", ""))}", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }

}

@Composable fun Readiness(desk: JSONObject) {
    Section("Readiness & next steps") {
        val checks = desk.obj("readiness").rows("checks")
        if (checks.isEmpty()) Text("Readiness has not been established. Refresh server status before taking action.")
        checks.forEach { check ->
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Icon(if (check.optBoolean("ready")) Icons.Outlined.CheckCircle else Icons.Outlined.Info, null,
                    tint = if (check.optBoolean("ready")) Teal else MaterialTheme.colorScheme.onSurfaceVariant)
                Column(verticalArrangement = Arrangement.spacedBy(3.dp)) {
                    Text(check.text("title"), fontWeight = FontWeight.SemiBold)
                    Text(check.text("detail"), style = MaterialTheme.typography.bodyMedium)
                }
            }
        }
        if (checks.isEmpty()) desk.strings("blockers").forEach { Text("• ${friendly(it)}") }
    }
}

@Composable private fun DiscoveryScreen(state: AppState, model: TraderViewModel) {
    val discovery = model.data("views").obj("discovery")
    var search by remember { mutableStateOf("") }; var filter by remember { mutableStateOf("all") }
    Section("Find stocks to research", "Saved, reviewed research. Screening strength is not a buy signal or a profit forecast.") {
        Field("Search symbol", search, { search = it })
        Choice("Show", filter, listOf("all" to "All stocks", "eligible" to "Screen passed", "subscribed" to "Monitored execution stocks"), { filter = it })
        Text("Research as of ${istTime(discovery.text("as_of", ""))}", style = MaterialTheme.typography.labelMedium)
    }
    val rows = discovery.rows("rows").filter { it.text("symbol").contains(search, true) && when (filter) {
        "eligible" -> it.optBoolean("eligible") || it.text("status") in listOf("eligible", "research_candidate")
        "subscribed" -> it.optBoolean("subscribed")
        else -> true
    } }
    if (rows.isEmpty()) Section("") { EmptyState("No matching saved research", if (discovery.text("state") == "missing") "Prepare and review strategy data to establish the discovery universe." else "Change the search or filter. No substitute rankings are generated.") }
    var shown by remember(search, filter) { mutableIntStateOf(30) }
    rows.take(shown).forEach { row ->
        Section(row.text("symbol"), if (row.optBoolean("subscribed")) "In your execution watchlist" else "Research universe") {
            Text(friendly(row.text("status", if (row.optBoolean("eligible")) "screen passed" else "review evidence")))
            row.strings("reasons").forEach { Text("• ${friendly(it)}", style = MaterialTheme.typography.bodyMedium) }
            Action("Inspect price & indicators", !state.busy, secondary = true) { model.selectSymbol(row.text("symbol")) }
            DetailTree(JSONObject(row.toString()).apply { remove("symbol"); remove("reasons") })
        }
    }
    if (rows.size > shown) Action("Show more · ${rows.size} saved stocks", secondary = true) { shown += 30 }
    DetailCard("Screen rules, ranking & data limitations", JSONObject(discovery.toString()).apply { remove("rows") })
}

@Composable private fun StrategyScreen(state: AppState, model: TraderViewModel, external: (String) -> Unit) {
    val desk = model.data("desk"); val prep = desk.obj("preparation"); val job = prep.obj("job")
    val requirements = prep.obj("download_prerequisites")
    var universe by remember { mutableStateOf("nifty50") }
    var policy by remember { mutableStateOf(if (desk.text("strategy_mode") in listOf("rules", "rules_ml")) desk.text("strategy_mode") else "") }
    DailyJourneyCard(state, model)
    var advanced by remember { mutableStateOf(false) }
    TextButton({ advanced = !advanced }, Modifier.fillMaxWidth()) { Text(if (advanced) "Hide advanced preparation controls" else "Advanced preparation & sources") }
    if (advanced) {
    Section("Today's setup", "Automatic checks and downloads stop at your review. They never activate a trading mode.") {
        Text("Kite session: " + if (requirements.optBoolean("session_verified")) "verified today" else "verification required")
        Text("NSE catalog: ${requirements.optInt("catalog_count")} supported instruments")
        Choice("Discovery universe", universe, listOf("nifty50" to "Nifty 50 · automatic official basket", "nifty100" to "Nifty 100 · broader research", "nifty500" to "Nifty 500 · broader coverage"), { universe = it })
        Text("This checks and reuses a valid download for the selected universe. Use Download fresh sources & history only when you want another download.", style = MaterialTheme.typography.bodyMedium)
        if (desk.text("mode") != "manual") Hint("Preparation requires Manual mode. Change it explicitly in Paper trading.")
        Action("Check & prepare today", model.canAct() && desk.text("mode") == "manual") { model.prepareToday(universe) }
        Action("Broker connection & recovery", !state.busy, secondary = true) { model.navigate(Page.BROKER) }
    }
    if (job.length() > 0) Section("Data preparation · ${friendly(job.text("state"))}") {
        val running = job.text("state") == "downloading"
        if (running) {
            Text(when (job.text("stage")) { "broker_session" -> "Checking Kite session"; "official_sources" -> "Reading official sources"; else -> "Reading completed daily candles" })
            if (job.optInt("total") > 0) LinearProgressIndicator(progress = { job.optInt("completed").toFloat() / job.optInt("total").coerceAtLeast(1) }, modifier = Modifier.fillMaxWidth())
            else LinearProgressIndicator(Modifier.fillMaxWidth())
            Action("Cancel download", model.canAct() && !job.optBoolean("cancel_requested"), secondary = true) {
                model.reviewPost("Cancel the download?", "The current bounded read can finish before cancellation. Incomplete evidence will not be installed.", "/api/desk/preparation/cancel", JSONObject())
            }
        }
        Text("${job.optInt("completed")} / ${job.optInt("total")} stocks read · ${job.optInt("eligible")} with eligible history")
        if (job.text("error", "").isNotBlank()) Hint("Download stopped: ${friendly(job.text("error"))}. Inspect source exclusions and broker access before another download.", error = true)
        DetailTree(json("history_start" to job.opt("history_start"), "history_end" to job.opt("history_end"), "excluded" to job.optJSONArray("excluded")))
        Action("Download fresh sources & history", model.canAct() && !running, secondary = true) { model.prepareToday(universe, true) }
    }
    if (job.text("state") in listOf("ready_for_review", "installed")) Section("Choose once, then review") {
        Choice("Decision policy", policy, listOf("rules" to "Rules only · experimental paper policy") +
            if (prep.optBoolean("ml_configured")) listOf("rules_ml" to "Rules + independently validated ML") else emptyList(), { policy = it })
        Text("A download does not train or validate an ML model. Current constituents support prospective screening, not historical profitability claims.", style = MaterialTheme.typography.bodyMedium)
        Action("Review and finish setup", model.canAct() && policy.isNotBlank()) { model.guidedReview(policy) }
    }
    DetailCard("Sources, calendar, coverage & exclusions", prep, external = external)
    AdvancedInstall(state, model, job, policy)
    val shortlist = desk.obj("shortlist")
    if (shortlist.length() > 0) Section("Execution shortlist", "Every held stock must remain represented. Changing the shortlist does not submit an order.") {
        DetailTree(shortlist)
        Action("Review and apply ranked shortlist", model.canAct() && shortlist.text("preview_sha256", "").isNotBlank()) {
            model.reviewPost("Apply this execution shortlist?", "Manual mode, a disconnected feed and resolved pending orders are required. All held stocks are retained.",
                "/api/desk/shortlist", json("preview_sha256" to shortlist.text("preview_sha256")), shortlist)
        }
    }
    }
}

@Composable private fun AdvancedInstall(state: AppState, model: TraderViewModel, job: JSONObject, policy: String) {
    var open by remember { mutableStateOf(false) }
    var calendar by remember(job.text("job_id")) { mutableStateOf(job.text("calendar_csv", "")) }
    var reference by remember { mutableStateOf("") }
    var calendarReviewed by remember { mutableStateOf(false) }; var basis by remember { mutableStateOf(false) }; var policyReviewed by remember { mutableStateOf(false) }; var correction by remember { mutableStateOf(false) }
    val prep = model.data("desk").obj("preparation")
    Section("") {
        TextButton({ open = !open }) { Text("Advanced calendar & separate installation") }
        if (open) {
            Hint("Use only when the normal combined review needs a calendar correction. Existing used session history cannot be overwritten.")
            Field("Reviewed session calendar · CSV", calendar, { calendar = it }, multiline = true)
            Field("Review reference", reference, { reference = it }, "Cite the actual source/calendar/basis review.")
            Acknowledge("I reviewed every calendar date and session time.", calendarReviewed, { calendarReviewed = it })
            Acknowledge("I reviewed price-basis and action coverage.", basis, { basis = it })
            Acknowledge("I reviewed the selected policy and its limitations.", policyReviewed, { policyReviewed = it })
            if (prep.optBoolean("can_correct_unused_calendar")) {
                DetailTree(json("calendar_conflicts" to prep.optJSONArray("calendar_conflicts")))
                Acknowledge("I approve the listed corrections to unused account hours.", correction, { correction = it })
            }
            Action("Review separate installation", model.canAct() && job.text("state") == "ready_for_review" && policy.isNotBlank() && reference.trim().length >= 3 && calendarReviewed && basis && policyReviewed) {
                val body = json("preview_sha256" to job.text("preview_sha256"), "revision" to model.data("desk").text("revision"), "strategy_mode" to policy,
                    "calendar_csv" to calendar, "reference" to reference.trim(), "calendar_reviewed" to true,
                    "basis_reviewed" to true, "policy_reviewed" to true, "correct_unused_calendar" to correction)
                model.reviewPost("Install the separately reviewed strategy?", "This installs the displayed calendar and strategy. Manual remains selected. Price-basis reviews for current execution remain separate.", "/api/desk/preparation/install", body)
            }
        }
    }
}

@Composable private fun PaperScreen(state: AppState, model: TraderViewModel) {
    val desk = model.data("desk")
    var elapsed by remember { mutableLongStateOf(SystemClock.elapsedRealtime()) }
    LaunchedEffect(Unit) { while (true) { delay(1000); elapsed = SystemClock.elapsedRealtime() } }
    val guidance = tradeGuidance(desk)
    Section("Your trading mode", "Current: ${friendly(desk.text("mode"))}. Feed connection alone cannot authorize trading.") {
        Text(guidance.text("title"), fontWeight = FontWeight.SemiBold, color = Teal)
        val nextEntry = guidance.text("next_entry_at", "")
        if (nextEntry.isNotBlank()) Text("Next reviewed entry start: ${istTime(nextEntry)}")
        Text(guidance.text("summary"), style = MaterialTheme.typography.bodyMedium)
        listOf("manual" to "Manual · no new strategy orders", "approval" to "Approval · review every proposal", "automatic" to "Automatic · eligible paper orders").forEach { (mode, label) ->
            Action(label, model.canAct() && desk.text("mode") != mode, secondary = mode != "manual") { model.chooseMode(mode) }
        }
        Text(desk.text("mode_reason", ""), style = MaterialTheme.typography.bodyMedium)
    }
    Section("Your next step") { ModeGuidanceContent(state, model) }
    Readiness(desk)
    val monitoring = desk.obj("monitoring")
    if (monitoring.length() > 0) Section("Automatic stock coverage") {
        Text("${universeName(monitoring.text("universe"))} · ${monitoring.optInt("monitored_count")} stocks monitored")
        Text("${monitoring.optInt("execution_covered_count")} have reviewed execution-history coverage. Other members stay visible with data/source exclusions; no stock is forced through a failed check.")
    }
    val analysis = desk.obj("analysis_status")
    if (analysis.length() > 0) Section("Latest strategy checks") {
        Text("${analysis.optInt("tracked")} stocks checked · ${analysis.optInt("seeded")} history states ready · ${analysis.optInt("warming_up")} warming up")
        Text("Completed live candles drive new signals. Historical warm-up does not replay missed purchases.")
        DetailCard("Per-stock signal / waiting reasons", analysis)
    }
    val decisions = desk.rows("decisions")
    if (decisions.isEmpty()) Section("") { EmptyState("No strategy proposals yet", "The strategy waits for eligible signals, fresh prices, reviewed sessions and independent risk approval.") }
    decisions.forEach { decision ->
        Section("${decision.text("side")} · ${decision.text("symbol")}", friendly(decision.text("state"))) {
            DetailTree(JSONObject(decision.toString()).apply { remove("context"); remove("review") })
            if (decision.text("state") == "awaiting_approval") {
                val remaining = runCatching { Duration.between(parseInstant(desk.text("observed_at")), parseInstant(decision.text("expires_at"))).seconds - (elapsed - state.receivedAtElapsed) / 1000 }.getOrDefault(0)
                Text(if (remaining > 0) "$remaining seconds remaining · expires ${istTime(decision.text("expires_at"))}" else "Proposal expired. Refreshing does not replay the signal.")
                Action("Review proposal", model.canAct() && remaining > 0) { model.previewDecision(decision.text("id")) }
                Action("Reject proposal", model.canAct(), secondary = true) { model.rejectDecision(decision.text("id")) }
            }
        }
    }
    if (desk.optBoolean("decisions_truncated")) Hint("The server returned its latest bounded proposal window. Use Trade history for saved outcomes.")
}

@Composable private fun HistoryScreen(state: AppState, model: TraderViewModel) {
    val activity = model.data("activity"); var side by remember { mutableStateOf("all") }
    Section("Recorded paper activity", "An accepted order is not a fill. These records include outcomes and proposals that created no order.") {
        Choice("Side", side, listOf("all" to "All activity", "BUY" to "Buys", "SELL" to "Sells"), { side = it })
    }
    val entries = activity.rows("entries").filter { side == "all" || it.obj("order").text("side") == side || it.obj("decision").text("side") == side }
    if (entries.isEmpty()) Section("") { EmptyState("No recorded activity in this page", "Earlier records may remain available below. No financial outcome is inferred.") }
    entries.forEach { entry ->
        val order = entry.obj("order"); val decision = entry.obj("decision")
        Section(if (order.length() > 0) "${order.text("symbol")} · ${friendly(order.text("state"))}" else "${decision.text("symbol")} · proposal ${friendly(decision.text("state"))}") {
            DetailTree(entry)
            if (order.text("id", "").isNotBlank()) Action("Inspect all recorded fills", !state.busy, secondary = true) { model.inspectFills(order.text("id")) }
        }
    }
    activity.opt("next_before")?.takeIf { it != JSONObject.NULL }?.let { next -> Action("Earlier activity", !state.busy, secondary = true) { model.olderActivity(next.toString()) } }
    val fills = model.data("fills")
    if (fills.length() > 0) DetailCard("Recorded fills · latest selected order", fills, open = true)
    fills.opt("next_before")?.takeIf { it != JSONObject.NULL }?.let { next ->
        Action("Earlier fills for this order", !state.busy, secondary = true) { model.inspectFills(fills.text("order_id"), next.toString()) }
    }
}

@Composable private fun MoreScreen(state: AppState, model: TraderViewModel) {
    Section("Plan & research") {
        listOf(Page.DISCOVER, Page.WATCHLIST, Page.STRATEGY, Page.ANALYSIS, Page.POLICY, Page.BACKTEST).forEach { page -> Action(page.title, !state.busy, secondary = true) { model.navigate(page) } }
    }
    Section("Account & controls") {
        listOf(Page.PURCHASES, Page.HISTORY, Page.RISK, Page.BROKER, Page.SETTINGS, Page.SECURITY, Page.LEARN).forEach { page -> Action(page.title, !state.busy, secondary = true) { model.navigate(page) } }
    }
}
