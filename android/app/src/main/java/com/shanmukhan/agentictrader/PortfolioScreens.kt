package com.shanmukhan.agentictrader

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.snapshots.SnapshotStateMap
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import org.json.JSONArray
import org.json.JSONObject

fun stockOptions(desk: JSONObject): List<Pair<String, String>> {
    val selected = desk.optJSONArray("selected") ?: JSONArray()
    val values = (0 until selected.length()).map { index ->
        selected.optJSONObject(index)?.text("symbol", "") ?: selected.optString(index)
    }.filter { it.startsWith("NSE:") }
    return (values + desk.obj("account").rows("positions").map { it.text("symbol") }).distinct().map { it to it.removePrefix("NSE:") }
}

@Composable fun PortfolioScreen(state: AppState, model: TraderViewModel) {
    val portfolio = model.data("views").obj("portfolio")
    Section("Your holdings", "Values use saved accepted prices. Missing prices, fees and pending commitments stay visible.") {
        Metric("Portfolio value", decimalMoney(portfolio.text("equity")))
        Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
            Metric("Available cash", decimalMoney(portfolio.text("available_cash")), Modifier.weight(1f))
            Metric("Holding P&L", decimalMoney(portfolio.text("net_unrealized_pnl")), Modifier.weight(1f))
        }
        if (!portfolio.optBoolean("valuation_fresh")) Hint("Valuation is stale or incomplete. An estimate is not an executable selling price.")
        Action("Purchases & SIP plans", !state.busy, secondary = true) { model.navigate(Page.PURCHASES) }
    }
    val positions = portfolio.rows("positions")
    if (positions.isEmpty()) Section("") { EmptyState("No open virtual holdings", "An accepted order appears here only after actual simulated fills.") }
    positions.forEach { position -> Section(position.text("symbol"), "${position.text("quantity")} current shares") {
        Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
            Metric("Remaining basis", decimalMoney(position.text("cost")), Modifier.weight(1f))
            Metric("Estimated P&L", decimalMoney(position.text("unrealized_pnl")), Modifier.weight(1f))
        }
        DetailTree(position)
        Action("Inspect stock research", !state.busy, secondary = true) { model.selectSymbol(position.text("symbol")) }
    } }
    if (portfolio.optBoolean("positions_truncated")) Hint("Only the server's latest bounded holding window is shown. Inspect the account before relying on completeness.")
    DetailCard("Allocation, cash reserve & claims", portfolio.obj("allocation"), open = true)
    DetailCard("Accounting & valuation coverage", JSONObject(portfolio.toString()).apply { remove("positions"); remove("allocation") })
}

@Composable fun PurchasesScreen(state: AppState, model: TraderViewModel) {
    val portfolio = model.data("portfolio"); val desk = model.data("desk")
    if (portfolio.optBoolean("unavailable")) {
        Hint(portfolio.text("message")); return
    }
    val symbols = stockOptions(desk)
    var symbol by remember { mutableStateOf("") }; var budget by remember { mutableStateOf("") }
    var stop by remember { mutableStateOf("") }; var target by remember { mutableStateOf("") }
    var reference by remember { mutableStateOf("Android manual paper purchase") }
    var intent by remember { mutableStateOf("contrib-" + newIdentity()) }
    val recorded = portfolio.rows("orders").any { it.text("id") == intent }
    Section("Preview a manual paper purchase", "Use existing virtual cash. Quantity, fees and risk are calculated by the server; there is no client-side sizing.") {
        Metric("Available for new purchases", decimalMoney(portfolio.obj("account").text("available_cash")))
        if (symbols.isNotEmpty()) Choice("Stock", symbol, symbols, { symbol = it }) else Field("NSE stock symbol", symbol, { symbol = it.uppercase() }, "For example NSE:INFY. The catalog validates the symbol.")
        Field("Maximum cash debit · INR", budget, { budget = it }, "Includes buy fees. Enter exact rupees and paise, without commas.", numeric = true)
        Field("Stop price · INR", stop, { stop = it }, "For a new holding, specify its reviewed protections. Existing holding protections are retained.", numeric = true)
        Field("Target price · INR", target, { target = it }, numeric = true)
        Field("Instruction reference", reference, { reference = it })
        if (recorded) Hint("This instruction is already recorded. Inspect its order and fills below before starting another purchase.", success = true)
        Action("Calculate purchase preview", model.canAct() && !recorded && symbol.isNotBlank() && budget.isNotBlank() && reference.trim().length >= 3) {
            val request = json("intent_id" to intent, "symbol" to symbol.trim(), "budget" to budget.trim(), "reference" to reference.trim())
            if (stop.isNotBlank() || target.isNotBlank()) { request.put("stop", stop.trim()); request.put("target", target.trim()) }
            model.previewPurchase(request)
        }
        Action("Start a different purchase", !state.busy, secondary = true) {
            symbol = ""; budget = ""; stop = ""; target = ""; intent = "contrib-" + newIdentity()
        }
    }
    portfolio.rows("plans").forEach { item ->
        val plan = item.obj("plan")
        Section("SIP · ${plan.text("symbol")}", if (item.optBoolean("cancelled")) "Cancelled" else "Dates require individual preview and confirmation") {
            Text("Cash cap per occurrence: ${decimalMoney(plan.text("budget"))}", fontWeight = FontWeight.SemiBold)
            DetailTree(item)
            item.rows("occurrences").filter { it.text("status") == "DUE" }.forEach { occurrence ->
                Action("Preview due ${occurrence.text("session")}", model.canAct(), secondary = true) { model.previewPurchase(occurrence.obj("request")) }
            }
            if (!item.optBoolean("cancelled")) Action("Cancel plan & pending buys", model.canAct(), secondary = true) {
                model.reviewPost("Cancel this SIP plan?", "Future occurrences and pending plan buys will be cancelled. Filled shares remain held with their existing protections.",
                    "/api/paper/portfolio/plans/cancel", json("plan_id" to plan.text("plan_id"), "reference" to "Android confirmed plan cancellation"), plan)
            }
        }
    }
    NewSip(state, model, symbols)
    DetailCard("Contribution orders & actual debits", json("orders" to portfolio.optJSONArray("orders"), "truncated" to portfolio.opt("orders_truncated")), open = true)
    DetailCard("Acquisition lots & fees", json("lots" to portfolio.optJSONArray("lots"), "truncated" to portfolio.opt("lots_truncated")))
}

@Composable private fun NewSip(state: AppState, model: TraderViewModel, symbols: List<Pair<String, String>>) {
    var open by remember { mutableStateOf(false) }
    var symbol by remember { mutableStateOf("") }; var budget by remember { mutableStateOf("") }
    var stop by remember { mutableStateOf("") }; var target by remember { mutableStateOf("") }
    var dates by remember { mutableStateOf("") }; var reference by remember { mutableStateOf("Android reviewed SIP plan") }
    var planId by remember { mutableStateOf("plan-" + newIdentity()) }
    val sessions = model.data("setup").rows("sessions")
    Section("") {
        TextButton({ open = !open }) { Text("Create a SIP plan") }
        if (open) {
            Text("Choose exact reviewed exchange dates. Each due date still needs a fresh purchase preview; missed dates stay missed.")
            Choice("Stock", symbol, symbols, { symbol = it })
            Field("Cash cap per date · INR", budget, { budget = it }, numeric = true)
            Field("Stop distance · %", stop, { stop = it }, numeric = true)
            Field("Target distance · %", target, { target = it }, numeric = true)
            if (sessions.isNotEmpty()) Choice("Add a reviewed session", "", sessions.map { it.text("date") to it.text("date") }, { date ->
                dates = (dates.split(',').map { it.trim() }.filter { it.isNotBlank() } + date).distinct().sorted().joinToString(", ")
            }, placeholder = "Add a date")
            Field("Reviewed dates · YYYY-MM-DD", dates, { dates = it }, "Comma-separated dates. Up to 120 explicitly reviewed sessions.", multiline = true)
            Field("Plan reference", reference, { reference = it })
            Action("Review SIP plan", model.canAct() && listOf(symbol, budget, stop, target, dates).all { it.isNotBlank() }) {
                val body = json("plan_id" to planId, "symbol" to symbol, "budget" to budget.trim(), "stop_pct" to stop.trim(), "target_pct" to target.trim(),
                    "sessions" to JSONArray(dates.split(',').map { it.trim() }.filter { it.isNotBlank() }), "reference" to reference.trim())
                model.reviewPost("Save this reviewed SIP plan?", "This creates a plan with the displayed cash caps and dates. It does not submit an order now or automatically buy on due dates.", "/api/paper/portfolio/plans", body)
            }
            Action("Start another plan", !state.busy, secondary = true) { symbol = ""; budget = ""; stop = ""; target = ""; dates = ""; planId = "plan-" + newIdentity() }
        }
    }
}

@Composable fun PolicyScreen(state: AppState, model: TraderViewModel) {
    val data = model.data("policies"); val definitions = data.rows("field_definitions")
    val groups = definitions.map { it.text("group") }.distinct()
    val values = remember { mutableStateMapOf<String, String>() }
    var label by remember { mutableStateOf("") }; var step by remember { mutableIntStateOf(0) }
    var discard by remember { mutableStateOf(false) }
    Section("Design a months-to-years policy", "A draft is a research specification. It cannot replace the installed strategy or activate trading.") {
        Hint(if (state.formDirty) "Unsaved choices. Review and save, or discard this copy before leaving." else "Blank choices remain unresolved. No financial policy is preselected.")
        Field("Draft name", label, { label = it; model.dirty(true) }, "Give this immutable snapshot a name you recognize.")
        if (groups.isNotEmpty()) Choice("Policy section", groups.getOrElse(step) { groups.first() }, groups.map { it to it }, { step = groups.indexOf(it).coerceAtLeast(0) })
        definitions.filter { it.text("group") == groups.getOrNull(step) }.forEach { field ->
            val name = field.text("name"); val current = values[name].orEmpty()
            if (field.text("kind") == "choice") Choice(field.text("label"), current,
                field.rows("choices").map { it.text("value") to it.text("label") }, { values[name] = it; model.dirty(true) }, "Unresolved — choose explicitly")
            else Field(field.text("label"), current, { values[name] = it; model.dirty(true) },
                "${field.text("unit", "count")}: ${field.text("minimum")} to ${field.text("maximum")}. Exact values; no rounding or thousands separators.", numeric = true)
        }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            OutlinedButton({ step-- }, enabled = step > 0, modifier = Modifier.weight(1f)) { Text("Previous") }
            OutlinedButton({ step++ }, enabled = step < groups.size - 1, modifier = Modifier.weight(1f)) { Text("Next section") }
        }
        Action("Review draft snapshot", model.canAct() && definitions.isNotEmpty() && label.trim().length >= 3) {
            runCatching { PolicyPayload.build(label, definitions, values) }.onSuccess(model::previewPolicy)
                .onFailure { model.reportError(it.message ?: "Review the exact policy inputs.") }
        }
        Action("Discard & start blank", !state.busy, secondary = true) { if (state.formDirty) discard = true else { values.clear(); label = ""; step = 0 } }
    }
    val inspected = model.data("draft").obj("draft")
    if (inspected.length() > 0) Section("Inspect · ${inspected.text("label")}") {
        DetailTree(inspected)
        Action("Edit a new copy", !state.busy && !state.formDirty, secondary = true) {
            val parameters = inspected.obj("parameters")
            values.clear(); definitions.forEach { field -> val name = field.text("name"); values[name] = parameters.text(name, "") }
            label = inspected.text("label", "Policy").take(94) + " copy"; step = 0; model.dirty(true)
        }
    }
    data.rows("drafts").forEach { draft -> Section(draft.text("label"), friendly(draft.text("state", "saved draft"))) {
        Text(draft.text("draft_id"), style = MaterialTheme.typography.labelSmall)
        Action("Inspect saved snapshot", !state.busy && !state.formDirty, secondary = true) { model.loadDraft(draft.text("draft_id")) }
    } }
    DetailCard("Policy limits & unresolved features", json("limitations" to data.optJSONArray("limitations")))
    if (discard) AlertDialog(onDismissRequest = { discard = false }, title = { Text("Discard unsaved choices?") }, text = { Text("This clears only this unsaved form. Saved draft snapshots remain available.") },
        confirmButton = { TextButton({ discard = false; values.clear(); label = ""; step = 0; model.dirty(false) }) { Text("Discard") } },
        dismissButton = { TextButton({ discard = false }) { Text("Keep editing") } })
}

@Composable fun BacktestScreen(state: AppState, model: TraderViewModel, external: (String) -> Unit) {
    val resources = model.data("resources"); val jobs = model.data("jobs")
    model.pendingBacktest()?.let {
        Hint("An earlier research submission has an uncertain outcome. Inspect saved jobs before retrying; the original request identity is retained.")
        Action("Review retry using original request", model.canAct()) { model.retryBacktest() }
    }
    if (!resources.obj("capability").optBoolean("available")) Hint("Job launch unavailable: " + resources.obj("capability").text("reason", "Required operating-system isolation has not been verified."))
    Section("Registered research inputs", "Backtests run separately from your connected paper account. No input prices, strategy policy or return series are invented.") {
        if (resources.rows("resources").isEmpty()) Text("No input bundles are registered. The server's local registration workflow must validate an explicit bundle first.")
        resources.rows("resources").forEach { resource ->
            Text(resource.text("label"), fontWeight = FontWeight.SemiBold)
            Text(if (resource.isNull("synthetic")) "Source origin not certified" else if (resource.optBoolean("synthetic")) "Synthetic inputs · demonstration only" else "Declared non-synthetic · not certified market acceptance")
            DetailTree(resource, external = external)
            Action("Review isolated run", model.canAct() && model.pendingBacktest() == null && resources.obj("capability").optBoolean("available")) { model.runBacktest(resource) }
            HorizontalDivider(color = Line)
        }
    }
    jobs.rows("jobs").forEach { job -> Section("${friendly(job.text("state"))} · historical simulation", "Stage: ${friendly(job.text("stage"))}") {
        DetailTree(job)
        if (job.text("state") in listOf("queued", "running", "cancelling")) Action("Review cancellation", model.canAct(), secondary = true) {
            model.reviewPost("Cancel this isolated research job?", "Cancellation can wait for a bounded worker step. It does not cancel a financial order, sell holdings or change account authority.",
                "/api/backtests/jobs/${job.text("job_id")}/cancel", json("acknowledged" to true), job)
        }
        if (job.text("state") == "succeeded" && job.text("report_id", "").isNotBlank()) {
            Action("Inspect recorded report", !state.busy, secondary = true) { model.loadReport(job.text("report_id")) }
            Action("Use as comparison report", !state.busy, secondary = true) { model.loadReport(job.text("report_id"), true) }
        }
    } }
    state.report?.let { DetailCard("Recorded report · primary", it, open = true, external = external) }
    state.compareReport?.let {
        Hint("Compare identical semantics, costs, code and coverage before interpreting differences. These are saved simulations, not a profit forecast.")
        DetailCard("Recorded report · comparison", it, open = true, external = external)
    }
    DetailCard("Runner limits & material limitations", JSONObject(resources.toString()).apply { remove("resources") }, external = external)
}
