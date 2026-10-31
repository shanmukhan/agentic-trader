package com.shanmukhan.agentictrader

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import org.json.JSONArray
import org.json.JSONObject
import java.math.BigDecimal
import java.math.MathContext
import kotlin.math.roundToInt

private val indicatorLabels = linkedMapOf(
    "sma20" to "SMA 20", "sma50" to "SMA 50", "sma200" to "SMA 200",
    "ema12" to "EMA 12", "ema26" to "EMA 26", "rsi14" to "RSI 14",
    "macd" to "MACD", "macd_signal" to "MACD signal", "macd_histogram" to "MACD histogram",
    "atr14" to "ATR 14", "support20" to "Prior 20-bar support", "resistance20" to "Prior 20-bar resistance",
    "drawdown_pct" to "Price drawdown %", "max_drawdown_pct" to "Maximum segment drawdown %",
    "volatility20_pct" to "20-return volatility %",
)
private val overlayKeys = listOf("sma20", "sma50", "sma200", "ema12", "ema26", "support20", "resistance20")
private val overlayColors = listOf(Color(0xFF3669BE), Color(0xFFAD6A1C), Color(0xFF8D5AB6),
    Color(0xFF147C7C), Color(0xFFB8567D), Color(0xFF6D7830), Color(0xFF4E6591))
private fun number(row: JSONObject, key: String): BigDecimal? = try { if (row.isNull(key)) null else BigDecimal(row.get(key).toString()) } catch (_: Exception) { null }
private fun coordinate(value: BigDecimal, minimum: BigDecimal, span: BigDecimal): Float =
    value.subtract(minimum).divide(span, MathContext.DECIMAL64).toFloat().coerceIn(0f, 1f)

@Composable fun AnalysisScreen(state: AppState, model: TraderViewModel, external: (String) -> Unit) {
    val analysis = model.data("analysis")
    var range by remember { mutableStateOf("60") }
    var overlays by remember { mutableStateOf(setOf("sma20", "sma50")) }
    var indicator by remember { mutableStateOf("rsi14") }
    val all = analysis.rows("bars")
    val bars = if (range == "all") all else all.takeLast(range.toInt())
    var selected by remember(analysis.text("symbol"), state.timeframe, range, bars.size) { mutableIntStateOf((bars.size - 1).coerceAtLeast(0)) }
    Section("Saved price research", "Historical candles and live quotes have separate freshness and review requirements.") {
        Choice("Stock", analysis.text("symbol", state.symbol), analysis.rows("symbols").map { it.text("symbol") to it.text("symbol").removePrefix("NSE:") }, { model.selectSymbol(it) }, enabled = !state.busy)
        Choice("Interval", state.timeframe, listOf("1m" to "1 minute", "5m" to "5 minutes", "1d" to "Daily", "1w" to "Weekly", "1mo" to "Monthly"),
            { model.selectSymbol(analysis.text("symbol", state.symbol), it) }, enabled = !state.busy)
        Choice("Display range", range, listOf("20" to "Latest 20 bars", "60" to "Latest 60 bars", "120" to "Latest 120 bars", "all" to "All returned bars"), { range = it })
        Text(analysis.text("message", "No saved research is available."), style = MaterialTheme.typography.bodyMedium)
        if (analysis.obj("source").opt("synthetic") == true) Hint("Synthetic source declaration · simulated evidence only.")
        if (analysis.optBoolean("truncated")) Hint("The server returned only its latest ${analysis.optInt("bar_limit")} bars. Indicator computation used eligible source history before display slicing.")
    }
    if (bars.isEmpty()) Section("") { EmptyState("No complete candles for this selection", "Inspect coverage and warmup below. No prices or indicators are filled in.") }
    else {
        Section(analysis.text("symbol") + " · price history", analysis.obj("source").text("price_basis", "Inspect the declared price basis below.")) {
            CandleChart(bars, overlays, selected, { selected = it })
            if (bars.size > 1) Slider(value = selected.toFloat(), onValueChange = { selected = it.roundToInt() },
                valueRange = 0f..bars.lastIndex.toFloat(), steps = (bars.size - 2).coerceAtLeast(0),
                modifier = Modifier.semantics { contentDescription = "Inspect candle ${selected + 1} of ${bars.size}. Exact values are below." })
            val bar = bars[selected.coerceIn(bars.indices)]
            Text(istTime(bar.text("time", bar.text("session", ""))), fontWeight = FontWeight.SemiBold)
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Column(Modifier.weight(1f)) { Text("Open ${bar.text("open")}"); Text("Low ${bar.text("low")}") }
                Column(Modifier.weight(1f)) { Text("Close ${bar.text("close")}"); Text("High ${bar.text("high")}") }
            }
            Text("Volume ${bar.text("volume")} shares", style = MaterialTheme.typography.bodyMedium)
            var showOverlays by remember { mutableStateOf(false) }
            TextButton({ showOverlays = !showOverlays }) { Text("Price overlays · ${overlays.size} selected") }
            if (showOverlays) overlayKeys.forEach { key -> Acknowledge(indicatorLabels.getValue(key), key in overlays, {
                overlays = if (it) overlays + key else overlays - key
            }) }
            Text("Up and down candles are also represented by their exact OHLC values. Gaps break indicator lines.", style = MaterialTheme.typography.bodySmall)
        }
        Section("Volume", "Reported share units on the declared price/share basis.") { ValuePlot(bars, "volume", Teal, columns = true) }
        Section("Indicator inspection", "Values are supplied by the server's full-history computation. Changing the display range never reseeds them.") {
            Choice("Indicator", indicator, indicatorLabels.map { it.key to it.value }, { indicator = it })
            ValuePlot(bars, indicator, Teal)
            val current = bars[selected.coerceIn(bars.indices)]
            Text("Selected value: ${current.text(indicator, "Unavailable · inspect warmup and coverage")}", fontWeight = FontWeight.SemiBold)
            Text("Drawdowns and volatility describe adjusted prices, not account returns or annualized performance.", style = MaterialTheme.typography.bodySmall)
        }
        DetailCard("Exact selected candle & all indicators", bars[selected.coerceIn(bars.indices)], open = true, external = external)
        DetailCard("Accessible candle history", json("candles" to JSONArray(bars)), external = external)
    }
    DetailCard("Current quote · independent freshness", analysis.obj("quote"), open = true, external = external)
    val research = analysis.obj("research")
    DetailCard("Warmup, formulas, gaps & coverage", research, external = external)
    DetailCard("Benchmark comparison & source", research.obj("benchmark"), open = true, external = external)
    DetailCard("Fundamental-data availability", research.obj("fundamentals"), open = true, external = external)
    DetailCard("Screen, source identity & limitations", JSONObject(analysis.toString()).apply { remove("bars"); remove("research"); remove("symbols"); remove("quote") }, external = external)
}

@Composable private fun CandleChart(bars: List<JSONObject>, overlays: Set<String>, selected: Int, pick: (Int) -> Unit) {
    val prices = bars.flatMap { row -> listOfNotNull(number(row, "high"), number(row, "low")) + overlays.mapNotNull { number(row, it) } }
    if (prices.isEmpty()) { Hint("No valid price points are available for drawing."); return }
    val low = prices.minOrNull()!!; val high = prices.maxOrNull()!!
    val span = high.subtract(low).takeIf { it.signum() > 0 } ?: BigDecimal.ONE
    Text("₹${high.toPlainString()} high · ₹${low.toPlainString()} low", style = MaterialTheme.typography.labelSmall)
    Canvas(Modifier.fillMaxWidth().height(230.dp).semantics { contentDescription = "Historical candlestick chart. Use the candle slider and exact-value section to inspect without relying on color." }
        .pointerInput(bars.size) { detectTapGestures { point -> pick((point.x / size.width * bars.size).toInt().coerceIn(bars.indices)) } }) {
        val width = size.width / bars.size
        fun y(v: BigDecimal) = size.height * (1f - coordinate(v, low, span))
        repeat(5) { n -> val y = size.height * n / 4; drawLine(Line, Offset(0f, y), Offset(size.width, y), 1f) }
        bars.forEachIndexed { index, row ->
            val o = number(row, "open"); val c = number(row, "close"); val h = number(row, "high"); val l = number(row, "low")
            if (o != null && c != null && h != null && l != null) {
                val color = if (c >= o) Teal else Color(0xFFBD524B)
                val x = (index + .5f) * width
                drawLine(color, Offset(x, y(h)), Offset(x, y(l)), 1.5f)
                drawRect(color, Offset(x - width * .3f, minOf(y(o), y(c))), Size((width * .6f).coerceAtLeast(1f), kotlin.math.abs(y(o) - y(c)).coerceAtLeast(2f)))
            }
        }
        overlayKeys.forEachIndexed { index, key -> if (key in overlays) {
            val path = Path(); var drawing = false
            bars.forEachIndexed { i, row ->
                val value = number(row, key)
                if (value == null) drawing = false else {
                    val x = (i + .5f) * width
                    if (!drawing || row.optBoolean("segment_break")) path.moveTo(x, y(value)) else path.lineTo(x, y(value))
                    drawing = true
                }
            }
            drawPath(path, overlayColors[index], style = androidx.compose.ui.graphics.drawscope.Stroke(2f))
        } }
        val x = (selected + .5f) * width
        drawLine(Ink.copy(alpha = .5f), Offset(x, 0f), Offset(x, size.height), 1f)
    }
    if (overlays.isNotEmpty()) Text(overlays.joinToString(" · ") { indicatorLabels[it] ?: it }, style = MaterialTheme.typography.labelSmall)
}

@Composable private fun ValuePlot(bars: List<JSONObject>, key: String, color: Color, columns: Boolean = false) {
    val points = bars.mapNotNull { number(it, key) }
    if (points.isEmpty()) { Hint("${indicatorLabels[key] ?: friendly(key)} is unavailable for this selection. Warmup or complete history may be missing; unavailable is not zero."); return }
    val minimum = if (columns) BigDecimal.ZERO else points.minOrNull()!!
    val maximum = points.maxOrNull()!!
    val span = maximum.subtract(minimum).takeIf { it.signum() > 0 } ?: BigDecimal.ONE
    Text("${minimum.toPlainString()} to ${maximum.toPlainString()}", style = MaterialTheme.typography.labelSmall)
    Canvas(Modifier.fillMaxWidth().height(130.dp).semantics { contentDescription = "${indicatorLabels[key] ?: friendly(key)} plot. Exact values and missing intervals are available in candle history." }) {
        val width = size.width / bars.size.coerceAtLeast(1)
        val path = Path(); var drawing = false
        bars.forEachIndexed { i, row ->
            val value = number(row, key)
            if (value == null) drawing = false else {
                val x = (i + .5f) * width; val y = size.height * (1 - coordinate(value, minimum, span))
                if (columns) drawRect(color.copy(alpha = .65f), Offset(x - width * .3f, y), Size((width * .6f).coerceAtLeast(1f), size.height - y))
                else { if (!drawing || row.optBoolean("segment_break")) path.moveTo(x, y) else path.lineTo(x, y); drawing = true }
            }
        }
        if (!columns) drawPath(path, color, style = androidx.compose.ui.graphics.drawscope.Stroke(2.5f))
    }
}
