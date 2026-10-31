package com.shanmukhan.agentictrader

import androidx.test.platform.app.InstrumentationRegistry
import kotlinx.coroutines.runBlocking
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.Test
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

/** Explicit opt-in read-only device acceptance. Never sends a credential or account instruction. */
class ProductionNetworkTest {
    @Test fun publicReadsSurviveIdleAndUiThreadCancellation() {
        assumeTrue(InstrumentationRegistry.getArguments().getString("allow_public_network") == "true")
        val transport = HttpsTransport()
        try {
            val before = runBlocking { transport.request("GET", "/api/mobile/release", null, null) }
            assertTrue(before.getString("sha256").matches(Regex("[a-f0-9]{64}")))
            Thread.sleep(6500)
            val after = runBlocking { transport.request("GET", "/api/mobile/release", null, null) }
            assertEquals(before.getString("package_name"), after.getString("package_name"))
            InstrumentationRegistry.getInstrumentation().runOnMainSync { transport.cancel() }
            val cleaned = CountDownLatch(1)
            cleanupNetwork { cleaned.countDown() }
            assertTrue(cleaned.await(5, TimeUnit.SECONDS))
            val fresh = runBlocking { transport.request("GET", "/api/mobile/release", null, null) }
            assertEquals(before.getString("package_name"), fresh.getString("package_name"))
        } finally { transport.cancel() }
    }
}
