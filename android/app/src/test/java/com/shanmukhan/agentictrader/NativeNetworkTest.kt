package com.shanmukhan.agentictrader

import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.junit.Assert.*
import org.junit.Test
import java.net.ServerSocket
import java.net.Socket
import java.util.concurrent.CopyOnWriteArrayList
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.CountDownLatch

class NativeNetworkTest {
    @Test fun cancellationCleanupRunsOffTheCallingThreadAndSurvivesAClosingFailure() {
        val caller = Thread.currentThread()
        val finished = CountDownLatch(1)
        var worker: Thread? = null
        cleanupNetwork { throw java.io.IOException("INVENTED TLS close failure") }
        cleanupNetwork { worker = Thread.currentThread(); finished.countDown() }
        assertTrue(finished.await(3, TimeUnit.SECONDS))
        assertNotSame(caller, worker)
    }

    @Test fun idleConnectionIsRetiredBeforeTheNextInstructionWithoutRetryingIt() {
        val connections = CopyOnWriteArrayList<Socket>()
        val requests = CopyOnWriteArrayList<String>()
        val executor = Executors.newSingleThreadExecutor()
        ServerSocket(0).use { server ->
            server.soTimeout = 5000
            val worker = executor.submit {
                repeat(2) {
                    // Keep the earlier socket open: the client must independently retire it.
                    val socket = server.accept().also(connections::add)
                    socket.soTimeout = 3000
                    val input = socket.getInputStream().bufferedReader()
                    val request = input.readLine()
                    var length = 0
                    while (true) {
                        val header = input.readLine() ?: error("Missing HTTP header terminator")
                        if (header.isEmpty()) break
                        if (header.startsWith("Content-Length:", true)) length = header.substringAfter(':').trim().toInt()
                    }
                    val body = CharArray(length)
                    var count = 0
                    while (count < length) {
                        val read = input.read(body, count, length - count)
                        check(read > 0); count += read
                    }
                    requests.add(request + " " + String(body))
                    socket.getOutputStream().write("HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: keep-alive\r\n\r\n{}".toByteArray())
                    socket.getOutputStream().flush()
                }
            }
            val client = phoneHttpClient().newBuilder().callTimeout(3, TimeUnit.SECONDS).build()
            try {
                val url = "http://127.0.0.1:${server.localPort}/synthetic"
                client.newCall(Request.Builder().url(url).build()).execute().use { assertEquals("{}", it.body.string()) }
                Thread.sleep(1500)
                client.newCall(Request.Builder().url(url).post("INVENTED-ONE-INSTRUCTION".toRequestBody()).build()).execute().use { assertEquals(200, it.code); it.body.string() }
                worker.get(5, TimeUnit.SECONDS)
                assertEquals(2, connections.size)
                assertEquals(2, requests.size)
                assertEquals(1, requests.count { it.startsWith("POST ") && it.endsWith("INVENTED-ONE-INSTRUCTION") })
            } finally {
                client.dispatcher.cancelAll(); client.connectionPool.evictAll()
                connections.forEach { it.close() }
                executor.shutdownNow()
            }
        }
    }
}
