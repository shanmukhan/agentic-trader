package com.shanmukhan.agentictrader

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import org.json.JSONArray
import org.json.JSONObject

internal fun modeIsReady(desk: JSONObject): Boolean = desk.optJSONArray("blockers")?.length() == 0 && desk.obj("readiness").opt("can_start") == true

/** Guidance cannot grant authority; only a fresh desk response and explicit review can. */
internal fun tradeGuidance(desk: JSONObject): JSONObject {
    val readiness = desk.obj("readiness")
    val supplied = readiness.obj("mode_guidance")
    if (supplied.optInt("schema_version") == 1) return supplied
    val blockers = desk.strings("blockers")
    return json("title" to if (modeIsReady(desk)) "Ready to review a paper mode" else "Paper trading is not ready yet",
        "summary" to readiness.text("next_action", "Review the current readiness checks below."),
        "now_ist" to desk.text("observed_at", ""), "items" to JSONArray(
            readiness.rows("checks").filter { !it.optBoolean("ready") }.map { check ->
                json("title" to check.text("title"), "detail" to check.text("detail"))
            }.ifEmpty { blockers.map { json("title" to friendly(it.lowercase()), "detail" to "Recheck server readiness before choosing a mode.") } }))
}

internal fun guidanceTarget(value: String): Page? = when (value) {
    "broker" -> Page.BROKER; "strategy" -> Page.STRATEGY; "risk" -> Page.RISK; "watchlist" -> Page.WATCHLIST; else -> null
}
private fun guidanceLabel(page: Page): String = when (page) {
    Page.BROKER -> "Open Broker & data"; Page.STRATEGY -> "Prepare & review strategy"; Page.WATCHLIST -> "Open Watchlist & safety"; else -> "Open Risk & safeguards"
}

@Composable internal fun ModeGuidanceContent(state: AppState, model: TraderViewModel) {
    val desk = state.data["desk"] ?: JSONObject()
    val guidance = tradeGuidance(desk)
    Text(guidance.text("title"), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
    Text(guidance.text("summary"))
    val upcoming = guidance.text("next_entry_at", "")
    if (upcoming.isNotBlank()) Text("Next reviewed entry start: ${istTime(upcoming)}", fontWeight = FontWeight.SemiBold, color = Teal)
    val window = guidance.text("entry_window", "")
    if (window.isNotBlank()) Text("Entry window: $window", style = MaterialTheme.typography.bodyMedium)
    val completed = desk.obj("readiness").rows("checks").filter { it.optBoolean("ready") }.map { it.text("title") }
    if (completed.isNotEmpty()) Text("Completed: ${completed.joinToString(" · ")}", style = MaterialTheme.typography.bodySmall)
    guidance.rows("items").forEach { item ->
        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(item.text("title"), fontWeight = FontWeight.SemiBold)
            Text(item.text("detail"), style = MaterialTheme.typography.bodyMedium)
        }
    }
    if (state.stale) Hint("These checks may be out of date. Reconnect and refresh before choosing a mode.", error = true)
    if (state.reconcile) Hint("Inspect the previous instruction's saved outcome before choosing a mode.")
    guidance.rows("items").mapNotNull { guidanceTarget(it.text("target", "")) }.distinct().forEach { page ->
        Action(guidanceLabel(page), enabled = !state.busy, secondary = true) {
            model.dismissModeHelp(); model.navigate(page)
        }
    }
    Text("Checked ${istTime(guidance.text("now_ist", ""))} · updates automatically", style = MaterialTheme.typography.labelSmall)
    Text("Waiting does not activate a mode. Review and confirm when the checks clear.", style = MaterialTheme.typography.bodySmall)
}

@Composable internal fun ModeHelpDialog(state: AppState, model: TraderViewModel) {
    val mode = state.modeHelp ?: return
    val ready = state.data["desk"]?.let { modeIsReady(it) } == true && !state.stale && !state.reconcile
    AlertDialog(onDismissRequest = model::dismissModeHelp, containerColor = MaterialTheme.colorScheme.surface,
        title = { Text(if (ready) "${friendly(mode)} is ready to review" else "Before choosing ${friendly(mode)}") },
        text = { Column(Modifier.heightIn(max = 500.dp).verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(14.dp)) { ModeGuidanceContent(state, model) } },
        confirmButton = {
            if (ready) TextButton({ model.chooseMode(mode) }, enabled = !state.busy) { Text("Review ${friendly(mode)} mode") }
            else TextButton(model::dismissModeHelp) { Text("Got it") }
        }, dismissButton = { if (ready) TextButton(model::dismissModeHelp) { Text("Not now") } })
}
