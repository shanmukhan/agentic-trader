package com.shanmukhan.agentictrader

import android.content.Context
import org.json.JSONObject

/** Separate offline package: no Internet permission and no production network fallback. */
class DemoTransport(context: Context) : Transport {
    private val fixtures = JSONObject(context.assets.open("demo.json").bufferedReader().use { it.readText() })
    override suspend fun request(method: String, path: String, token: String?, body: JSONObject?): JSONObject {
        check(BuildConfig.DEMO) { "Offline fixtures cannot authorize production access." }
        if (method != "GET") throw ApiFailure(409, "Offline demo only. No action is sent or saved.")
        val value = fixtures.optJSONObject(path.substringBefore('?'))
            ?: return JSONObject().put("message", "No records in this invented offline demonstration.")
        return JSONObject(value.toString())
    }
    override fun cancel() = Unit
}
