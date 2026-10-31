package com.shanmukhan.agentictrader

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import org.json.JSONArray
import org.json.JSONObject

@Composable fun BrokerScreen(state: AppState, model: TraderViewModel, external: (String) -> Unit) {
    val setup = model.data("setup"); val diagnostics = setup.obj("feed_diagnostics")
    val requested = setup.optBoolean("stream_requested"); val connected = setup.optBoolean("feed_connected")
    val failed = diagnostics.text("state") == "failed"
    Section("Market-data connection") {
        Hint(when {
            connected -> "Connected to Zerodha market data. Check fresh usable prices and trading readiness separately."
            failed -> "Connection failed after its retry limit. Resolve the cause, then explicitly disconnect and reconnect."
            requested -> "Connecting or retrying · status updates automatically. ${diagnostics.optInt("failures")} failures recorded."
            else -> "Disconnected. Your holdings remain open; fills and protective exits need fresh reviewed quotes."
        }, error = failed, success = connected)
        if (diagnostics.length() > 0) DetailTree(diagnostics)
        Action("Connect paper market data", model.canAct() && !requested && setup.optBoolean("access_token_available") && setup.rows("selected").isNotEmpty()) {
            model.reviewPost("Connect market data?", "Fresh quotes can resume pending paper fills and protective exits for the displayed subscriptions. This does not submit a new intent or activate a trading mode.",
                "/api/setup/connect", JSONObject(), json("selected" to setup.optJSONArray("selected"), "connection_effect" to "Pending fills and exits can resume"))
        }
        Action("Disconnect market data", model.canAct() && requested, secondary = true) {
            model.reviewPost("Disconnect market data?", "Holdings remain open. Fills and protective exits must wait for fresh quotes after reconnection.", "/api/setup/disconnect", JSONObject())
        }
    }
    Section("Kite session", if (setup.optBoolean("profile_verified_this_run")) "Verified in this server run" else "Verification needed") {
        Text("A saved token can expire. Profile success alone does not prove history or streaming entitlement.")
        Action("Check saved broker session", model.canAct()) { model.direct("/api/setup/profile", label = "Verifying Kite session") }
        Action("Sign in to Zerodha", model.canAct() && !requested, secondary = true) { model.brokerLogin() }
        Text("Login and 2FA happen in your system browser. The server receives and exchanges the one-time callback. Return here and unlock to continue; no API secret is placed in the browser.", style = MaterialTheme.typography.bodyMedium)
        ManualBrokerToken(state, model)
    }
    BrokerCredentials(state, model, requested, external)
    Section("Automatic Nifty 50 basket") {
        val monitoring = model.data("desk").obj("monitoring")
        Text(if (setup.text("automatic_universe", "custom") == "nifty50")
            "Following the official Nifty 50 basket · ${setup.rows("selected").size} subscribed stocks."
            else "Use the official Nifty 50 basket automatically. You do not need to choose ten stocks.")
        Text("Every constituent is monitored. History, source reviews, strategy signals and risk checks determine which stocks can receive a paper order.")
        if (monitoring.length() > 0) Text("${monitoring.optInt("execution_covered_count")} stocks have reviewed history coverage; exclusions remain visible in strategy sources.")
        Action("Use / refresh official Nifty 50", model.canAct() && !requested && model.data("desk").text("mode") == "manual") {
            model.reviewPost("Use the official Nifty 50 basket?", "The server fetches current constituents automatically and subscribes to the entire supported basket. Held stocks are retained. This changes the monitoring universe and feed capacity, not cash limits, position limits or the trading mode.",
                "/api/desk/universe/nifty50", json("revision" to model.data("desk").text("revision"), "acknowledged" to true),
                json("universe" to "Official Nifty 50", "selection" to "All current constituents; no ten-stock cap"))
        }
        if (requested || model.data("desk").text("mode") != "manual") Text("Basket changes require Manual and a disconnected feed. Held stocks remain protected by the existing workflow.", style = MaterialTheme.typography.bodySmall)
    }
    var customOpen by remember { mutableStateOf(false) }
    TextButton({ customOpen = !customOpen }) { Text("Advanced: custom feed subscriptions") }
    if (customOpen) {
        val selected = setup.rows("selected").map { it.text("symbol") }
        var selection by remember { mutableStateOf(selected.joinToString(", ")) }
        Section("Stock subscriptions", "${setup.optInt("catalog_count")} catalog instruments · account limit ${setup.optInt("stream_limit", 50)} subscriptions") {
            Action("Import / validate NSE catalog", model.canAct() && !requested, secondary = true) { model.direct("/api/setup/catalog", label = "Importing NSE catalog") }
            Field("NSE symbols, comma separated", selection, { selection = it }, "The catalog validates tokens, tick sizes and held-stock coverage. Disconnect before replacement.", multiline = true)
            Action("Review subscription changes", model.canAct() && !requested && selection.isNotBlank()) {
                val symbols = selection.split(',').map { it.trim().uppercase() }.filter { it.isNotBlank() }
                model.reviewPost("Save these feed subscriptions?", "All held stocks must remain represented. This switches to a custom feed and stops following the automatic Nifty 50 basket. Saved research and cash are retained.",
                    "/api/setup/symbols", json("symbols" to JSONArray(symbols)))
            }
            DetailTree(json("saved_subscriptions" to setup.optJSONArray("selected")))
        }
    }
    CalendarReview(state, model)
}

@Composable private fun ManualBrokerToken(state: AppState, model: TraderViewModel) {
    var open by remember { mutableStateOf(false) }; var requestToken by remember { mutableStateOf("") }
    TextButton({ open = !open }) { Text("Fallback: exchange a one-time request token") }
    if (open) {
        Field("One-time request token", requestToken, { requestToken = it }, "Use only when the automatic callback did not finish. Start the login from this app first.", secret = true)
        Action("Exchange and verify session", model.canAct() && requestToken.isNotBlank(), secondary = true) {
            val supplied = requestToken; requestToken = ""; model.manualExchange(supplied)
        }
    }
}

@Composable private fun BrokerCredentials(state: AppState, model: TraderViewModel, requested: Boolean, external: (String) -> Unit) {
    var open by remember { mutableStateOf(false) }; var key by remember { mutableStateOf("") }; var secret by remember { mutableStateOf("") }
    Section("") {
        TextButton({ open = !open }) { Text("App registration & credentials") }
        if (open) {
            Text("Edit the existing app in Kite's developer console. For this hosted deployment register exactly:")
            Text("https://shanmukhan.com/agentic-trader/", fontWeight = FontWeight.SemiBold)
            Action("Open Kite developer console", secondary = true) { external("https://developers.kite.trade/apps") }
            Text("Existing saved credentials are used automatically. Replace them only when necessary; replacement clears the old broker token.")
            Field("Kite API key", key, { key = it }, secret = true)
            Field("Kite API secret", secret, { secret = it }, secret = true)
            Action("Review credential replacement", model.canAct() && !requested && key.isNotBlank() && secret.isNotBlank()) {
                val body = json("api_key" to key.trim(), "api_secret" to secret.trim()); key = ""; secret = ""
                model.reviewPost("Replace saved Kite credentials?", "The new values are sent only to your HTTPS server. Replacement clears the old broker session. Values are not shown in this review or returned by status.",
                    "/api/setup/credentials", body, json("effect" to "Replace app credentials and clear saved broker access token"))
            }
        }
    }
}

@Composable private fun CalendarReview(state: AppState, model: TraderViewModel) {
    val setup = model.data("setup")
    var date by remember { mutableStateOf(setup.text("today", "")) }
    var open by remember { mutableStateOf("09:15") }; var close by remember { mutableStateOf("15:30") }
    var reference by remember { mutableStateOf("https://www.nseindia.com/resources/exchange-communication-holidays") }
    var reviewed by remember { mutableStateOf(false) }
    Section("Exchange session review", "Normal hours are suggestions. They do not approve a holiday, special session or price basis.") {
        Field("Session date · YYYY-MM-DD", date, { date = it })
        Field("Open · HH:MM IST", open, { open = it })
        Field("Close · HH:MM IST", close, { close = it })
        Field("Exchange notice / reference", reference, { reference = it })
        Acknowledge("I checked this date and these exact hours against exchange notices.", reviewed, { reviewed = it })
        Action("Review session save", model.canAct() && reviewed && reference.trim().length >= 3) {
            model.reviewPost("Save this reviewed session?", "Existing used session definitions cannot be overwritten. This date approval does not approve a holding's price basis or submit an order.",
                "/api/setup/session", json("date" to date.trim(), "open" to open.trim(), "close" to close.trim(), "source" to reference.trim(), "reviewed" to true))
            reviewed = false
        }
        DetailTree(json("saved_current_and_future_sessions" to setup.optJSONArray("sessions")))
    }
}

@Composable fun RiskScreen(state: AppState, model: TraderViewModel, external: (String) -> Unit) {
    val desk = model.data("desk"); val account = desk.obj("account")
    Section("Account safeguards", "Current kill state: ${if (account.optBoolean("kill")) "active" else "not active"}. Pending fills and exits still depend on usable quotes.") {
        Action("Stop new entries & cancel pending buys", model.canAct(), destructive = true) {
            model.reviewPost("Activate the kill switch?", "This pauses strategy authority and cancels pending buys. Existing holdings remain open with their protection workflow; it does not sell them.", "/api/control/kill", JSONObject())
        }
        Action("Queue exits and stop", model.canAct(), secondary = true) {
            model.reviewPost("Queue exits for all holdings?", "This stops new entries and queues virtual exits. It does not immediately close holdings; fills require fresh, reviewed quotes and liquidity.", "/api/control/flatten", JSONObject())
        }
        Action("Review kill-switch reset", model.canAct() && account.optBoolean("kill"), secondary = true) {
            model.reviewPost("Reset the kill switch?", "The server rechecks account health and policy. Clearing the switch does not select a strategy trading mode.", "/api/control/reset", JSONObject())
        }
    }
    HoldingReviewForm(state, model)
    desk.obj("account").rows("positions").forEach { position -> Section("Exit ${position.text("symbol")}", "${position.text("quantity")} remaining virtual shares") {
        Action("Review full holding exit", model.canAct(), secondary = true) {
            model.reviewPost("Queue the full paper exit?", "This queues sale of the entire remaining holding and persists across restarts. Fresh reviewed prices and liquidity are required for fills.",
                "/api/paper/long-term/exit", json("symbol" to position.text("symbol")), position)
        }
    } }
    if (desk.optBoolean("bound_intraday_controller")) Section("Bound intraday controller") {
        Action("Review automation arm", model.canAct()) { model.reviewPost("Arm the bound paper controller?", "This can submit eligible paper orders without another proposal approval. The server rechecks every readiness and risk gate.", "/api/paper/automation/arm", JSONObject()) }
        Action("Disarm bound automation", model.canAct(), secondary = true) { model.reviewPost("Disarm paper automation?", "Pending proposals are revoked. Existing holdings still require protective execution and fresh prices.", "/api/paper/automation/disarm", JSONObject()) }
    }
    DetailCard("Risk, quotes, orders & basis evidence", model.data("console"), open = true, external = external)
}

@Composable private fun HoldingReviewForm(state: AppState, model: TraderViewModel) {
    var symbol by remember { mutableStateOf("") }; var date by remember { mutableStateOf(todayIst(model.data("desk").text("observed_at", ""))) }
    var result by remember { mutableStateOf("") }; var reference by remember { mutableStateOf("") }
    Section("Review a long-term price basis", "A calendar or working socket cannot prove corporate actions are absent. Review all changes since the last accepted quote, including offline periods.") {
        Choice("Stock", symbol, stockOptions(model.data("desk")), { symbol = it })
        Field("Review date · YYYY-MM-DD", date, { date = it })
        Choice("Your reviewed finding", result, listOf("clear" to "No uncovered corporate action", "quarantine" to "Unresolved action · quarantine stock"), { result = it })
        Field("Evidence reference", reference, { reference = it }, "Cite your actual review. A clear review cannot erase an existing persistent quarantine.", multiline = true)
        Action("Review basis record", model.canAct() && symbol.isNotBlank() && result.isNotBlank() && reference.trim().length >= 3) {
            model.reviewPost("Record this price-basis finding?", if (result == "clear") "This records the stated source review. It does not verify real custody or settlement and cannot clear a prior quarantine." else "This blocks the symbol across sessions. A reviewed offline corporate-action batch is needed to resolve it; another review cannot remove it.",
                "/api/paper/long-term/reviews", json("symbol" to symbol, "session_date" to date.trim(), "no_corporate_action" to (result == "clear"), "reference" to reference.trim()))
        }
    }
}

@Composable fun SettingsScreen(state: AppState, model: TraderViewModel) {
    val toggleAlerts = LocalProposalAlerts.current
    Section("App preferences") {
        Text("Appearance · Light", fontWeight = FontWeight.SemiBold)
        Text("Secure unlock · Strong hardware-backed biometrics")
        Text("Privacy · Locks in the background and after two idle minutes")
        Text("App ${BuildConfig.VERSION_NAME} · server ${model.data("setup").text("ui_version")}")
        Action(if (state.alertsEnabled) "Turn proposal alerts off" else "Enable proposal alerts", !state.busy && !BuildConfig.DEMO, secondary = true, onClick = toggleAlerts)
        Text("Optional generic notifications while the app stays unlocked. Backgrounding locks the app and stops alerts; there is no background push service.", style = MaterialTheme.typography.bodySmall)
        Action("Phone security & pairing", !state.busy, secondary = true) { model.navigate(Page.SECURITY) }
    }
    DetailCard("Configured account policy & operational limits", model.data("views").obj("settings"), open = true)
    Hint("Account economics are read-only here. Their reviewed server configuration cannot be changed by a phone preference.")
}

@Composable fun SecurityScreen(state: AppState, model: TraderViewModel) {
    var owner by remember { mutableStateOf("") }
    var emergency by remember { mutableStateOf(false) }
    Section("Protected on this phone", "Biometrics authorize the Keystore cryptographic operation; a simulated UI success cannot release the stored credential.") {
        Text("• Separate revocable phone credential; owner token is not stored\n• Short-lived server sessions in memory\n• Fixed HTTPS server and Android system certificate trust\n• No cloud/device-transfer backup, analytics or WebView\n• Secure-window and obscured-touch protection", style = MaterialTheme.typography.bodyMedium)
        Hint("A compromised or rooted device can still expose information while unlocked. These protections are not a security certification or a substitute for keeping Android updated.")
    }
    model.data("devices").rows("devices").forEach { device -> Section(device.text("label"), if (device.optBoolean("active")) "Active pairing" else "Revoked / inactive") {
        Text("Paired ${istTime(device.text("created_at"))}")
        Action("Revoke this phone", model.canAct() && device.optBoolean("active"), secondary = true) { model.revokePhone(device.text("id")) }
    } }
    Section("Lost phone or changed biometrics") {
        Text("Use owner authorization to revoke a lost phone below. Rotating the operator token invalidates all phone pairings. Changed biometric enrollment can invalidate this phone's encryption key and require pairing again.")
        TextButton({ emergency = !emergency }) { Text("Manage other paired phones") }
        if (emergency) {
            Field("Owner token · emergency device management", owner, { owner = it }, "Used only while this page stays unlocked. It is not saved.", secret = true)
            Action("Load my paired phones", model.canAct() && owner.length >= 32, secondary = true) {
                val supplied = owner; owner = ""; model.ownerPhones(supplied)
            }
            model.data("ownerDevices").rows("devices").forEach { device ->
                Text(device.text("label"), fontWeight = FontWeight.SemiBold)
                Text(if (device.optBoolean("active")) "Active · paired ${istTime(device.text("created_at"))}" else "Revoked / inactive")
                Action("Review revocation", model.canAct() && device.optBoolean("active"), secondary = true) { model.revokeOwnedPhone(device) }
            }
        }
    }
}

private val learning = listOf(
    "Prepare today" to "One action verifies the saved session, imports a missing catalog and acquires current completed history. It stops at the source/calendar/policy review. It never chooses a trading mode.",
    "Cash, equity and fees" to "Available virtual cash excludes commitments to pending buys. Equity also includes marked holdings. Fees and unavailable or stale holding prices can materially change the result. Accepted orders are not fills.",
    "Approval and automatic modes" to "Approval waits for your explicit review of each proposal. Automatic can submit eligible paper orders without another proposal confirmation. Neither mode guarantees a signal, a fill or profit; risk and freshness checks remain independent.",
    "Quote freshness and liquidity" to "A connected socket can have old, empty-sided or unusable quotes. Only accepted fresh reviewed prices and usable depth can drive paper fills. No missing liquidity is invented.",
    "Discovery and indicators" to "Discovery shows the installed prior-daily screen, not live recommendations. Indicator warmup and missing sessions matter. Short histories cannot manufacture SMA200 or certified multi-year returns. Fundamental data may be unavailable.",
    "Source and calendar review" to "Normal hours and a holiday feed are proposals. Review special sessions, actual exchange notices and corporate-action coverage. Downloads and successful login do not approve those facts.",
    "Policy drafts" to "A saved draft is an immutable research specification. Blank choices remain unresolved. It does not replace the installed strategy, change cash, create holdings or activate a longer-term investment engine.",
    "Backtesting" to "Simulations use registered inputs, explicit fees and independent virtual accounts. Input origin, chronology, policy, code and isolation limits constrain interpretation. The RPi runner can be unavailable when OS isolation has not been verified.",
    "Manual purchases and SIP" to "Each purchase needs an exact preview and confirmation. A SIP plan records explicit reviewed dates and cash caps; due occurrences still need individual preview. Missed dates stay missed. Cancellation preserves filled shares.",
    "Long-term price basis" to "Review actions since the last accepted quote, including offline periods. An unresolved action quarantines the stock across sessions. A normal review cannot remove that quarantine; a reviewed offline action workflow is required.",
    "Emergency controls" to "Kill stops new entries and pending buys. Queue exits requests sales but cannot force immediate fills without fresh prices and liquidity. Holdings remain open until recorded fills resolve them.",
    "Unknown results" to "A timeout does not prove an action failed. Inspect saved state before another instruction. The app does not automatically repeat consequential POST requests. Locking cannot undo a request already received by the server.",
    "Secure phone access" to "Pair once with the owner token. Strong biometrics release a separate device credential from Android Keystore to obtain a short-lived session. Biometrics stay on Android. Lock clears private app memory; the server and holdings continue.",
)

@Composable fun LearnScreen(model: TraderViewModel, external: (String) -> Unit) {
    var query by remember { mutableStateOf("") }
    Section("A plain-language guide") { Field("Search the guide", query, { query = it }) }
    learning.filter { (title, text) -> title.contains(query, true) || text.contains(query, true) }.forEach { (title, text) ->
        Section(title) { Text(text, style = MaterialTheme.typography.bodyMedium) }
    }
    DetailCard("Server research tools & limitations", model.data("views").obj("backtests"), external = external)
    Section("Official references") {
        Action("NSE notices & trading holidays", secondary = true) { external("https://www.nseindia.com/resources/exchange-communication-holidays") }
        Action("Kite authentication documentation", secondary = true) { external("https://kite.trade/docs/connect/v3/user/") }
    }
}
