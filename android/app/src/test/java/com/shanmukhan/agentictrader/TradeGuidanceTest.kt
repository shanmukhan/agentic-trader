package com.shanmukhan.agentictrader

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class TradeGuidanceTest {
    @Test fun omittedOrContradictoryReadinessNeverEnablesModeReview() {
        assertFalse(modeIsReady(JSONObject()))
        val desk = json("blockers" to JSONArray(), "readiness" to json("can_start" to false))
        assertFalse(modeIsReady(desk))
        desk.obj("readiness").put("can_start", true)
        assertTrue(modeIsReady(desk))
        desk.put("blockers", JSONArray(listOf("NO_FRESH_EXECUTION_QUOTES")))
        assertFalse(modeIsReady(desk))
    }
    @Test fun oldBackendFallbackPreservesReasonsAndDoesNotInventAnEntryTime() {
        val desk = json("blockers" to JSONArray(listOf("FEED_DISCONNECTED")), "readiness" to json("checks" to JSONArray()))
        val guide = tradeGuidance(desk)
        assertEquals("Feed disconnected", guide.rows("items").single().text("title"))
        assertFalse(guide.has("next_entry_at"))
        assertNotEquals("Ready to review a paper mode", guide.text("title"))
    }
    @Test fun actionsMapOnlyToSupportedReadOnlyDestinations() {
        assertEquals(Page.BROKER, guidanceTarget("broker"))
        assertEquals(Page.STRATEGY, guidanceTarget("strategy"))
        assertEquals(Page.RISK, guidanceTarget("risk"))
        assertEquals(Page.WATCHLIST, guidanceTarget("watchlist"))
        assertNull(guidanceTarget("automatic"))
        assertNull(guidanceTarget("https://example.test"))
    }
}
