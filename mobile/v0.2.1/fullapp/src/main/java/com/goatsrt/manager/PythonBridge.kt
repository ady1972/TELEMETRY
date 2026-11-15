package com.goatsrt.manager

import android.content.Context
import com.chaquo.python.PyObject
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import org.json.JSONArray
import org.json.JSONObject

class PythonBridge(context: Context) {
    private val module: PyObject

    init {
        if (!Python.isStarted()) {
            Python.start(AndroidPlatform(context.applicationContext))
        }
        val py = Python.getInstance()
        module = try {
            py.getModule("android_bridge")
        } catch (t: Throwable) {
            throw IllegalStateException("Avvio Python fallito durante import android_bridge: ${t.message}", t)
        }
        try {
            module.callAttr("init_app", context.filesDir.absolutePath)
        } catch (t: Throwable) {
            throw IllegalStateException("Avvio Python fallito durante init_app/database: ${t.message}", t)
        }
    }

    private fun callJson(name: String, vararg args: Any?): JSONObject =
        JSONObject(module.callAttr(name, *args).toString())

    private fun callArray(name: String, vararg args: Any?): JSONArray =
        JSONArray(module.callAttr(name, *args).toString())

    fun health(): JSONObject = callJson("health_json")
    fun dashboard(): JSONObject = callJson("dashboard_json")
    fun sessions(search: String = ""): JSONArray = callArray("sessions_json", search)
    fun importFile(path: String): JSONObject = callJson("import_file", path)
    fun deleteSession(id: Int): JSONObject = callJson("delete_session", id)
    fun setSessionNotes(id: Int, notes: String): JSONObject = callJson("set_session_notes", id, notes)
    fun analysis(id: Int, lap: Int = 0): JSONObject = callJson("analysis_json", id, lap)
    fun compare(ids: List<Int>): JSONArray = callArray("compare_json", JSONArray(ids).toString())

    fun tracks(): JSONArray = callArray("tracks_json")
    fun importTrack(path: String): JSONObject = callJson("import_track_file", path)
    fun track(id: String): JSONObject = callJson("track_json", id)
    fun saveTrack(payloadJson: String): JSONObject = callJson("save_track_json", payloadJson)
    fun deleteTrack(id: String): JSONObject = callJson("delete_track", id)
    fun prepareMergedCatalog(existingBase64: String, selectedIds: Set<String>): JSONObject =
        callJson("prepare_merged_catalog", existingBase64, JSONArray(selectedIds.toList()).toString())
    fun saveCatalogFromLaptimer(payloadBase64: String): JSONObject =
        callJson("save_catalog_from_laptimer", payloadBase64)

}
