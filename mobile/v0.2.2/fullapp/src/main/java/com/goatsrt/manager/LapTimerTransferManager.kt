package com.goatsrt.manager

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

/**
 * Trasferimento remoto GOATS RT.
 *
 * Wi-Fi: l'app prova un piccolo contratto REST pensato per il firmware hotspot:
 *   GET /api/sessions            -> array oppure {"sessions":[...]}
 *   GET /api/sessions/{id}/download -> file GRT/GSA/CSV/JSON
 * In alternativa accetta /sessions e l'eventuale campo download_url/url nei metadati.
 *
 */

data class RemoteSessionUi(
    val id: String,
    val name: String,
    val track: String,
    val date: String,
    val time: String,
    val format: String,
    val sizeBytes: Long,
    val downloadUrl: String
)

object LapTimerWifiTransport {
    private fun normalizedBase(baseUrl: String): String {
        val raw = baseUrl.trim().ifBlank { "http://192.168.4.1" }
        val withScheme = if (raw.startsWith("http://") || raw.startsWith("https://")) raw else "http://$raw"
        return withScheme.trimEnd('/')
    }

    private fun getBytes(url: String, timeoutMs: Int = 7000): ByteArray {
        val c = URL(url).openConnection() as HttpURLConnection
        c.requestMethod = "GET"
        c.connectTimeout = timeoutMs
        c.readTimeout = timeoutMs
        c.instanceFollowRedirects = true
        c.setRequestProperty("Accept", "application/json, application/octet-stream, */*")
        c.setRequestProperty("User-Agent", "GOATS-RT-Manager-Android/0.2.2")
        return try {
            val code = c.responseCode
            if (code !in 200..299) throw IllegalStateException("HTTP $code da $url")
            c.inputStream.use { it.readBytes() }
        } finally {
            c.disconnect()
        }
    }

    private fun parseSessionArray(text: String): JSONArray {
        val t = text.trim()
        if (t.startsWith("[")) return JSONArray(t)
        val obj = JSONObject(t)
        return obj.optJSONArray("sessions") ?: obj.optJSONArray("items")
            ?: throw IllegalArgumentException("Risposta sessioni non riconosciuta")
    }

    fun listSessions(baseUrl: String): List<RemoteSessionUi> {
        val base = normalizedBase(baseUrl)
        val candidates = listOf("$base/api/sessions", "$base/sessions", "$base/goats/sessions")
        var lastError: Throwable? = null
        for (url in candidates) {
            try {
                val arr = parseSessionArray(getBytes(url).toString(Charsets.UTF_8))
                return buildList {
                    for (i in 0 until arr.length()) {
                        val o = arr.getJSONObject(i)
                        val id = o.optString("id", o.optString("session_id", i.toString()))
                        val format = o.optString("format", o.optString("type", "grt"))
                        val track = o.optString("track", o.optString("track_name", "Circuito"))
                        val date = o.optString("date")
                        val time = o.optString("time")
                        val name = o.optString("name").ifBlank {
                            listOf(track, date, time).filter { it.isNotBlank() }.joinToString(" • ").ifBlank { "Sessione $id" }
                        }
                        add(
                            RemoteSessionUi(
                                id = id,
                                name = name,
                                track = track,
                                date = date,
                                time = time,
                                format = format,
                                sizeBytes = o.optLong("size", o.optLong("bytes", 0L)),
                                downloadUrl = o.optString("download_url", o.optString("url"))
                            )
                        )
                    }
                }
            } catch (t: Throwable) {
                lastError = t
            }
        }
        throw IllegalStateException(lastError?.message ?: "Lap timer non raggiungibile")
    }

    fun downloadSession(context: Context, baseUrl: String, item: RemoteSessionUi): File {
        val base = normalizedBase(baseUrl)
        val encoded = URLEncoder.encode(item.id, "UTF-8")
        val candidates = buildList {
            if (item.downloadUrl.isNotBlank()) {
                add(if (item.downloadUrl.startsWith("http://") || item.downloadUrl.startsWith("https://")) item.downloadUrl else "$base/${item.downloadUrl.trimStart('/')}")
            }
            add("$base/api/sessions/$encoded/download")
            add("$base/sessions/$encoded")
            add("$base/goats/sessions/$encoded")
        }.distinct()
        var lastError: Throwable? = null
        for (url in candidates) {
            try {
                val bytes = getBytes(url, 20000)
                if (bytes.isEmpty()) throw IllegalStateException("File vuoto")
                val ext = item.format.lowercase().replace(Regex("[^a-z0-9]"), "").ifBlank { "grt" }.take(5)
                val stem = listOf(item.date, item.time, item.track, item.id)
                    .filter { it.isNotBlank() }
                    .joinToString("_")
                    .replace(Regex("[^A-Za-z0-9_-]"), "_")
                    .replace(Regex("_+"), "_")
                    .trim('_')
                    .ifBlank { item.id.replace(Regex("[^A-Za-z0-9_-]"), "_") }
                val out = File(context.cacheDir, "GOATS_SESSION_${stem.take(120)}.$ext")
                out.writeBytes(bytes)
                return out
            } catch (t: Throwable) {
                lastError = t
            }
        }
        throw IllegalStateException(lastError?.message ?: "Download sessione fallito")
    }
}
