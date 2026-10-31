package com.shanmukhan.agentictrader

import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import android.net.Uri
import android.os.Bundle
import android.view.MotionEvent
import android.view.WindowManager
import androidx.activity.compose.setContent
import androidx.activity.compose.BackHandler
import androidx.activity.viewModels
import androidx.activity.result.contract.ActivityResultContracts
import androidx.browser.customtabs.CustomTabsIntent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.fragment.app.FragmentActivity
import androidx.lifecycle.compose.collectAsStateWithLifecycle

class MainActivity : FragmentActivity() {
    private val model: TraderViewModel by viewModels()
    private lateinit var gate: BiometricGate
    private val alerts by lazy { PhoneAlerts(this) }
    private val notificationPermission = registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted -> model.alerts(granted) }
    private fun toggleAlerts() {
        if (model.state.value.alertsEnabled) model.alerts(false)
        else if (android.os.Build.VERSION.SDK_INT >= 33 && !alerts.allowed()) notificationPermission.launch(android.Manifest.permission.POST_NOTIFICATIONS)
        else model.alerts(alerts.allowed())
    }
    override fun onCreate(savedInstanceState: Bundle?) {
        val splash = installSplashScreen()
        super.onCreate(savedInstanceState)
        splash.setOnExitAnimationListener { provider ->
            if (android.animation.ValueAnimator.areAnimatorsEnabled())
                provider.view.animate().alpha(0f).setDuration(160).withEndAction { provider.remove() }.start()
            else provider.remove()
        }
        if (!BuildConfig.DEMO) window.addFlags(WindowManager.LayoutParams.FLAG_SECURE)
        gate = BiometricGate(this)
        setContent { TraderTheme {
            val state by model.state.collectAsStateWithLifecycle()
            LaunchedEffect(state.unlocked, state.alertsEnabled, state.stale, state.data["desk"]) { alerts.update(state) }
            CompositionLocalProvider(LocalProposalAlerts provides ::toggleAlerts) { TraderApp(model, gate, ::openExternal) }
        } }
    }
    private fun openExternal(url: String) {
        val parsed = Uri.parse(url)
        if (parsed.scheme != "https" || parsed.host.isNullOrBlank() || parsed.userInfo != null) {
            model.reportError("Only secure HTTPS sources can be opened."); return
        }
        try { CustomTabsIntent.Builder().setShowTitle(true).build().launchUrl(this, parsed) }
        catch (_: Exception) { model.reportError("No secure browser could open this page.") }
    }
    override fun dispatchTouchEvent(event: MotionEvent): Boolean {
        if (event.flags and (MotionEvent.FLAG_WINDOW_IS_OBSCURED or MotionEvent.FLAG_WINDOW_IS_PARTIALLY_OBSCURED) != 0) return false
        return super.dispatchTouchEvent(event)
    }
    override fun onUserInteraction() { super.onUserInteraction(); model.touch() }
    override fun onStop() {
        gate.cancel()
        alerts.clear()
        model.lock()
        super.onStop()
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable fun TraderApp(model: TraderViewModel, gate: BiometricGate, external: (String) -> Unit) {
    val state by model.state.collectAsStateWithLifecycle()
    val pageScroll = rememberScrollState()
    LaunchedEffect(state.page) { pageScroll.scrollTo(0) }
    BackHandler(state.unlocked && state.page != Page.HOME) { model.navigate(Page.HOME) }
    LaunchedEffect(state.brokerUrl) { state.brokerUrl?.let { external(it); model.brokerOpened() } }
    if (!state.unlocked) { CompositionLocalProvider(LocalFormEnabled provides !state.busy) { UnlockScreen(state, model, gate) }; return }
    val bottom = listOf(Page.HOME to Icons.Outlined.Home, Page.WATCHLIST to Icons.Outlined.PlaylistAddCheck,
        Page.PAPER to Icons.Outlined.SwapHoriz, Page.PORTFOLIO to Icons.Outlined.AccountBalanceWallet,
        Page.MORE to Icons.Outlined.GridView)
    Scaffold(containerColor = CanvasColor,
        topBar = { Column { TopAppBar(title = { Column {
            Text("AGENTIC TRADER", style = MaterialTheme.typography.labelSmall, color = Teal)
            Text(state.page.title, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
        } }, actions = {
            IconButton({ model.refresh() }, enabled = !state.busy) { Icon(Icons.Outlined.Refresh, "Refresh displayed status") }
            IconButton({ model.lock() }) { Icon(Icons.Outlined.Lock, "Lock account") }
        }, colors = TopAppBarDefaults.topAppBarColors(containerColor = CanvasColor))
            Row(Modifier.fillMaxWidth().padding(horizontal = 18.dp), verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                AssistChip(onClick = { model.showEnvironment(true) }, enabled = !state.busy && state.review == null,
                    label = { Text("Paper") }, trailingIcon = { Icon(Icons.Outlined.ExpandMore, "Choose trading environment") })
                Text("Virtual funds", style = MaterialTheme.typography.labelMedium, color = Teal)
            }
        } },
        bottomBar = { NavigationBar(containerColor = androidx.compose.ui.graphics.Color.White) {
            bottom.forEach { (page, icon) ->
                NavigationBarItem(selected = state.page == page, onClick = { model.navigate(page) },
                    icon = { Icon(icon, page.title) }, label = { Text(when (page) {
                        Page.HOME -> "Home"; Page.WATCHLIST -> "Watchlist"; Page.PAPER -> "Trade"; Page.PORTFOLIO -> "Portfolio"; else -> "More"
                    }) }, enabled = !state.busy && state.review == null)
            }
        } }) { insets ->
        Column(Modifier.padding(insets).fillMaxSize(), horizontalAlignment = Alignment.CenterHorizontally) {
            Box(Modifier.fillMaxWidth().height(4.dp)) { if (state.busy) LinearProgressIndicator(Modifier.fillMaxWidth()) }
            Column(Modifier.widthIn(max = 900.dp).fillMaxWidth().verticalScroll(pageScroll)
                .padding(horizontal = 18.dp, vertical = 12.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
                if (BuildConfig.DEMO) Hint("OFFLINE DEMO · all balances, stocks and outcomes are invented. No Internet access.")
                if (state.progress.isNotBlank()) Text(state.progress, color = Teal, style = MaterialTheme.typography.bodyMedium)
                state.error?.let { Hint(it, error = true) }
                state.notice?.let { Hint(it, success = !BuildConfig.DEMO) }
                if (state.stale) Hint("Displayed data may be stale. Actions wait until the server can be checked again.")
                if (state.reconcile) {
                    Hint("A previous instruction may have completed. Inspect ${state.reconcilePage.title.lowercase()} before creating another instruction.")
                    Action("Inspect saved outcome", secondary = true, enabled = !state.busy) { model.navigate(state.reconcilePage) }
                    if (state.page == state.reconcilePage) Action("I inspected the saved outcome", secondary = true, enabled = !state.busy && !state.stale) { model.acknowledgeReconciliation() }
                }
                if (!state.data.containsKey("desk")) WorkspaceLoadingScreen(state.busy)
                else CompositionLocalProvider(LocalFormEnabled provides (!state.busy && state.review == null)) { NativeScreen(state, model, external) }
                Text("Virtual INR · paper trading only", style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(vertical = 10.dp))
            }
        }
    }
    if (state.environmentDialog) EnvironmentDialog { model.showEnvironment(false) }
    if (state.modeHelp != null) ModeHelpDialog(state, model)
    state.review?.let { review -> ReviewSheet(review, !state.busy && !state.stale && !state.reconcile,
        { model.cancelReview() }, { model.confirmReview(it) }, external) }
    state.pendingPage?.let {
        AlertDialog(onDismissRequest = { model.discardNavigation(false) }, title = { Text("Discard unsaved changes?") },
            text = { Text("These edits have not been saved. Stay here to review/save them, or discard this copy before leaving.") },
            confirmButton = { TextButton({ model.discardNavigation(true) }) { Text("Discard and leave") } },
            dismissButton = { TextButton({ model.discardNavigation(false) }) { Text("Keep editing") } })
    }
}

@Composable internal fun UnlockScreen(state: AppState, model: TraderViewModel, gate: BiometricGate) {
    var owner by remember { mutableStateOf("") }
    var label by remember { mutableStateOf("My Android phone") }
    var forget by remember { mutableStateOf(false) }
    Column(Modifier.fillMaxSize().background(androidx.compose.ui.graphics.Brush.verticalGradient(
        listOf(CanvasColor, androidx.compose.ui.graphics.Color(0xFFE4F3F0), CanvasColor)))
        .safeDrawingPadding().imePadding().verticalScroll(rememberScrollState()).padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(22.dp)) {
        Spacer(Modifier.height(20.dp))
        BrandMark(88.dp)
        Text("Agentic Trader", style = MaterialTheme.typography.headlineLarge, fontWeight = FontWeight.Bold)
        Text("Clarity for every market day.", style = MaterialTheme.typography.titleMedium, color = Teal)
        Text(if (state.paired) "Use your fingerprint to unlock this phone's encrypted access. Your biometric never leaves Android."
            else "Pair this phone once. After that, unlock with strong biometrics instead of typing a long token.",
            color = MaterialTheme.colorScheme.onSurfaceVariant)
        state.error?.let { Hint(it, error = true) }
        if (state.busy) { LinearProgressIndicator(Modifier.fillMaxWidth()); Text(state.progress) }
        if (state.paired) {
            Action("Unlock with biometrics", enabled = !state.busy) { model.unlock(gate) }
            TextButton({ forget = true }, enabled = !state.busy) { Text("Pair this phone again") }
        } else Section("Pair your Android phone") {
            Field("Phone name", label, { label = it }, "A name you recognize in your paired-phone list.")
            Field("Server operator token", owner, { owner = it }, "Use the server token once. It is not saved on this phone.", secret = true)
            Action("Pair and protect this phone", enabled = !state.busy && owner.length >= 32 && label.isNotBlank()) {
                val supplied = owner; owner = ""; model.pair(supplied, label, gate)
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Outlined.Fingerprint, null, tint = Teal)
            Text("Hardware-backed protection · private by design", style = MaterialTheme.typography.labelMedium)
        }
        if (!state.paired) Hint("Requires Android 11 or newer, a secure screen lock and hardware-backed strong biometrics. A changed biometric enrollment can require pairing again.")
        Text("Connects only to shanmukhan.com over HTTPS. Paper account only.", style = MaterialTheme.typography.bodySmall)
    }
    if (forget) AlertDialog(onDismissRequest = { forget = false }, title = { Text("Remove local phone access?") },
        text = { Text("This removes the encrypted pairing on this phone. Pairing again needs the owner token. It does not stop the server or close holdings.") },
        confirmButton = { TextButton({ forget = false; model.forgetPhone() }) { Text("Remove local pairing") } },
        dismissButton = { TextButton({ forget = false }) { Text("Cancel") } })
}

@Composable private fun ReviewSheet(review: Review, enabled: Boolean, cancel: () -> Unit,
                                  confirm: (Boolean) -> Unit, external: (String) -> Unit) {
    var acknowledged by remember(review) { mutableStateOf(false) }
    Dialog(cancel, properties = DialogProperties(usePlatformDefaultWidth = false, dismissOnClickOutside = false)) {
        Surface(modifier = Modifier.fillMaxWidth().widthIn(max = 900.dp).fillMaxHeight(.94f).padding(12.dp),
            shape = RoundedCornerShape(24.dp), color = MaterialTheme.colorScheme.surface) {
            Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text(review.title, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                Column(Modifier.weight(1f).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(18.dp)) {
                    Text(review.explanation, style = MaterialTheme.typography.bodyMedium)
                    DetailTree(review.details, external = external)
                    Acknowledge("I reviewed the displayed values, effects and limitations.", acknowledged, { acknowledged = it })
                }
                Action(review.confirmLabel, enabled && acknowledged) { confirm(acknowledged) }
                Action("Cancel", secondary = true, onClick = cancel)
            }
        }
    }
}
