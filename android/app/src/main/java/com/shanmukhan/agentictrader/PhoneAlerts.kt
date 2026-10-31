package com.shanmukhan.agentictrader

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import androidx.compose.runtime.staticCompositionLocalOf

val LocalProposalAlerts = staticCompositionLocalOf<() -> Unit> { {} }

/** Optional foreground-only, generic alerts. No background polling or financial lock-screen data. */
class PhoneAlerts(private val context: Context) {
    private val manager = context.getSystemService(NotificationManager::class.java)
    private var shown = emptySet<String>()
    fun allowed() = manager.areNotificationsEnabled()
    fun clear() { manager.cancel(17); shown = emptySet() }
    fun update(state: AppState) {
        if (!state.unlocked || !state.alertsEnabled || state.stale || !allowed() || BuildConfig.DEMO) { clear(); return }
        val ids = state.data["desk"]?.rows("decisions").orEmpty()
            .filter { it.text("state") == "awaiting_approval" }.map { it.text("id") }.toSet()
        if (ids.isEmpty()) { clear(); return }
        if (ids == shown) return
        manager.createNotificationChannel(NotificationChannel("paper_proposals", "Paper proposal reviews", NotificationManager.IMPORTANCE_DEFAULT))
        val open = PendingIntent.getActivity(context, 17, Intent(context, MainActivity::class.java), PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        manager.notify(17, Notification.Builder(context, "paper_proposals")
            .setSmallIcon(R.drawable.ic_notification).setContentTitle("Paper proposal needs review")
            .setContentText("Open Agentic Trader to inspect current account status.")
            .setVisibility(Notification.VISIBILITY_SECRET).setAutoCancel(true).setOnlyAlertOnce(true)
            .setContentIntent(open).build())
        shown = ids
    }
}
