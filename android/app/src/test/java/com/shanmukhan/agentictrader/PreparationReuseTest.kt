package com.shanmukhan.agentictrader

import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class PreparationReuseTest {
    private fun job(state: String = "ready_for_review") = json("job_id" to "a".repeat(32),
        "state" to state, "universe" to "nifty100", "snapshot_at" to "2026-10-28T03:25:00+00:00")
    private fun report(state: String = "ready_for_review") = json("preparation" to job(state),
        "observed_at" to "2026-10-28T03:30:00+00:00", "source_validation" to json(
            "hashes_valid" to true, "same_ist_date" to true, "coverage_valid" to true))

    @Test fun recentReadyOrInstalledDownloadCanBeReused() {
        listOf("ready_for_review", "installed").forEach { state ->
            assertTrue(PreparationReuse.verified(report(state), "nifty100", job(state)))
        }
    }
    @Test fun lightweightOrMissingAuditCannotEstablishReuse() {
        assertFalse(PreparationReuse.verified(report().put("source_validation", JSONObject.NULL), "nifty100", job()))
        assertFalse(PreparationReuse.verified(JSONObject(), "nifty100", job()))
    }
    @Test fun staleChangedOrIncompleteEvidenceCannotBeReused() {
        listOf("hashes_valid", "same_ist_date", "coverage_valid").forEach { flag ->
            val stale = report().apply { obj("source_validation").put(flag, false) }
            assertFalse(flag, PreparationReuse.verified(stale, "nifty100", job()))
        }
    }
    @Test fun reuseIsBoundToTheRequestedUniverseAndCurrentCompletedJob() {
        assertFalse(PreparationReuse.verified(report(), "nifty500", job()))
        assertFalse(PreparationReuse.verified(report(), "nifty100", job().put("job_id", "b".repeat(32))))
        assertFalse(PreparationReuse.verified(report(), "nifty100", job("downloading")))
        assertFalse(PreparationReuse.verified(report("failed"), "nifty100", job("failed")))
    }
    @Test fun officialFiftyHasItsOwnNameAndAuditedReuseContract() {
        assertEquals("Nifty 50", universeName("nifty50"))
        assertEquals("Nifty 100", universeName("nifty100"))
        assertEquals("Nifty 500", universeName("nifty500"))
        val audit = report()
        audit.obj("preparation").put("universe", "nifty50")
        val current = job().put("universe", "nifty50")
        assertTrue(PreparationReuse.verified(audit, "nifty50", current))
        assertFalse(PreparationReuse.verified(audit, "nifty100", current))
    }
}
