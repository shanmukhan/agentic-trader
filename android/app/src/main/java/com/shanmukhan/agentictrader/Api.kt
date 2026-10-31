package com.shanmukhan.agentictrader

import kotlinx.coroutines.suspendCancellableCoroutine
import okhttp3.Call
import okhttp3.Callback
import okhttp3.ConnectionPool
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import org.json.JSONObject
import java.io.IOException
import java.io.ByteArrayOutputStream
import java.net.URLDecoder
import java.util.concurrent.TimeUnit
import java.util.concurrent.Executors
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

class ApiFailure(val status: Int, message: String, val uncertain: Boolean = false, val endpoint: String = "") : Exception(message)

interface Transport {
    suspend fun request(method: String, path: String, token: String?, body: JSONObject?): JSONObject
    fun cancel()
}

internal fun phoneHttpClient(): OkHttpClient = OkHttpClient.Builder()
        .followRedirects(false).followSslRedirects(false).retryOnConnectionFailure(false)
        // Retire idle sockets before this deployment's five-second upstream timeout.
        // Keep mutation retries disabled: a lost response never proves rejection.
        .connectionPool(ConnectionPool(2, 1, TimeUnit.SECONDS))
        .connectTimeout(15, TimeUnit.SECONDS).readTimeout(45, TimeUnit.SECONDS)
        .callTimeout(50, TimeUnit.SECONDS).build()

private val networkCleanup = Executors.newSingleThreadExecutor { work ->
    Thread(work, "agentic-network-cleanup").apply { isDaemon = true }
}
internal fun cleanupNetwork(action: () -> Unit) { networkCleanup.execute { runCatching(action) } }

class HttpsTransport : Transport {
    @Volatile private var client = phoneHttpClient()

    companion object {
        const val ORIGIN = "https://shanmukhan.com/agentic-trader"
        fun allowedPath(path: String): Boolean = try {
            val decoded = URLDecoder.decode(path.substringBefore('?'), "UTF-8")
            path.startsWith("/api/") && decoded.startsWith("/api/") &&
                decoded.split('/').none { it == "." || it == ".." } && !decoded.contains("//") &&
                !(decoded + path).any { it in listOf('\\', '#', '\r', '\n') } && !path.contains("://")
        } catch (_: Exception) { false }
        fun consequential(method: String, path: String): Boolean = method != "GET" &&
            path != "/api/setup/profile" && path != "/api/mobile/session" && !path.endsWith("/preview")
    }

    override suspend fun request(method: String, path: String, token: String?, body: JSONObject?): JSONObject {
        require(allowedPath(path)) { "Unsupported app destination." }
        require(method in listOf("GET", "POST", "DELETE"))
        val builder = Request.Builder().url(ORIGIN + path).header("Cache-Control", "no-store")
        if (token != null) builder.header("Authorization", "Bearer $token")
        val requestBody = if (method == "POST") (body ?: JSONObject()).toString()
            .toRequestBody("application/json; charset=utf-8".toMediaType()) else null
        val call = client.newCall(builder.method(method, requestBody).build())
        return suspendCancellableCoroutine { continuation ->
            continuation.invokeOnCancellation { cleanupNetwork { call.cancel() } }
            call.enqueue(object : Callback {
                override fun onFailure(call: Call, e: IOException) {
                    if (continuation.isActive) continuation.resumeWithException(ApiFailure(0,
                        if (method == "GET") "Could not reach your server. Displayed data may be stale."
                        else "The result is unknown. Inspect saved state before another instruction.", consequential(method, path), path))
                }
                override fun onResponse(call: Call, response: Response) {
                    response.use {
                        try {
                            val bytes = it.body.byteStream().use { stream ->
                                val out = ByteArrayOutputStream(); val buffer = ByteArray(8192)
                                while (out.size() <= 8 * 1024 * 1024) {
                                    val count = stream.read(buffer, 0, minOf(buffer.size, 8 * 1024 * 1024 + 1 - out.size()))
                                    if (count < 0) break
                                    out.write(buffer, 0, count)
                                }
                                out.toByteArray()
                            }
                            if (bytes.size > 8 * 1024 * 1024) throw ApiFailure(0, "Server response is too large.", consequential(method, path), path)
                            val value = try { JSONObject(String(bytes, Charsets.UTF_8)) } catch (_: Exception) {
                                if (it.isSuccessful) throw ApiFailure(0, "Server response could not be validated.", consequential(method, path), path)
                                JSONObject()
                            }
                            if (!it.isSuccessful) {
                                val detail = value.optString("detail", "").takeIf { text -> !text.startsWith("[") && text.isNotBlank() }
                                    ?: value.optJSONObject("error")?.optString("message")
                                    ?: "Request could not be completed. Review the current server status."
                                throw ApiFailure(it.code, detail.take(500), consequential(method, path) && it.code >= 500, path)
                            }
                            if (continuation.isActive) continuation.resume(value)
                        } catch (error: Exception) {
                            if (continuation.isActive) continuation.resumeWithException(
                                if (error is ApiFailure) error else ApiFailure(0, "Response could not be read safely.", consequential(method, path), path))
                        }
                    }
                }
            })
        }
    }
    override fun cancel() {
        val retiring = synchronized(this) { val old = client; client = phoneHttpClient(); old }
        // Conscrypt close can send TLS records. It must never run on Android's UI thread.
        // New requests use a separate client, so late cleanup cannot cancel a fresh unlock.
        cleanupNetwork {
            try { retiring.dispatcher.cancelAll() } finally { retiring.connectionPool.evictAll() }
        }
    }
}

class Api(private val transport: Transport, private val instruction: (String, Boolean) -> Unit = { _, _ -> }) {
    var token: String? = null
        private set
    fun authorize(value: String) { token = value }
    fun lock() { token = null; transport.cancel() }
    suspend fun get(path: String) = transport.request("GET", path, token, null)
    private suspend fun mutate(method: String, path: String, body: JSONObject?): JSONObject {
        val tracked = HttpsTransport.consequential(method, path)
        if (tracked) instruction(path, true)
        val result = try { transport.request(method, path, token, body) } catch (error: Exception) {
            if (tracked && error is ApiFailure && !error.uncertain) instruction(path, false)
            throw error // Cancellation and unknown outcomes retain the durable inspection marker.
        }
        if (tracked) instruction(path, false)
        return result
    }
    suspend fun post(path: String, body: JSONObject = JSONObject()) = mutate("POST", path, body)
    suspend fun delete(path: String) = mutate("DELETE", path, null)
    suspend fun pair(owner: String, label: String) = transport.request("POST", "/api/mobile/devices", owner, JSONObject().put("label", label))
    suspend fun unlock(credential: JSONObject) = transport.request("POST", "/api/mobile/session", null, credential)
}
