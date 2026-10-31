package com.shanmukhan.agentictrader

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class DailyJourneyTest {
    private fun state(installed: Boolean = false): AppState {
        val job = json("job_id" to "c".repeat(32), "state" to if (installed) "installed" else "ready_for_review", "universe" to "nifty50", "preview_sha256" to "d".repeat(64))
        val desk = json("observed_at" to "2026-10-29T09:00:00+05:30", "strategy_mode" to "rules", "mode" to "manual",
            "preparation" to json("job" to job, "download_prerequisites" to json("session_verified" to true)),
            "readiness" to json("checks" to JSONArray(listOf(json("key" to "strategy", "ready" to installed)))))
        val setup = json("sessions" to JSONArray(listOf(json("date" to "2026-10-29", "close" to "15:30"))))
        val audit = json("preparation" to JSONObject(job.toString()), "source_validation" to json("hashes_valid" to true, "same_ist_date" to true, "coverage_valid" to true))
        return AppState(data = mapOf("desk" to desk, "setup" to setup, "dailyAudit" to audit), journeyAuditKey = DailyJourney.auditKey(desk, setup))
    }
    @Test fun progressRequiresEvidenceAndExplicitInstallation() {
        assertEquals(0, DailyJourney.step(AppState()))
        val state = state()
        assertEquals(2, DailyJourney.step(state))
        assertEquals(1, DailyJourney.step(state.copy(journeyAuditKey = "")))
        assertEquals(3, DailyJourney.step(state(installed = true)))
        state.data.getValue("desk").obj("preparation").obj("download_prerequisites").put("session_verified", false)
        assertEquals(0, DailyJourney.step(state))
    }
    @Test fun alteredEvidenceNeverSkipsPreparation() {
        listOf("hashes_valid", "same_ist_date", "coverage_valid").forEach { flag ->
            val state = state(true)
            state.data.getValue("dailyAudit").obj("source_validation").put(flag, false)
            assertEquals(flag, 1, DailyJourney.step(state))
        }
        val state = state(true)
        state.data.getValue("dailyAudit").obj("preparation").put("job_id", "e".repeat(32))
        assertEquals(1, DailyJourney.step(state))
    }
    @Test fun serverDayReviewedCloseAndChangedJobInvalidateCachedAudit() {
        listOf("2026-10-29T15:30:00+05:30", "2026-10-30T09:00:00+05:30").forEach { time ->
            val state = state(true)
            state.data.getValue("desk").put("observed_at", time)
            assertEquals(1, DailyJourney.step(state))
        }
        val state = state(true)
        state.data.getValue("desk").obj("preparation").obj("job").put("preview_sha256", "f".repeat(64))
        assertEquals(1, DailyJourney.step(state))
    }
    @Test fun proposedCalendarCloseInvalidatesHistoryBeforeFirstInstallation() {
        val initial = state()
        val desk = initial.data.getValue("desk")
        val setup = initial.data.getValue("setup").put("sessions", JSONArray())
        desk.obj("preparation").obj("job").put("calendar_csv", "date,open,close,source\n2026-10-29,09:15,15:30,https://example.test/notice\n")
        val current = initial.copy(journeyAuditKey = DailyJourney.auditKey(desk, setup))
        assertTrue(DailyJourney.dataReady(current))
        desk.put("observed_at", "2026-10-29T15:30:00+05:30")
        assertFalse(DailyJourney.dataReady(current))
    }

    @Test fun incompleteGuidedReceiptCannotPretendInstallationFinished() {
        val state = state(true)
        val desk = state.data.getValue("desk")
        desk.put("guided_setup", json("state" to "stopped", "plan" to json("job_id" to "c".repeat(32))))
        assertEquals(2, DailyJourney.step(state))
        desk.obj("guided_setup").put("state", "complete")
        assertEquals(3, DailyJourney.step(state))
    }
    @Test fun previousDayOrFutureProfileCheckDoesNotEstablishTodayAccess() {
        val desk = json("observed_at" to "2026-10-29T09:00:00+05:30")
        val setup = json("profile_verified_this_run" to true, "profile_checked_at" to "2026-10-28T09:00:00+05:30")
        assertFalse(DailyJourney.sessionReady(desk, setup))
        setup.put("profile_checked_at", "2026-10-29T08:59:00+05:30")
        assertTrue(DailyJourney.sessionReady(desk, setup))
        assertFalse(DailyJourney.sessionReady(JSONObject(), setup))
        setup.put("profile_checked_at", "2026-10-29T09:01:00+05:30")
        assertFalse(DailyJourney.sessionReady(desk, setup))
    }
    @Test fun unconfiguredPolicyHasNoSilentRulesFallback() {
        assertEquals("", DailyJourney.policy(AppState()))
        assertEquals("rules", DailyJourney.policy(state()))
        assertEquals("rules_ml", DailyJourney.policy(state().copy(journeyPolicy = "rules_ml")))
    }
}
