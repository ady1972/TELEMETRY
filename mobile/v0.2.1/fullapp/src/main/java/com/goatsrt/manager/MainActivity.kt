package com.goatsrt.manager

import android.app.Activity
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform

class MainActivity : Activity() {
    private lateinit var status: TextView
    private val defaultHandler = Thread.getDefaultUncaughtExceptionHandler()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        installCrashCapture()
        Diagnostics.mark(this, "safe_launcher_onCreate")
        showSafeLauncher()
    }

    private fun installCrashCapture() {
        Thread.setDefaultUncaughtExceptionHandler { thread, error ->
            Diagnostics.saveCrash(applicationContext, thread, error)
            defaultHandler?.uncaughtException(thread, error)
                ?: run { android.os.Process.killProcess(android.os.Process.myPid()) }
        }
    }

    private fun showSafeLauncher() {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(20), dp(20), dp(20))
            setBackgroundColor(Color.rgb(11, 16, 22))
        }

        root.addView(text("GOATS RT Manager", 24f, Color.WHITE, true))
        root.addView(text("Android V0.1.9.3 USB FULL + NATIVE MAP Z22", 15f, Color.rgb(0, 199, 140), true))
        root.addView(text(
            "Questa schermata non carica Compose, Python o USB all'avvio. Serve a isolare il crash senza far chiudere subito l'app.",
            14f, Color.LTGRAY, false
        ))

        status = text("Stato: pronto\nUltimo stage: ${Diagnostics.stage(this)}", 13f, Color.WHITE, false)
        status.setPadding(0, dp(14), 0, dp(14))
        root.addView(status)

        val crash = Diagnostics.readCrash(this)
        if (crash.isNotBlank()) {
            root.addView(text("CRASH PRECEDENTE RILEVATO", 15f, Color.rgb(227, 93, 106), true))
            val crashText = text(crash, 11f, Color.WHITE, false)
            crashText.setTextIsSelectable(true)
            root.addView(crashText)
        }

        root.addView(button("1 • TEST PYTHON") { testPython() })
        root.addView(button("2 • APRI MANAGER COMPLETO") { openManager() })
        root.addView(button("COPIA DIAGNOSTICA") { copyDiagnostics() })
        root.addView(button("AZZERA DIAGNOSTICA") {
            Diagnostics.clear(this)
            status.text = "Diagnostica azzerata."
        })

        val scroll = ScrollView(this).apply { addView(root) }
        setContentView(scroll)
    }

    private fun testPython() {
        Diagnostics.mark(this, "manual_python_test")
        status.text = "Test Python in corso..."
        try {
            if (!Python.isStarted()) {
                Diagnostics.mark(this, "manual_python_start")
                Python.start(AndroidPlatform(applicationContext))
            }
            Diagnostics.mark(this, "manual_python_bridge")
            val bridge = PythonBridge(this)
            val health = bridge.health().toString(2)
            Diagnostics.mark(this, "manual_python_ok")
            status.text = "PYTHON OK ✅\n$health"
        } catch (t: Throwable) {
            Diagnostics.saveCrash(this, Thread.currentThread(), t)
            status.text = "ERRORE PYTHON ❌\n${android.util.Log.getStackTraceString(t)}"
        }
    }

    private fun openManager() {
        Diagnostics.mark(this, "manager_launch_requested")
        status.text = "Avvio Manager completo..."
        startActivity(Intent(this, ManagerActivity::class.java))
    }

    private fun copyDiagnostics() {
        val report = buildString {
            appendLine("GOATS RT Manager V0.1.9.3 USB FULL + NATIVE MAP Z22")
            appendLine("Stage: ${Diagnostics.stage(this@MainActivity)}")
            appendLine()
            appendLine(Diagnostics.readCrash(this@MainActivity).ifBlank { "Nessun crash Java registrato." })
        }
        val cm = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        cm.setPrimaryClip(ClipData.newPlainText("GOATS diagnostics", report))
        status.text = "Diagnostica copiata negli appunti."
    }

    private fun button(label: String, action: () -> Unit): View {
        return Button(this).apply {
            text = label
            isAllCaps = false
            setOnClickListener { action() }
            val lp = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            )
            lp.topMargin = dp(10)
            layoutParams = lp
        }
    }

    private fun text(value: String, size: Float, color: Int, bold: Boolean): TextView {
        return TextView(this).apply {
            text = value
            textSize = size
            setTextColor(color)
            gravity = Gravity.START
            if (bold) setTypeface(typeface, android.graphics.Typeface.BOLD)
        }
    }

    private fun dp(v: Int): Int = (v * resources.displayMetrics.density).toInt()
}
