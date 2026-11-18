package com.goatsrt.manager

import android.content.Context
import java.io.File

object Diagnostics {
    private const val PREFS = "goats_diag"
    private const val KEY_STAGE = "last_stage"
    private const val KEY_TIME = "last_stage_time"

    fun mark(context: Context, stage: String) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY_STAGE, stage)
            .putLong(KEY_TIME, System.currentTimeMillis())
            .apply()
    }

    fun stage(context: Context): String {
        val p = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val s = p.getString(KEY_STAGE, "nessuno") ?: "nessuno"
        val t = p.getLong(KEY_TIME, 0L)
        return if (t > 0) "$s @ $t" else s
    }

    fun crashFile(context: Context): File = File(context.filesDir, "last_crash.txt")

    fun saveCrash(context: Context, thread: Thread, error: Throwable) {
        try {
            crashFile(context).writeText(
                buildString {
                    appendLine("THREAD: ${thread.name}")
                    appendLine("STAGE: ${stage(context)}")
                    appendLine("ERROR: ${error.javaClass.name}: ${error.message}")
                    appendLine()
                    appendLine(android.util.Log.getStackTraceString(error))
                }
            )
        } catch (_: Throwable) { }
    }

    fun readCrash(context: Context): String = try {
        crashFile(context).takeIf { it.exists() }?.readText().orEmpty()
    } catch (_: Throwable) { "" }

    fun clear(context: Context) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().clear().apply()
        try { crashFile(context).delete() } catch (_: Throwable) { }
    }
}
