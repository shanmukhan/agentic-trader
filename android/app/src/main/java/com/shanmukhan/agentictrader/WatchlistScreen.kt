package com.shanmukhan.agentictrader

import androidx.compose.material3.Text
import androidx.compose.runtime.*
import org.json.JSONObject

@Composable internal fun WatchlistScreen(state: AppState, model: TraderViewModel) {
    val value = state.data["watchlist"] ?: JSONObject()
    val safety = value.obj("safety")
    if (!safety.has("revision")) {
        Hint("Watchlist is unavailable. Refresh to check backend compatibility; no permissions can be changed here.")
        return
    }
    val saved = safety.strings("symbols").sorted()
    var draft by remember { mutableStateOf(saved) }
    var search by remember { mutableStateOf("") }
    LaunchedEffect(safety.optInt("revision"), state.formDirty) {
        if (!state.formDirty) draft = saved
    }
    fun change(symbols: List<String>) {
        draft = symbols.distinct().sorted()
        model.dirty(draft != saved)
    }
    Section("Account safety", "Cash only · no margin borrowing or short selling") {
        Text("${safety.optInt("entries_today")} / 5 entry slots used today. Accepted entries use a slot even if cancelled; partial fills and retries of the same order do not add slots. Exits remain available.")
        Text("Maximum order cost including buy fees: ${decimalMoney(safety.text("max_order_cost"))} (25% of current equity). Stricter risk limits still apply.")
        Text("Observed equity reference: ${decimalMoney(safety.text("peak_equity"))} · Drawdown: ${safety.text("drawdown_pct")}%")
        if (!safety.optBoolean("valuation_fresh")) Hint("Valuation is stale or incomplete. These amounts cannot authorize a trade.", error = true)
        if (safety.optBoolean("data_blocked_today")) Hint("Price integrity incident: no new purchases for the rest of this IST day, including after restart. ${safety.text("data_reason")}", error = true)
        if (safety.optBoolean("paused")) {
            Hint("25% drawdown pause is latched. Recovery or restart cannot resume entries.", error = true)
            Action("Review drawdown pause reset", model.canAct() && !state.formDirty && value.text("mode") == "manual", secondary = true) { model.reviewSafetyResume() }
        }
        Text("Unreadable or inconsistent ledger records block execution. External deposits and withdrawals are unsupported. Contributions and SIPs invest existing cash.")
    }
    Section("Permitted NSE stocks", "Only the saved list may be bought. Holdings outside it remain exit only.") {
        Text("Checked ${istTime(value.text("observed_at"))}")
        if (state.formDirty) Hint("Unsaved watchlist edits. Review and save, or discard before leaving.")
        if (draft.isEmpty()) Hint("Empty watchlist: every new purchase is blocked.")
        draft.forEach { symbol ->
            Text(symbol)
            value.rows("selected").find { it.text("symbol") == symbol }?.let { row ->
                if (!row.optBoolean("feed_selected")) Text("Not selected for market data. Add its feed subscription before trading.")
                if (row.optBoolean("held")) Text("Currently held; removing it still permits protective exits.")
            }
            Action("Remove $symbol", !state.busy, secondary = true) { change(draft - symbol) }
        }
        if (value.strings("held_outside_watchlist").isNotEmpty()) Text("Exit only: ${value.strings("held_outside_watchlist").joinToString()}. Keep their feed subscriptions.")
        Action("Review watchlist change", model.canAct() && state.formDirty) { model.reviewWatchlist(draft) }
        Action("Discard watchlist edits", state.formDirty && !state.busy, secondary = true) { draft = saved; model.dirty(false) }
    }
    Section("Pick from NSE", "${value.optInt("catalog_count")} supported catalog instruments. Saved catalog imported: ${value.text("catalog_imported_at", "time unavailable")}. Refresh the catalog in Broker & data when needed.") {
        Field("NSE symbol", search, { search = it.take(34) }, "For example RELIANCE. Search returns at most 100 matches.")
        Action("Search NSE catalog", !state.busy) { model.searchWatchlist(search) }
        val results = state.data["watchlistCatalog"]
        results?.let { Text("${it.optInt("matches")} matches · ${it.rows("items").size} shown. Narrow the search if needed.") }
        results?.rows("items")?.forEach { row ->
            val symbol = row.text("symbol")
            Action(if (symbol in draft) "Remove $symbol" else "Add $symbol", !state.busy, secondary = true) {
                change(if (symbol in draft) draft - symbol else draft + symbol)
            }
        }
        Text("Watchlist permission alone cannot start trading. Feed selection, fresh quotes, reviewed strategy and every financial safeguard are still required.")
        Action("Open Broker & data", !state.busy, secondary = true) { model.navigate(Page.BROKER) }
        Action("Open Stock Discovery", !state.busy, secondary = true) { model.navigate(Page.DISCOVER) }
    }
}
