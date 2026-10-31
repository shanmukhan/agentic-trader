package com.shanmukhan.agentictrader

import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class NativeContractsTest {
    @Test fun moneyIsExactAndNeverRoundsAwayPaise() {
        assertEquals("₹25,000.00", decimalMoney("25000.00"))
        assertEquals("₹1,23,45,67,890.12", decimalMoney("1234567890.12"))
        assertEquals("−₹0.01", decimalMoney("-0.01"))
        assertEquals("Not available", decimalMoney("0.001"))
        assertEquals("Not available", decimalMoney("NaN"))
        assertEquals("Not available", decimalMoney(""))
    }

    @Test fun requestsStayWithinTheFixedHttpsApiAndRejectEncodedTraversal() {
        listOf("/api/desk", "/api/research/series?symbol=NSE%3AM%26M&timeframe=1d",
            "/api/paper/orders/contrib-123/cancel").forEach { assertTrue(it, HttpsTransport.allowedPath(it)) }
        listOf("https://evil.test/api/desk", "//evil.test/api/desk", "/api/../setup",
            "/api/%2e%2e/setup", "/api/%5cevil", "/api/desk#fragment", "/api/desk\r\nOther: value")
            .forEach { assertFalse(it, HttpsTransport.allowedPath(it)) }
    }

    @Test fun previewsAndSessionChecksDoNotTriggerFinancialUnknownOutcomeHandling() {
        assertFalse(HttpsTransport.consequential("GET", "/api/desk"))
        assertFalse(HttpsTransport.consequential("POST", "/api/setup/profile"))
        assertFalse(HttpsTransport.consequential("POST", "/api/paper/portfolio/preview"))
        assertTrue(HttpsTransport.consequential("POST", "/api/paper/portfolio/contributions"))
        assertTrue(HttpsTransport.consequential("POST", "/api/desk/mode"))
        assertTrue(HttpsTransport.consequential("POST", "/api/backtests/jobs"))
    }

    @Test fun draftParametersPreserveUnresolvedFieldsAndExactDecimalStrings() {
        val definitions = listOf(
            json("name" to "horizon_count", "label" to "Horizon", "kind" to "integer"),
            json("name" to "cash_reserve_pct", "label" to "Cash reserve", "kind" to "decimal"),
            json("name" to "review_frequency", "label" to "Reviews", "kind" to "choice"),
        )
        val empty = PolicyPayload.build("My policy", definitions, emptyMap()).obj("parameters")
        assertTrue(empty.isNull("horizon_count")); assertTrue(empty.isNull("cash_reserve_pct"))
        assertTrue(empty.isNull("review_frequency"))
        val exact = PolicyPayload.build("My policy", definitions,
            mapOf("horizon_count" to "12", "cash_reserve_pct" to "17.1234", "review_frequency" to "monthly")).obj("parameters")
        assertEquals(12, exact.getInt("horizon_count"))
        assertTrue(exact.get("horizon_count") is Int)
        assertEquals("17.1234", exact.get("cash_reserve_pct"))
        try { PolicyPayload.build("My policy", definitions, mapOf("horizon_count" to "1.5")); fail() } catch (_: IllegalArgumentException) { }
        try { PolicyPayload.build("My policy", definitions, mapOf("cash_reserve_pct" to "NaN")); fail() } catch (_: NumberFormatException) { }
    }

    @Test fun nullFinancialAndIndicatorValuesRemainUnavailable() {
        val data = JSONObject("""{"sma200":null,"cash":"0.00","quantity":0}""")
        assertEquals("Not available", data.text("sma200"))
        assertEquals("0.00", data.text("cash"))
        assertEquals("0", data.text("quantity"))
        assertEquals("Not available", data.text("missing"))
    }
}
