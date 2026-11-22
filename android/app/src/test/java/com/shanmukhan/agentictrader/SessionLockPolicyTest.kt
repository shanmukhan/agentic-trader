package com.shanmukhan.agentictrader

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.Instant

class SessionLockPolicyTest {
    @Test fun switchingAppsWithinIdleWindowKeepsSessionUnlocked() {
        val now = Instant.parse("2026-11-22T06:30:00Z")
        val expires = "2026-11-22T06:45:00Z"
        assertFalse(SessionLockPolicy.expired(unlocked = true, demo = false, lastTouchElapsed = 10_000L, nowElapsed = 55_000L, expiresAt = expires, nowInstant = now))
        assertFalse(SessionLockPolicy.expired(unlocked = true, demo = false, lastTouchElapsed = 10_000L, nowElapsed = 130_000L, expiresAt = expires, nowInstant = now))
    }

    @Test fun exceedingIdleTimeoutLocksEvenBeforeServerSessionExpires() {
        val now = Instant.parse("2026-11-22T06:30:00Z")
        val expires = "2026-11-22T06:45:00Z"
        assertTrue(SessionLockPolicy.expired(unlocked = true, demo = false, lastTouchElapsed = 10_000L, nowElapsed = 130_001L, expiresAt = expires, nowInstant = now))
    }

    @Test fun serverSessionExpiryLocksWithinIdleWindow() {
        val now = Instant.parse("2026-11-22T06:45:00Z")
        val expires = "2026-11-22T06:45:00Z"
        assertTrue(SessionLockPolicy.expired(unlocked = true, demo = false, lastTouchElapsed = 10_000L, nowElapsed = 15_000L, expiresAt = expires, nowInstant = now))
    }

    @Test fun lockedOrDemoStatesNeverReportSessionExpiry() {
        val now = Instant.parse("2026-11-22T06:50:00Z")
        val expires = "2026-11-22T06:45:00Z"
        assertFalse(SessionLockPolicy.expired(unlocked = false, demo = false, lastTouchElapsed = 0L, nowElapsed = 500_000L, expiresAt = expires, nowInstant = now))
        assertFalse(SessionLockPolicy.expired(unlocked = true, demo = true, lastTouchElapsed = 0L, nowElapsed = 500_000L, expiresAt = expires, nowInstant = now))
    }
}
