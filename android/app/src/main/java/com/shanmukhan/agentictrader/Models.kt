package com.shanmukhan.agentictrader

import org.json.JSONArray
import org.json.JSONObject
import java.math.BigDecimal
import java.math.RoundingMode
import java.time.Instant
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter

fun JSONObject.obj(key: String) = optJSONObject(key) ?: JSONObject()
fun JSONObject.rows(key: String): List<JSONObject> = optJSONArray(key)?.let { a ->
    (0 until a.length()).mapNotNull { a.optJSONObject(it) }
} ?: emptyList()
fun JSONObject.strings(key: String): List<String> = optJSONArray(key)?.let { a ->
    (0 until a.length()).map { a.optString(it) }
} ?: emptyList()
fun JSONObject.text(key: String, empty: String = "Not available"): String =
    if (!has(key) || isNull(key)) empty else opt(key)?.toString() ?: empty
fun json(vararg pairs: Pair<String, Any?>) = JSONObject().apply {
    pairs.forEach { (key, value) -> put(key, value ?: JSONObject.NULL) }
}
fun decimalMoney(value: String): String = try {
    val amount = BigDecimal(value).setScale(2, RoundingMode.UNNECESSARY)
    val parts = amount.abs().toPlainString().split('.')
    val integer = parts[0]
    val grouped = if (integer.length <= 3) integer else {
        val head = integer.dropLast(3).reversed().chunked(2).joinToString(",").reversed()
        head + "," + integer.takeLast(3)
    }
    (if (amount.signum() < 0) "−" else "") + "₹" + grouped + "." + parts[1]
} catch (_: Exception) { "Not available" }
fun istTime(value: String): String = try {
    DateTimeFormatter.ofPattern("d MMM, h:mm a 'IST'").withZone(ZoneId.of("Asia/Kolkata")).format(parseInstant(value))
} catch (_: Exception) { value }
fun todayIst(value: String): String = try { parseInstant(value).atZone(ZoneId.of("Asia/Kolkata")).toLocalDate().toString() }
catch (_: Exception) { "" }
fun friendly(key: String) = key.replace('_', ' ').replaceFirstChar { it.uppercase() }
fun newIdentity() = java.util.UUID.randomUUID().toString().replace("-", "")
// Android 11's java.time parser requires offset timestamps through OffsetDateTime.
fun parseInstant(value: String): Instant = OffsetDateTime.parse(value).toInstant()

enum class Page(val title: String) {
    HOME("Overview"), DISCOVER("Discover stocks"), WATCHLIST("Watchlist"), ANALYSIS("Stock analysis"), STRATEGY("Your strategy"),
    PAPER("Paper trading"), PORTFOLIO("Portfolio"), PURCHASES("Purchases & SIP"), HISTORY("Trade history"),
    POLICY("Investment policies"), BACKTEST("Backtesting"), RISK("Risk & safeguards"),
    BROKER("Broker & data"), SETTINGS("Settings"), LEARN("Learning center"), SECURITY("Phone security"), MORE("Your workspace")
}

data class Review(
    val title: String, val explanation: String, val details: JSONObject,
    val confirmLabel: String, val submit: suspend () -> Unit,
)

data class AppState(
    val unlocked: Boolean = false, val paired: Boolean = false, val page: Page = Page.HOME,
    val data: Map<String, JSONObject> = emptyMap(), val busy: Boolean = false,
    val progress: String = "", val error: String? = null, val notice: String? = null,
    val review: Review? = null, val stale: Boolean = false, val reconcile: Boolean = false,
    val symbol: String = "", val timeframe: String = "1d", val report: JSONObject? = null,
    val compareReport: JSONObject? = null, val brokerUrl: String? = null,
    val dailyPreparing: Boolean = false, val expiresAt: String = "",
    val formDirty: Boolean = false, val pendingPage: Page? = null,
    val reconcilePage: Page = Page.HISTORY, val receivedAtElapsed: Long = 0,
    val alertsEnabled: Boolean = false,
    val environmentDialog: Boolean = false,
    val modeHelp: String? = null,
    val journeyAuditKey: String = "", val journeyChecking: Boolean = false,
    val journeyCheckError: String? = null, val journeyPolicy: String = "",
    val journeyRunning: Boolean = false,
)

object PolicyPayload {
    fun build(label: String, definitions: List<JSONObject>, values: Map<String, String>): JSONObject {
        val parameters = JSONObject()
        definitions.forEach { field ->
            val name = field.text("name", "")
            val raw = values[name]?.trim().orEmpty()
            if (raw.isEmpty()) parameters.put(name, JSONObject.NULL)
            else when (field.text("kind")) {
                "integer" -> { require(raw.matches(Regex("[0-9]+"))) { "${field.text("label")}: enter a whole number." }; parameters.put(name, raw.toInt()) }
                "decimal" -> { BigDecimal(raw); parameters.put(name, raw) }
                else -> parameters.put(name, raw)
            }
        }
        return json("label" to label.trim(), "parameters" to parameters)
    }
}

object PreparationReuse {
    fun verified(report: JSONObject, universe: String, currentJob: JSONObject): Boolean {
        val auditedJob = report.obj("preparation")
        val evidence = report.obj("source_validation")
        val identity = auditedJob.text("job_id", "")
        return universe in listOf("nifty50", "nifty100", "nifty500") &&
            identity.matches(Regex("[a-f0-9]{32}")) && identity == currentJob.text("job_id", "") &&
            auditedJob.text("state") in listOf("ready_for_review", "installed") &&
            currentJob.text("state") in listOf("ready_for_review", "installed") &&
            auditedJob.text("universe") == universe && currentJob.text("universe") == universe &&
            listOf("hashes_valid", "same_ist_date", "coverage_valid").all { evidence.opt(it) == true }
    }
}

fun universeName(value: String) = when (value) { "nifty50" -> "Nifty 50"; "nifty100" -> "Nifty 100"; "nifty500" -> "Nifty 500"; else -> "selected universe" }
