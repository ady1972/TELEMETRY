package com.goatsrt.manager

import android.content.Context
import android.net.Uri
import android.os.Bundle
import android.provider.OpenableColumns
import android.util.Log
import android.graphics.BitmapFactory
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.compose.setContent
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import org.json.JSONArray
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.floor
import kotlin.math.ln
import kotlin.math.max
import kotlin.math.min
import kotlin.math.pow
import kotlin.math.tan
import kotlin.math.atan
import kotlin.math.sinh

class ManagerActivity : ComponentActivity() {
    private var usb: UsbSerialManager? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        Diagnostics.mark(this, "manager_onCreate")

        try {
            // Avvio esplicito di Chaquopy: in questo modo qualsiasi errore di bootstrap
            // viene mostrato sullo schermo invece di chiudere subito l'app.
            Diagnostics.mark(this, "python_start")
            if (!Python.isStarted()) {
                Python.start(AndroidPlatform(applicationContext))
            }
            Diagnostics.mark(this, "python_started")

            Diagnostics.mark(this, "python_bridge")
            val bridge = PythonBridge(this)
            bridge.health()
            Diagnostics.mark(this, "python_health_ok")
            Diagnostics.mark(this, "usb_init")
            val usbManager = UsbSerialManager(this)
            Diagnostics.mark(this, "usb_ok")
            usb = usbManager

            Diagnostics.mark(this, "compose_setContent")
            setContent {
                GoatsTheme {
                    Diagnostics.mark(this@ManagerActivity, "compose_render")
                    GoatsApp(this, bridge, usbManager)
                }
            }
        } catch (t: Throwable) {
            Log.e("GOATS_STARTUP", "Errore durante l'avvio di GOATS RT Manager", t)
            val details = Log.getStackTraceString(t)
            setContent {
                GoatsTheme {
                    StartupErrorScreen(details)
                }
            }
        }
    }

    override fun onDestroy() {
        usb?.close()
        super.onDestroy()
    }
}

@Composable
private fun StartupErrorScreen(details: String) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Bg)
            .verticalScroll(rememberScrollState())
            .padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text("GOATS RT Manager", fontSize = 24.sp, fontWeight = FontWeight.Bold, color = Color.White)
        Text("Errore di avvio", fontSize = 20.sp, fontWeight = FontWeight.Bold, color = Danger)
        Text(
            "La V0.1.1 ha intercettato l'errore invece di chiudere l'app. Fai uno screenshot di questa schermata e invialo per la correzione definitiva.",
            color = Muted
        )
        SelectionContainer {
            Text(details, color = Color.White, fontSize = 12.sp)
        }
    }
}

private val Bg = Color(0xFF0B1016)
private val CardBg = Color(0xFF141C25)
private val Accent = Color(0xFF00C78C)
private val Accent2 = Color(0xFF42A5F5)
private val Muted = Color(0xFF94A3B8)
private val Danger = Color(0xFFE35D6A)

@Composable
private fun GoatsTheme(content: @Composable () -> Unit) {
    val scheme = darkColorScheme(
        primary = Accent,
        secondary = Accent2,
        background = Bg,
        surface = CardBg,
        onPrimary = Color.Black,
        onBackground = Color.White,
        onSurface = Color.White,
    )
    MaterialTheme(colorScheme = scheme, typography = Typography(), content = content)
}

private enum class Page(val label: String, val short: String) {
    Dashboard("Dashboard", "Home"), Sessions("Sessioni", "Sessioni"), Analysis("Analisi", "Analisi"),
    Tracks("Circuiti", "Circuiti"), Info("Informazioni", "Info")
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun GoatsApp(context: Context, bridge: PythonBridge, usb: UsbSerialManager) {
    var page by remember { mutableStateOf(Page.Dashboard) }
    var selectedSessionId by remember { mutableIntStateOf(0) }
    var refreshToken by remember { mutableIntStateOf(0) }
    val snackbar = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()

    Scaffold(
        containerColor = Bg,
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("GOATS RT Manager", fontWeight = FontWeight.Bold)
                        Text("Android 0.2.2 • editor circuiti • import Wi-Fi • Cloud Sync • core V5.4.13.8", fontSize = 11.sp, color = Muted)
                    }
                },
                actions = {
                    Text(
                        if (usb.connected) "USB ●" else "USB ○",
                        color = if (usb.connected) Accent else Muted,
                        fontSize = 12.sp,
                        modifier = Modifier.padding(end = 12.dp)
                    )
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = Bg)
            )
        },
        bottomBar = {
            NavigationBar(containerColor = CardBg) {
                Page.entries.forEach { p ->
                    NavigationBarItem(
                        selected = page == p,
                        onClick = { page = p },
                        icon = { Text(if (page == p) "●" else "○", fontSize = 11.sp) },
                        label = { Text(p.short, fontSize = 9.sp, maxLines = 1) }
                    )
                }
            }
        },
        snackbarHost = { SnackbarHost(snackbar) }
    ) { pad ->
        Box(Modifier.padding(pad).fillMaxSize()) {
            when (page) {
                Page.Dashboard -> DashboardScreen(bridge, refreshToken) { page = it }
                Page.Sessions -> SessionsScreen(context, bridge, refreshToken,
                    onRefresh = { refreshToken++ },
                    onOpen = { id -> selectedSessionId = id; page = Page.Analysis },
                    showMessage = { msg -> scope.launch { snackbar.showSnackbar(msg) } }
                )
                Page.Analysis -> AnalysisScreen(bridge, selectedSessionId,
                    onSelectSession = { selectedSessionId = it }, refreshToken = refreshToken)
                Page.Tracks -> TracksScreen(context, bridge, usb, refreshToken,
                    onRefresh = { refreshToken++ },
                    showMessage = { msg -> scope.launch { snackbar.showSnackbar(msg) } })
                Page.Info -> InfoScreen(usb)
            }
        }
    }
}

@Composable
private fun DashboardScreen(bridge: PythonBridge, refreshToken: Int, navigate: (Page) -> Unit) {
    var data by remember { mutableStateOf(DashboardUi()) }
    LaunchedEffect(refreshToken) {
        data = withContext(Dispatchers.IO) { bridge.dashboard().toDashboardUi() }
    }
    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item { PageHeader("Dashboard", "Archivio storico e telemetria ad alta risoluzione") }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                MetricCard("Sessioni", data.sessions.toString(), Modifier.weight(1f))
                MetricCard("Punti GPS", data.points.toString(), Modifier.weight(1f))
            }
        }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                MetricCard("Ore registrate", "${data.hours}", Modifier.weight(1f))
                MetricCard("Best lap", data.best, Modifier.weight(1f))
            }
        }
        item { ActionCard("Sessioni", "Importa CSV, GRT8, GSA2/GSA3 e JSON dal telefono o da USB.", "APRI SESSIONI") { navigate(Page.Sessions) } }
        item { ActionCard("Analisi", "Traccia offline, grafico velocità e selezione giro.", "APRI ANALISI") { navigate(Page.Analysis) } }
        item { ActionCard("Circuiti / USB", "Importa circuiti e sincronizzali col laptimer senza cancellare quelli esistenti.", "GESTISCI CIRCUITI") { navigate(Page.Tracks) } }
    }
}

@Composable
private fun PageHeader(title: String, sub: String) {
    Column(Modifier.fillMaxWidth()) {
        Text(title, fontSize = 26.sp, fontWeight = FontWeight.Bold)
        Text(sub, color = Muted, fontSize = 13.sp)
    }
}

@Composable
private fun MetricCard(label: String, value: String, modifier: Modifier = Modifier) {
    Card(modifier, colors = CardDefaults.cardColors(containerColor = CardBg)) {
        Column(Modifier.padding(16.dp)) {
            Text(label, color = Muted, fontSize = 12.sp)
            Text(value, fontWeight = FontWeight.Bold, fontSize = 22.sp)
        }
    }
}

@Composable
private fun ActionCard(title: String, desc: String, button: String, action: () -> Unit) {
    Card(colors = CardDefaults.cardColors(containerColor = CardBg)) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(title, fontWeight = FontWeight.Bold, fontSize = 18.sp)
            Text(desc, color = Muted)
            Button(onClick = action) { Text(button) }
        }
    }
}

@Composable
private fun SessionsScreen(
    context: Context, bridge: PythonBridge, refreshToken: Int,
    onRefresh: () -> Unit, onOpen: (Int) -> Unit, showMessage: (String) -> Unit
) {
    var search by remember { mutableStateOf("") }
    var sessions by remember { mutableStateOf(emptyList<SessionUi>()) }
    var busy by remember { mutableStateOf(false) }
    var showRemoteImport by remember { mutableStateOf(false) }
    var showCloudSync by remember { mutableStateOf(false) }
    var cloudRefresh by remember { mutableIntStateOf(0) }
    val scope = rememberCoroutineScope()

    fun reload() {
        scope.launch {
            sessions = withContext(Dispatchers.IO) { bridge.sessions(search).toSessions() }
        }
    }
    LaunchedEffect(search, refreshToken) { reload() }

    val picker = rememberLauncherForActivityResult(ActivityResultContracts.OpenMultipleDocuments()) { uris ->
        if (uris.isEmpty()) return@rememberLauncherForActivityResult
        scope.launch {
            busy = true
            var ok = 0
            val errors = mutableListOf<String>()
            for (uri in uris) {
                try {
                    val archived = withContext(Dispatchers.IO) { SessionArchive.storeUri(context, uri) }
                    val result = withContext(Dispatchers.IO) { bridge.importFile(archived.absolutePath) }
                    ok += result.optInt("count", 0)
                } catch (e: Exception) {
                    errors += (e.cause?.message ?: e.message ?: "errore")
                }
            }
            if (ok > 0) syncAfterLocalChange(context, bridge)?.let { errors += it }
            busy = false
            onRefresh()
            showMessage("Importate $ok sessioni" + if (errors.isNotEmpty()) " • ${errors.first()}" else "")
        }
    }

    val cloudFolderPicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocumentTree()) { uri ->
        uri ?: return@rememberLauncherForActivityResult
        try {
            CloudSessionSync.setFolder(context, uri)
            cloudRefresh++
            showMessage("Cartella cloud selezionata: ${CloudSessionSync.folderLabel(context)}")
        } catch (t: Throwable) {
            showMessage(t.message ?: "Impossibile usare la cartella cloud")
        }
    }

    if (showRemoteImport) {
        LapTimerImportDialog(
            context = context,
            bridge = bridge,
            onDismiss = { showRemoteImport = false },
            onImported = { count ->
                showRemoteImport = false
                onRefresh()
                showMessage("Importate $count sessioni dal lap timer")
            },
            showMessage = showMessage
        )
    }

    if (showCloudSync) {
        CloudSyncDialog(
            context = context,
            bridge = bridge,
            refreshToken = cloudRefresh,
            onChooseFolder = { cloudFolderPicker.launch(null) },
            onDismiss = { showCloudSync = false },
            onSynced = { result ->
                onRefresh()
                showMessage("${result.imported} sessioni • ${result.tracksImported} circuiti • ${result.conflicts} conflitti • ${result.errors} errori")
            }
        )
    }

    Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        PageHeader("Sessioni", "Archivio locale con import Wi-Fi e sincronizzazione cloud")
        OutlinedTextField(
            value = search, onValueChange = { search = it },
            label = { Text("Cerca circuito, data o note") }, modifier = Modifier.fillMaxWidth(), singleLine = true
        )
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.horizontalScroll(rememberScrollState())) {
            Button(onClick = { picker.launch(arrayOf("text/csv", "application/json", "application/octet-stream", "*/*")) }, enabled = !busy) {
                Text(if (busy) "IMPORTAZIONE..." else "IMPORTA FILE")
            }
            Button(onClick = { showRemoteImport = true }, enabled = !busy) { Text("DAL LAP TIMER") }
            OutlinedButton(onClick = { showCloudSync = true }, enabled = !busy) {
                Text(if (CloudSessionSync.folderUri(context) != null) "SYNC WINDOWS ✓" else "SYNC WINDOWS")
            }
            OutlinedButton(onClick = { reload() }) { Text("AGGIORNA") }
        }
        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxSize()) {
            items(sessions, key = { it.id }) { s ->
                Card(
                    colors = CardDefaults.cardColors(containerColor = CardBg),
                    modifier = Modifier.fillMaxWidth().clickable { onOpen(s.id) }
                ) {
                    Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text(s.track, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.weight(1f))
                            Text(s.best, color = Accent, fontWeight = FontWeight.Bold)
                        }
                        Text("${s.date} ${s.time} • ${s.laps} giri • ${s.points} punti • ${s.format}", color = Muted, fontSize = 12.sp)
                        Text("Vmax ${s.vmax} km/h • Vmedia ${s.vavg} km/h • ${s.duration}", fontSize = 12.sp)
                        if (s.notes.isNotBlank()) Text(s.notes, color = Muted, fontSize = 12.sp, maxLines = 2)
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            TextButton(onClick = { onOpen(s.id) }) { Text("ANALIZZA") }
                            TextButton(onClick = {
                                scope.launch {
                                    withContext(Dispatchers.IO) { bridge.deleteSession(s.id) }
                                    onRefresh(); showMessage("Sessione eliminata")
                                }
                            }) { Text("ELIMINA", color = Danger) }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun LapTimerImportDialog(
    context: Context,
    bridge: PythonBridge,
    onDismiss: () -> Unit,
    onImported: (Int) -> Unit,
    showMessage: (String) -> Unit
) {
    val prefs = remember { context.getSharedPreferences("goats_remote", Context.MODE_PRIVATE) }
    var baseUrl by remember { mutableStateOf(prefs.getString("wifi_base_url", "http://192.168.4.1") ?: "http://192.168.4.1") }
    var sessions by remember { mutableStateOf(emptyList<RemoteSessionUi>()) }
    val selected = remember { mutableStateMapOf<String, Boolean>() }
    var busy by remember { mutableStateOf(false) }
    var status by remember { mutableStateOf("Collegati all'hotspot Wi-Fi del lap timer e premi CERCA SESSIONI.") }
    val scope = rememberCoroutineScope()

    Dialog(onDismissRequest = { if (!busy) onDismiss() }, properties = DialogProperties(usePlatformDefaultWidth = false)) {
        Card(
            modifier = Modifier.fillMaxWidth(0.96f).fillMaxHeight(0.92f),
            colors = CardDefaults.cardColors(containerColor = Bg)
        ) {
            Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                    Column {
                        Text("Importa dal Lap Timer", fontSize = 22.sp, fontWeight = FontWeight.Bold)
                        Text("Importazione Wi-Fi dal laptimer", color = Muted, fontSize = 12.sp)
                    }
                    TextButton(onClick = onDismiss, enabled = !busy) { Text("CHIUDI") }
                }
                    OutlinedTextField(
                        value = baseUrl,
                        onValueChange = { baseUrl = it },
                        label = { Text("Indirizzo lap timer") },
                        supportingText = { Text("Default hotspot: http://192.168.4.1") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.horizontalScroll(rememberScrollState())) {
                        Button(enabled = !busy, onClick = {
                            scope.launch {
                                busy = true
                                status = "Ricerca sessioni..."
                                try {
                                    prefs.edit().putString("wifi_base_url", baseUrl).apply()
                                    sessions = withContext(Dispatchers.IO) { LapTimerWifiTransport.listSessions(baseUrl) }
                                    selected.clear()
                                    sessions.forEach { selected[it.id] = true }
                                    status = "Trovate ${sessions.size} sessioni"
                                } catch (t: Throwable) {
                                    status = t.message ?: "Lap timer non raggiungibile"
                                }
                                busy = false
                            }
                        }) { Text("CERCA SESSIONI") }
                        OutlinedButton(enabled = sessions.isNotEmpty() && !busy, onClick = {
                            sessions.forEach { selected[it.id] = true }
                        }) { Text("TUTTE") }
                        OutlinedButton(enabled = sessions.isNotEmpty() && !busy, onClick = { selected.clear() }) { Text("NESSUNA") }
                    }
                    Text(status, color = if (status.startsWith("Trovate")) Accent else Muted, fontSize = 12.sp)
                    if (busy) LinearProgressIndicator(Modifier.fillMaxWidth())
                    LazyColumn(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        items(sessions, key = { it.id }) { s ->
                            Card(colors = CardDefaults.cardColors(containerColor = CardBg)) {
                                Row(Modifier.fillMaxWidth().padding(10.dp), verticalAlignment = Alignment.CenterVertically) {
                                    Checkbox(checked = selected[s.id] == true, onCheckedChange = { selected[s.id] = it })
                                    Column(Modifier.weight(1f)) {
                                        Text(s.name, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                                        Text("${s.format.uppercase()}${if (s.sizeBytes > 0) " • ${s.sizeBytes / 1024} KB" else ""}", color = Muted, fontSize = 11.sp)
                                    }
                                }
                            }
                        }
                    }
                    Button(
                        enabled = !busy && selected.any { it.value },
                        modifier = Modifier.fillMaxWidth(),
                        onClick = {
                            scope.launch {
                                busy = true
                                var imported = 0
                                var failed = 0
                                val chosen = sessions.filter { selected[it.id] == true }
                                chosen.forEachIndexed { i, item ->
                                    status = "Download ${i + 1}/${chosen.size}: ${item.name}"
                                    try {
                                        val file = withContext(Dispatchers.IO) { LapTimerWifiTransport.downloadSession(context, baseUrl, item) }
                                        val archived = withContext(Dispatchers.IO) { SessionArchive.storeFile(context, file, file.name) }
                                        val result = withContext(Dispatchers.IO) { bridge.importFile(archived.absolutePath) }
                                        imported += result.optInt("count", 0)
                                    } catch (_: Throwable) {
                                        failed++
                                    }
                                }
                                val cloudWarning = if (imported > 0) syncAfterLocalChange(context, bridge) else null
                                busy = false
                                if (imported > 0) onImported(imported)
                                else showMessage("Nessuna sessione importata${if (failed > 0) " • $failed errori" else ""}")
                                if (cloudWarning != null) showMessage(cloudWarning)
                            }
                        }
                    ) { Text("SCARICA E IMPORTA") }

            }
        }
    }
}

private suspend fun syncAfterLocalChange(context: Context, bridge: PythonBridge): String? = withContext(Dispatchers.IO) {
    try {
        val result = CloudSessionSync.syncIfEnabled(context, bridge)
        when {
            result == null -> null
            result.errors > 0 -> "Dati salvati offline; sincronizzazione con ${result.errors} errori"
            result.conflicts > 0 -> "Conservate ${result.conflicts} varianti di conflitto dei circuiti"
            else -> null
        }
    } catch (t: Exception) {
        "Dati salvati offline; sincronizzazione non completata: ${t.message}"
    }
}

@Composable
private fun CloudSyncDialog(
    context: Context,
    bridge: PythonBridge,
    refreshToken: Int,
    onChooseFolder: () -> Unit,
    onDismiss: () -> Unit,
    onSynced: (CloudSyncResult) -> Unit
) {
    var folderLabel by remember(refreshToken) { mutableStateOf(CloudSessionSync.folderLabel(context)) }
    var autoSync by remember(refreshToken) { mutableStateOf(CloudSessionSync.autoSync(context)) }
    var busy by remember { mutableStateOf(false) }
    var status by remember { mutableStateOf("Sessioni originali e circuiti vengono scambiati con il Manager Windows. Il database e le note rimangono locali.") }
    val scope = rememberCoroutineScope()

    Dialog(onDismissRequest = { if (!busy) onDismiss() }) {
        Card(colors = CardDefaults.cardColors(containerColor = Bg), modifier = Modifier.fillMaxWidth()) {
            Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text("Sincronizza con Windows", fontSize = 22.sp, fontWeight = FontWeight.Bold)
                Text(
                    "Scegli la stessa cartella cloud configurata nel Manager Windows in Importa Sessioni → Cloud Sync. Sul telefono il provider deve consentire la selezione di una cartella.",
                    color = Muted,
                    fontSize = 12.sp
                )
                Card(colors = CardDefaults.cardColors(containerColor = CardBg), modifier = Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text("Cartella selezionata", color = Muted, fontSize = 11.sp)
                        Text(folderLabel, fontWeight = FontWeight.Bold, maxLines = 2, overflow = TextOverflow.Ellipsis)
                    }
                }
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Switch(
                        checked = autoSync,
                        onCheckedChange = {
                            autoSync = it
                            CloudSessionSync.setAutoSync(context, it)
                        },
                        enabled = CloudSessionSync.folderUri(context) != null && !busy
                    )
                    Spacer(Modifier.width(10.dp))
                    Column {
                        Text("Sincronizzazione automatica", fontWeight = FontWeight.Bold)
                        Text("Dopo importazioni e salvataggi dei circuiti sincronizza sessioni e circuiti.", color = Muted, fontSize = 11.sp)
                    }
                }
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.horizontalScroll(rememberScrollState())) {
                    Button(onClick = onChooseFolder, enabled = !busy) { Text("CARTELLA CONDIVISA") }
                    OutlinedButton(
                        enabled = CloudSessionSync.folderUri(context) != null && !busy,
                        onClick = {
                            scope.launch {
                                busy = true
                                status = "Sincronizzazione in corso..."
                                try {
                                    val result = withContext(Dispatchers.IO) { CloudSessionSync.sync(context, bridge) }
                                    status = "Completata: ${result.imported} sessioni • ${result.tracksImported} circuiti • ${result.uploaded} file pubblicati • ${result.conflicts} conflitti conservati • ${result.errors} errori" + result.errorMessages.firstOrNull()?.let { "\n$it" }.orEmpty()
                                    onSynced(result)
                                } catch (t: Throwable) {
                                    status = t.message ?: "Errore Cloud Sync"
                                }
                                folderLabel = CloudSessionSync.folderLabel(context)
                                busy = false
                            }
                        }
                    ) { Text("SINCRONIZZA ORA") }
                }
                if (busy) LinearProgressIndicator(Modifier.fillMaxWidth())
                Text(status, color = if (status.startsWith("Completata")) Accent else Muted, fontSize = 12.sp)
                Text(
                    "Usa una cartella dedicata, ad esempio GOATS_RT_CLOUD, sincronizzata su PC e telefono. Alcuni provider Android richiedono un client che esponga cartelle al selettore di sistema. Le cancellazioni non si propagano; le varianti dei circuiti modificati contemporaneamente sono conservate.",
                    color = Muted,
                    fontSize = 11.sp
                )
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                    TextButton(onClick = onDismiss, enabled = !busy) { Text("CHIUDI") }
                }
            }
        }
    }
}

@Composable
private fun AnalysisScreen(bridge: PythonBridge, selectedId: Int, onSelectSession: (Int) -> Unit, refreshToken: Int) {
    var sessions by remember { mutableStateOf(emptyList<SessionUi>()) }
    var selectedLap by remember(selectedId) { mutableIntStateOf(0) }
    var analysis by remember { mutableStateOf(AnalysisUi()) }
    var loading by remember { mutableStateOf(false) }

    LaunchedEffect(refreshToken) {
        sessions = withContext(Dispatchers.IO) { bridge.sessions("").toSessions() }
        if (selectedId == 0 && sessions.isNotEmpty()) onSelectSession(sessions.first().id)
    }
    LaunchedEffect(selectedId, selectedLap, refreshToken) {
        if (selectedId > 0) {
            loading = true
            analysis = withContext(Dispatchers.IO) { bridge.analysis(selectedId, selectedLap).toAnalysisUi() }
            loading = false
        }
    }

    LazyColumn(
        Modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item { PageHeader("Analisi", "Traiettorie multi-giro, mappa satellitare, zoom/pan e grafico velocità") }
        item {
            if (sessions.isEmpty()) {
                Text("Nessuna sessione importata", color = Muted)
            } else {
                Text("Sessione", color = Muted, fontSize = 12.sp)
                Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    sessions.take(20).forEach { s ->
                        FilterChip(selected = s.id == selectedId, onClick = { selectedLap = 0; onSelectSession(s.id) }, label = { Text("${s.track} • ${s.date}") })
                    }
                }
            }
        }
        if (loading) item { LinearProgressIndicator(Modifier.fillMaxWidth()) }
        if (analysis.ok) {
            item {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                    MetricCard("Best", analysis.best, Modifier.weight(1f))
                    MetricCard("Vmax", "${analysis.vmax}", Modifier.weight(1f))
                    MetricCard("Vmedia", "${analysis.vavg}", Modifier.weight(1f))
                }
            }
            item {
                Text("Giro visualizzato", color = Muted, fontSize = 12.sp)
                Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    FilterChip(selected = selectedLap == 0, onClick = { selectedLap = 0 }, label = { Text("TRACCIA") })
                    analysis.laps.forEach { l ->
                        FilterChip(selected = selectedLap == l.lap, onClick = { selectedLap = l.lap }, label = { Text("G${l.lap} ${l.time}") })
                    }
                }
            }
            item {
                var mapMode by remember(selectedId, selectedLap) { mutableStateOf("satellite") }
                Card(colors = CardDefaults.cardColors(containerColor = CardBg)) {
                    Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Column {
                                Text("Traiettoria • ${analysis.points.size} punti GPS", fontWeight = FontWeight.Bold)
                                Text(
                                    if (mapMode == "satellite") "Satellite nativo • pinch per zoom • trascina per spostare"
                                    else "Vista offline • pinch per zoom • trascina per spostare",
                                    color = Muted,
                                    fontSize = 11.sp
                                )
                            }
                            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                FilterChip(
                                    selected = mapMode == "satellite",
                                    onClick = { mapMode = "satellite" },
                                    label = { Text("SAT") }
                                )
                                FilterChip(
                                    selected = mapMode == "offline",
                                    onClick = { mapMode = "offline" },
                                    label = { Text("OFFLINE") }
                                )
                            }
                        }
                        if (mapMode == "satellite") {
                            SatelliteTrackMap(analysis.points, Modifier.fillMaxWidth().height(360.dp))
                        } else {
                            TrackCanvas(analysis.points, Modifier.fillMaxWidth().height(360.dp))
                        }
                    }
                }
            }
            item {
                Card(colors = CardDefaults.cardColors(containerColor = CardBg)) {
                    Column(Modifier.padding(12.dp)) {
                        Text("Velocità", fontWeight = FontWeight.Bold)
                        SpeedChart(analysis.points, Modifier.fillMaxWidth().height(220.dp))
                    }
                }
            }
            item {
                Card(colors = CardDefaults.cardColors(containerColor = CardBg)) {
                    Column(Modifier.padding(12.dp)) {
                        Text("Tempi giro", fontWeight = FontWeight.Bold)
                        analysis.laps.forEach { l ->
                            Row(Modifier.fillMaxWidth().padding(vertical = 5.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                                Text("Giro ${l.lap}")
                                Text(l.time, color = if (l.time == analysis.best) Accent else Color.White, fontWeight = FontWeight.SemiBold)
                                Text("${l.vmax} km/h", color = Muted)
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun TrackCanvas(points: List<TrackPoint>, modifier: Modifier = Modifier) {
    val valid = remember(points) {
        points.filter {
            it.lat.isFinite() && it.lon.isFinite() &&
                it.lat in -90.0..90.0 && it.lon in -180.0..180.0 &&
                !(it.lat == 0.0 && it.lon == 0.0)
        }
    }
    if (valid.size < 2) {
        Box(modifier, contentAlignment = Alignment.Center) {
            Text("Nessuna traccia GPS valida (${points.size} punti)", color = Muted)
        }
        return
    }

    var zoom by remember(points) { mutableFloatStateOf(1f) }
    var pan by remember(points) { mutableStateOf(Offset.Zero) }
    val groups = remember(valid) { valid.groupBy { it.lap }.toList().sortedBy { if (it.first <= 0) Int.MAX_VALUE else it.first } }
    val palette = listOf(
        Color(0xFF42A5F5), Color(0xFF00C78C), Color(0xFFFFB74D), Color(0xFFEF5350),
        Color(0xFFAB47BC), Color(0xFF26C6DA), Color(0xFFD4E157), Color(0xFFEC407A),
        Color(0xFF7E57C2), Color(0xFF66BB6A), Color(0xFFFFA726), Color(0xFF29B6F6)
    )

    Box(modifier.background(Color(0xFF0E151D), RoundedCornerShape(8.dp))) {
        Canvas(
            Modifier
                .fillMaxSize()
                .pointerInput(points) {
                    detectTransformGestures { _, panChange, zoomChange, _ ->
                        zoom = (zoom * zoomChange).coerceIn(1f, 80f)
                        pan += panChange
                    }
                }
        ) {
            val avgLat = valid.map { it.lat }.average()
            val scaleLon = cos(Math.toRadians(avgLat)).coerceAtLeast(0.2)
            val xs = valid.map { it.lon * scaleLon }
            val ys = valid.map { it.lat }
            val minX = xs.minOrNull() ?: 0.0
            val maxX = xs.maxOrNull() ?: 1.0
            val minY = ys.minOrNull() ?: 0.0
            val maxY = ys.maxOrNull() ?: 1.0
            val dx = max(1e-9, maxX - minX)
            val dy = max(1e-9, maxY - minY)
            val pad = 18f
            val sx = (size.width - pad * 2) / dx.toFloat()
            val sy = (size.height - pad * 2) / dy.toFloat()
            val baseScale = min(sx, sy)
            val usedW = dx.toFloat() * baseScale
            val usedH = dy.toFloat() * baseScale
            val ox = (size.width - usedW) / 2f
            val oy = (size.height - usedH) / 2f
            val center = Offset(size.width / 2f, size.height / 2f)

            fun transformed(p: TrackPoint): Offset {
                val x0 = ox + ((p.lon * scaleLon - minX).toFloat() * baseScale)
                val y0 = size.height - (oy + ((p.lat - minY).toFloat() * baseScale))
                return Offset(
                    (x0 - center.x) * zoom + center.x + pan.x,
                    (y0 - center.y) * zoom + center.y + pan.y
                )
            }

            groups.forEachIndexed { index, (_, lapPoints) ->
                if (lapPoints.size < 2) return@forEachIndexed
                val path = Path()
                lapPoints.forEachIndexed { i, p ->
                    val pt = transformed(p)
                    if (i == 0) path.moveTo(pt.x, pt.y) else path.lineTo(pt.x, pt.y)
                }
                drawPath(path, palette[index % palette.size], style = Stroke(width = 4f, cap = StrokeCap.Round))
            }
            drawCircle(Accent, radius = 7f, center = transformed(valid.first()))
        }

        Column(
            modifier = Modifier.align(Alignment.TopStart).padding(8.dp).background(Color(0xCC0C1219), RoundedCornerShape(7.dp)).padding(horizontal = 7.dp, vertical = 4.dp)
        ) {
            groups.take(8).forEachIndexed { index, (lap, _) ->
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                    Box(Modifier.size(8.dp).background(palette[index % palette.size], RoundedCornerShape(50)))
                    Text(if (lap > 0) "G$lap" else "TRACCIA", fontSize = 10.sp, color = Color.White)
                }
            }
            if (groups.size > 8) Text("+${groups.size - 8} giri", fontSize = 9.sp, color = Muted)
        }

        Row(
            modifier = Modifier.align(Alignment.TopEnd).padding(8.dp),
            horizontalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            FilledTonalButton(
                onClick = { zoom = (zoom / 1.5f).coerceAtLeast(1f); if (zoom == 1f) pan = Offset.Zero },
                contentPadding = PaddingValues(horizontal = 10.dp, vertical = 2.dp)
            ) { Text("−") }
            FilledTonalButton(
                onClick = { zoom = (zoom * 1.5f).coerceAtMost(80f) },
                contentPadding = PaddingValues(horizontal = 10.dp, vertical = 2.dp)
            ) { Text("+") }
            FilledTonalButton(
                onClick = { zoom = 1f; pan = Offset.Zero },
                contentPadding = PaddingValues(horizontal = 8.dp, vertical = 2.dp)
            ) { Text("FIT", fontSize = 10.sp) }
        }
    }
}

private data class SatTileKey(val z: Int, val x: Int, val y: Int)
private data class SatTilePlacement(val key: SatTileKey, val left: Float, val top: Float)

private const val SAT_TILE_SIZE = 256.0
private const val SAT_MIN_ZOOM = 2
private const val SAT_MAX_ZOOM = 22
private const val SAT_NATIVE_MAX_ZOOM = 19

private fun satClampLat(lat: Double): Double = lat.coerceIn(-85.05112878, 85.05112878)

private fun satNormX(lon: Double): Double = (lon + 180.0) / 360.0

private fun satNormY(lat: Double): Double {
    val rad = Math.toRadians(satClampLat(lat))
    return (1.0 - ln(tan(rad) + 1.0 / cos(rad)) / PI) / 2.0
}

private fun satWorldSize(zoom: Int): Double = SAT_TILE_SIZE * 2.0.pow(zoom.toDouble())

private fun satWrap01(value: Double): Double {
    var v = value % 1.0
    if (v < 0.0) v += 1.0
    return v
}

private fun satWrapTileX(x: Int, n: Int): Int {
    val r = x % n
    return if (r < 0) r + n else r
}

private suspend fun loadSatelliteTile(context: Context, key: SatTileKey) = withContext(Dispatchers.IO) {
    try {
        val cacheDir = File(context.cacheDir, "goats_sat_tiles").apply { mkdirs() }
        val cacheFile = File(cacheDir, "${key.z}_${key.x}_${key.y}.jpg")

        val bitmap = if (cacheFile.exists() && cacheFile.length() > 0L) {
            BitmapFactory.decodeFile(cacheFile.absolutePath)
        } else {
            val url = URL(
                "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/" +
                    "${key.z}/${key.y}/${key.x}"
            )
            val connection = (url.openConnection() as HttpURLConnection).apply {
                connectTimeout = 6000
                readTimeout = 6000
                instanceFollowRedirects = true
                useCaches = true
                setRequestProperty("User-Agent", "GOATS-RT-Manager/0.2.2 Android")
            }
            try {
                if (connection.responseCode !in 200..299) return@withContext null
                val bytes = connection.inputStream.use { it.readBytes() }
                if (bytes.isEmpty()) return@withContext null
                runCatching { cacheFile.writeBytes(bytes) }
                BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
            } finally {
                connection.disconnect()
            }
        }
        bitmap?.asImageBitmap()
    } catch (_: Throwable) {
        null
    }
}

@Composable
private fun SatelliteTrackMap(points: List<TrackPoint>, modifier: Modifier = Modifier) {
    val context = LocalContext.current
    val valid = remember(points) {
        points.filter {
            it.lat.isFinite() && it.lon.isFinite() &&
                it.lat in -90.0..90.0 && it.lon in -180.0..180.0 &&
                !(it.lat == 0.0 && it.lon == 0.0)
        }
    }
    if (valid.size < 2) {
        Box(modifier.background(Color(0xFF0E151D), RoundedCornerShape(8.dp)), contentAlignment = Alignment.Center) {
            Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text("Nessuna traccia GPS valida", color = Muted)
                Text("Punti ricevuti: ${points.size}", color = Muted, fontSize = 11.sp)
            }
        }
        return
    }

    val groups = remember(valid) {
        valid.groupBy { it.lap }
            .toList()
            .sortedBy { (lap, _) -> if (lap <= 0) Int.MAX_VALUE else lap }
    }
    val palette = listOf(
        Color(0xFF42A5F5), Color(0xFF00C78C), Color(0xFFFFB74D), Color(0xFFEF5350),
        Color(0xFFAB47BC), Color(0xFF26C6DA), Color(0xFFD4E157), Color(0xFFEC407A),
        Color(0xFF7E57C2), Color(0xFF66BB6A), Color(0xFFFFA726), Color(0xFF29B6F6)
    )

    var viewSize by remember { mutableStateOf(IntSize.Zero) }
    var zoom by remember(valid) { mutableIntStateOf(16) }
    var centerX by remember(valid) { mutableStateOf(valid.map { satNormX(it.lon) }.average()) }
    var centerY by remember(valid) { mutableStateOf(valid.map { satNormY(it.lat) }.average()) }
    var gestureScale by remember(valid) { mutableFloatStateOf(1f) }
    var hadTileFailure by remember(valid) { mutableStateOf(false) }

    val tileImages = remember { mutableStateMapOf<SatTileKey, androidx.compose.ui.graphics.ImageBitmap>() }
    val loadingTiles = remember { mutableStateMapOf<SatTileKey, Boolean>() }

    fun fitTrack() {
        if (viewSize.width <= 0 || viewSize.height <= 0) return
        val xs = valid.map { satNormX(it.lon) }
        val ys = valid.map { satNormY(it.lat) }
        val minX = xs.minOrNull() ?: return
        val maxX = xs.maxOrNull() ?: return
        val minY = ys.minOrNull() ?: return
        val maxY = ys.maxOrNull() ?: return

        centerX = (minX + maxX) / 2.0
        centerY = (minY + maxY) / 2.0

        val usableW = max(100.0, viewSize.width.toDouble() - 56.0)
        val usableH = max(100.0, viewSize.height.toDouble() - 56.0)
        var selected = SAT_MIN_ZOOM
        for (z in SAT_MAX_ZOOM downTo SAT_MIN_ZOOM) {
            val world = satWorldSize(z)
            if ((maxX - minX) * world <= usableW && (maxY - minY) * world <= usableH) {
                selected = z
                break
            }
        }
        zoom = selected
        gestureScale = 1f
    }

    fun panBy(delta: Offset) {
        if (viewSize.width <= 0 || viewSize.height <= 0) return
        val world = satWorldSize(zoom)
        centerX = satWrap01(centerX - delta.x / world)
        centerY = (centerY - delta.y / world).coerceIn(0.0, 1.0)
    }

    fun zoomAt(newZoom: Int, anchor: Offset) {
        val next = newZoom.coerceIn(SAT_MIN_ZOOM, SAT_MAX_ZOOM)
        if (next == zoom || viewSize.width <= 0 || viewSize.height <= 0) return

        val oldWorld = satWorldSize(zoom)
        val anchorNormX = (centerX * oldWorld + anchor.x - viewSize.width / 2.0) / oldWorld
        val anchorNormY = (centerY * oldWorld + anchor.y - viewSize.height / 2.0) / oldWorld

        val newWorld = satWorldSize(next)
        centerX = satWrap01(
            (anchorNormX * newWorld - anchor.x + viewSize.width / 2.0) / newWorld
        )
        centerY = (
            (anchorNormY * newWorld - anchor.y + viewSize.height / 2.0) / newWorld
        ).coerceIn(0.0, 1.0)
        zoom = next
    }

    LaunchedEffect(valid, viewSize) {
        fitTrack()
    }

    val nativeTileZoom = min(zoom, SAT_NATIVE_MAX_ZOOM)
    val tileDisplayScale = 2.0.pow((zoom - nativeTileZoom).toDouble())

    val visibleTiles = remember(viewSize, centerX, centerY, zoom, nativeTileZoom) {
        if (viewSize.width <= 0 || viewSize.height <= 0) {
            emptyList()
        } else {
            // La vista può arrivare a Z22, ma le immagini Esri World Imagery non
            // sono garantite oltre Z19 in tutte le zone. Oltre Z19 usiamo quindi
            // la tile nativa Z19 ingrandita, mantenendo però la telemetria a Z22.
            val displayWorld = satWorldSize(zoom)
            val nativeN = 1 shl nativeTileZoom
            val tileSpan = SAT_TILE_SIZE * tileDisplayScale
            val centerPxX = centerX * displayWorld
            val centerPxY = centerY * displayWorld
            val leftWorld = centerPxX - viewSize.width / 2.0
            val topWorld = centerPxY - viewSize.height / 2.0

            val x0 = floor(leftWorld / tileSpan).toInt() - 1
            val x1 = floor((leftWorld + viewSize.width) / tileSpan).toInt() + 1
            val y0 = floor(topWorld / tileSpan).toInt() - 1
            val y1 = floor((topWorld + viewSize.height) / tileSpan).toInt() + 1

            buildList {
                for (rawY in y0..y1) {
                    if (rawY !in 0 until nativeN) continue
                    for (rawX in x0..x1) {
                        val wrappedX = satWrapTileX(rawX, nativeN)
                        add(
                            SatTilePlacement(
                                key = SatTileKey(nativeTileZoom, wrappedX, rawY),
                                left = (rawX * tileSpan - leftWorld).toFloat(),
                                top = (rawY * tileSpan - topWorld).toFloat()
                            )
                        )
                    }
                }
            }
        }
    }
    val visibleKeys = remember(visibleTiles) { visibleTiles.map { it.key }.distinct() }

    LaunchedEffect(visibleKeys) {
        if (tileImages.size > 96) {
            val keep = visibleKeys.toSet()
            tileImages.keys.toList().filterNot { it in keep }.take(tileImages.size - 72).forEach {
                tileImages.remove(it)
            }
        }
        coroutineScope {
            visibleKeys.forEach { key ->
                if (tileImages[key] == null && loadingTiles[key] != true) {
                    loadingTiles[key] = true
                    launch {
                        try {
                            val image = loadSatelliteTile(context, key)
                            if (image != null) {
                                tileImages[key] = image
                            } else {
                                hadTileFailure = true
                            }
                        } finally {
                            loadingTiles.remove(key)
                        }
                    }
                }
            }
        }
    }

    val loadedVisibleCount = visibleKeys.count { tileImages[it] != null }
    val loadingVisibleCount = visibleKeys.count { loadingTiles[it] == true }
    val tileStatus = when {
        loadedVisibleCount > 0 -> if (zoom > nativeTileZoom) "SAT Z$nativeTileZoom • VISTA Z$zoom" else "SAT ONLINE • Z$zoom"
        loadingVisibleCount > 0 -> if (zoom > nativeTileZoom) "SAT CARICAMENTO Z$nativeTileZoom • VISTA Z$zoom" else "SAT CARICAMENTO • Z$zoom"
        hadTileFailure -> "SAT OFFLINE • TRACCIA ATTIVA • Z$zoom"
        else -> "SAT • TRACCIA ATTIVA • Z$zoom"
    }

    Box(
        modifier
            .background(Color(0xFF0E151D), RoundedCornerShape(8.dp))
            .onSizeChanged { viewSize = it }
    ) {
        Canvas(
            Modifier
                .fillMaxSize()
                .pointerInput(valid) {
                    detectTransformGestures { centroid, panChange, zoomChange, _ ->
                        panBy(panChange)
                        gestureScale *= zoomChange
                        if (gestureScale >= 1.10f && zoom < SAT_MAX_ZOOM) {
                            zoomAt(zoom + 1, centroid)
                            gestureScale = 1f
                        } else if (gestureScale <= 0.91f && zoom > SAT_MIN_ZOOM) {
                            zoomAt(zoom - 1, centroid)
                            gestureScale = 1f
                        }
                    }
                }
        ) {
            visibleTiles.forEach { placement ->
                val image = tileImages[placement.key]
                if (image != null) {
                    drawImage(
                        image = image,
                        dstOffset = androidx.compose.ui.unit.IntOffset(placement.left.toInt(), placement.top.toInt()),
                        dstSize = IntSize(
                            (SAT_TILE_SIZE * tileDisplayScale).toInt().coerceAtLeast(1),
                            (SAT_TILE_SIZE * tileDisplayScale).toInt().coerceAtLeast(1)
                        )
                    )
                } else {
                    drawRect(
                        color = Color(0xFF18222D),
                        topLeft = Offset(placement.left, placement.top),
                        size = Size(
                            (SAT_TILE_SIZE * tileDisplayScale).toFloat(),
                            (SAT_TILE_SIZE * tileDisplayScale).toFloat()
                        )
                    )
                }
            }

            val world = satWorldSize(zoom)
            val centerWorldX = centerX * world
            val centerWorldY = centerY * world

            fun toScreen(p: TrackPoint): Offset {
                val px = satNormX(p.lon) * world
                val py = satNormY(p.lat) * world
                return Offset(
                    (viewSize.width / 2.0 + (px - centerWorldX)).toFloat(),
                    (viewSize.height / 2.0 + (py - centerWorldY)).toFloat()
                )
            }

            groups.forEachIndexed { index, (_, lapPoints) ->
                if (lapPoints.size < 2) return@forEachIndexed
                val path = Path()
                lapPoints.forEachIndexed { i, point ->
                    val screen = toScreen(point)
                    if (i == 0) path.moveTo(screen.x, screen.y) else path.lineTo(screen.x, screen.y)
                }
                // Dark halo keeps the telemetry line readable over bright satellite imagery.
                drawPath(
                    path = path,
                    color = Color.Black.copy(alpha = 0.72f),
                    style = Stroke(width = 9f, cap = StrokeCap.Round)
                )
                drawPath(
                    path = path,
                    color = palette[index % palette.size],
                    style = Stroke(width = 5f, cap = StrokeCap.Round)
                )
            }

            val start = toScreen(valid.first())
            drawCircle(Color.White, radius = 9f, center = start)
            drawCircle(Accent, radius = 6f, center = start)
        }

        Column(
            modifier = Modifier
                .align(Alignment.TopStart)
                .padding(8.dp)
                .background(Color(0xD90C1219), RoundedCornerShape(7.dp))
                .padding(horizontal = 7.dp, vertical = 4.dp)
        ) {
            groups.take(8).forEachIndexed { index, (lap, _) ->
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                    Box(Modifier.size(8.dp).background(palette[index % palette.size], RoundedCornerShape(50)))
                    Text(if (lap > 0) "G$lap" else "TRACCIA", fontSize = 10.sp, color = Color.White)
                }
            }
            if (groups.size > 8) Text("+${groups.size - 8} giri", fontSize = 9.sp, color = Muted)
        }

        Column(
            modifier = Modifier.align(Alignment.TopEnd).padding(8.dp),
            verticalArrangement = Arrangement.spacedBy(4.dp),
            horizontalAlignment = Alignment.End
        ) {
            FilledTonalButton(
                onClick = {
                    zoomAt(
                        zoom + 1,
                        Offset(viewSize.width / 2f, viewSize.height / 2f)
                    )
                },
                contentPadding = PaddingValues(horizontal = 12.dp, vertical = 2.dp)
            ) { Text("+") }
            FilledTonalButton(
                onClick = {
                    zoomAt(
                        zoom - 1,
                        Offset(viewSize.width / 2f, viewSize.height / 2f)
                    )
                },
                contentPadding = PaddingValues(horizontal = 12.dp, vertical = 2.dp)
            ) { Text("−") }
            FilledTonalButton(
                onClick = { fitTrack() },
                contentPadding = PaddingValues(horizontal = 9.dp, vertical = 2.dp)
            ) { Text("FIT", fontSize = 10.sp) }
        }

        Text(
            tileStatus,
            color = Color.White,
            fontSize = 9.sp,
            modifier = Modifier
                .align(Alignment.BottomStart)
                .padding(8.dp)
                .background(Color(0xD90C1219), RoundedCornerShape(6.dp))
                .padding(horizontal = 7.dp, vertical = 4.dp)
        )
        Text(
            "Imagery © Esri",
            color = Color(0xFFD7DEE8),
            fontSize = 8.sp,
            modifier = Modifier
                .align(Alignment.BottomEnd)
                .padding(6.dp)
                .background(Color(0x99000000), RoundedCornerShape(4.dp))
                .padding(horizontal = 4.dp, vertical = 2.dp)
        )
    }
}

@Composable
private fun SpeedChart(points: List<TrackPoint>, modifier: Modifier = Modifier) {
    if (points.size < 2) {
        Box(modifier, contentAlignment = Alignment.Center) { Text("Nessun dato velocità", color = Muted) }
        return
    }
    Canvas(modifier.background(Color(0xFF0E151D), RoundedCornerShape(8.dp))) {
        val minT = points.first().t
        val maxT = points.last().t.coerceAtLeast(minT + 1)
        val vmax = points.maxOfOrNull { it.speed }?.coerceAtLeast(1.0) ?: 1.0
        val pad = 14f
        val path = Path()
        points.forEachIndexed { i, p ->
            val x = pad + ((p.t - minT).toFloat() / (maxT - minT).toFloat()) * (size.width - pad * 2)
            val y = size.height - pad - (p.speed.toFloat() / vmax.toFloat()) * (size.height - pad * 2)
            if (i == 0) path.moveTo(x, y) else path.lineTo(x, y)
        }
        drawLine(Muted.copy(alpha = .25f), Offset(pad, size.height - pad), Offset(size.width - pad, size.height - pad), 1f)
        drawPath(path, Accent, style = Stroke(width = 3f, cap = StrokeCap.Round))
    }
}

@Composable
private fun UsbPanel(usb: UsbSerialManager, showMessage: (String) -> Unit) {
    var devices by remember { mutableStateOf(usb.refreshDevices()) }
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text("USB OTG", fontWeight = FontWeight.Bold)
        Text(usb.status, color = if (usb.connected) Accent else Muted, fontSize = 12.sp)
        if (usb.progress > 0f && usb.progress < 1f) LinearProgressIndicator(progress = { usb.progress }, modifier = Modifier.fillMaxWidth())
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedButton(onClick = { devices = usb.refreshDevices() }) { Text("CERCA USB") }
            if (usb.connected) OutlinedButton(onClick = { usb.disconnect(); devices = usb.refreshDevices() }) { Text("SCOLLEGA") }
        }
        if (!usb.connected) {
            devices.forEach { d ->
                OutlinedButton(onClick = {
                    try { usb.connect(d.deviceId) } catch (e: Exception) { showMessage(e.message ?: "Errore USB") }
                }, modifier = Modifier.fillMaxWidth()) {
                    Text("COLLEGA ${d.label}", maxLines = 1, overflow = TextOverflow.Ellipsis)
                }
            }
        }
    }
}

@Composable
private fun TracksScreen(
    context: Context, bridge: PythonBridge, usb: UsbSerialManager, refreshToken: Int,
    onRefresh: () -> Unit, showMessage: (String) -> Unit
) {
    var tracks by remember { mutableStateOf(emptyList<TrackUi>()) }
    val selected = remember { mutableStateMapOf<String, Boolean>() }
    var busy by remember { mutableStateOf(false) }
    var editorTrackId by remember { mutableStateOf<String?>(null) }
    var createNew by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()

    fun reload() { scope.launch { tracks = withContext(Dispatchers.IO) { bridge.tracks().toTracks() } } }
    LaunchedEffect(refreshToken) { reload() }

    if (editorTrackId != null || createNew) {
        TrackEditorScreen(
            context = context,
            bridge = bridge,
            trackId = editorTrackId,
            onBack = { editorTrackId = null; createNew = false },
            onSaved = {
                editorTrackId = null
                createNew = false
                onRefresh()
                showMessage("Circuito salvato")
            },
            showMessage = showMessage
        )
        return
    }

    val importPicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        uri ?: return@rememberLauncherForActivityResult
        scope.launch {
            try {
                val path = withContext(Dispatchers.IO) { copyUriToCache(context, uri, "track_import") }
                val r = withContext(Dispatchers.IO) { bridge.importTrack(path) }
                val warning = syncAfterLocalChange(context, bridge)
                onRefresh(); showMessage("Importati ${r.optInt("count")} circuiti" + (warning?.let { " • $it" } ?: ""))
            } catch (e: Exception) { showMessage(e.cause?.message ?: e.message ?: "Errore import circuiti") }
        }
    }

    LazyColumn(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        item { PageHeader("Circuiti", "Tocca un circuito per visualizzarlo o modificarlo") }
        item { Card(colors = CardDefaults.cardColors(containerColor = CardBg)) { Column(Modifier.padding(14.dp)) { UsbPanel(usb, showMessage) } } }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.horizontalScroll(rememberScrollState())) {
                Button(onClick = { createNew = true }) { Text("NUOVO CIRCUITO") }
                OutlinedButton(onClick = { importPicker.launch(arrayOf("application/json", "text/plain", "*/*")) }) { Text("IMPORTA JSON") }
                OutlinedButton(onClick = { tracks.forEach { selected[it.id] = true } }) { Text("TUTTI") }
                OutlinedButton(onClick = { selected.clear() }) { Text("NESSUNO") }
            }
        }
        items(tracks, key = { it.id }) { t ->
            Card(
                colors = CardDefaults.cardColors(containerColor = CardBg),
                modifier = Modifier.fillMaxWidth().clickable { editorTrackId = t.id }
            ) {
                Row(Modifier.fillMaxWidth().padding(10.dp), verticalAlignment = Alignment.CenterVertically) {
                    Checkbox(checked = selected[t.id] == true, onCheckedChange = { selected[t.id] = it })
                    Column(Modifier.weight(1f)) {
                        Text(t.name, fontWeight = FontWeight.Bold)
                        Text("${t.realSectors} settori reali • ${t.splitLines} linee intermedie • raggio ${t.triggerRadius.toInt()} m", color = Muted, fontSize = 12.sp)
                        Text("TOCCA PER APRIRE MAPPA / EDITOR", color = Accent, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                    }
                    TextButton(onClick = {
                        scope.launch {
                            withContext(Dispatchers.IO) { bridge.deleteTrack(t.id) }
                            selected.remove(t.id); onRefresh(); showMessage("Circuito eliminato")
                        }
                    }) { Text("ELIMINA", color = Danger) }
                }
            }
        }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.horizontalScroll(rememberScrollState())) {
                Button(enabled = usb.connected && selected.any { it.value } && !busy, onClick = {
                    scope.launch {
                        busy = true
                        try {
                            val ids = selected.filterValues { it }.keys
                            val summary = withContext(Dispatchers.IO) {
                                val existing = usb.readTrackCatalogBase64()
                                val merged = bridge.prepareMergedCatalog(existing, ids)
                                usb.uploadTrackCatalogBase64(merged.getString("payload_b64"))
                                merged
                            }
                            showMessage("Invio OK: ${summary.optInt("selected")} selezionati • ${summary.optInt("total")} totali")
                        } catch (e: Exception) { showMessage(e.cause?.message ?: e.message ?: "Errore invio circuiti") }
                        busy = false
                    }
                }) { Text(if (busy) "ATTENDI..." else "INVIA SELEZIONATI") }
                OutlinedButton(enabled = usb.connected && !busy, onClick = {
                    scope.launch {
                        busy = true
                        try {
                            val count = withContext(Dispatchers.IO) {
                                val b64 = usb.readTrackCatalogBase64()
                                bridge.saveCatalogFromLaptimer(b64).optInt("count")
                            }
                            val warning = syncAfterLocalChange(context, bridge)
                            onRefresh(); showMessage("Scaricati $count circuiti dal laptimer" + (warning?.let { " • $it" } ?: ""))
                        } catch (e: Exception) { showMessage(e.cause?.message ?: e.message ?: "Errore download circuiti") }
                        busy = false
                    }
                }) { Text("SCARICA DAL LAPTIMER") }
            }
        }
        item { Spacer(Modifier.height(16.dp)) }
    }
}

private data class MapSearchResult(val lat: Double, val lon: Double, val label: String)

private suspend fun searchMapLocation(query: String): MapSearchResult? = withContext(Dispatchers.IO) {
    val q = query.trim()
    if (q.isBlank()) return@withContext null
    try {
        val url = URL("https://nominatim.openstreetmap.org/search?format=json&limit=1&q=${URLEncoder.encode(q, "UTF-8")}")
        val c = (url.openConnection() as HttpURLConnection).apply {
            connectTimeout = 7000
            readTimeout = 7000
            setRequestProperty("User-Agent", "GOATS-RT-Manager-Android/0.2.2")
            setRequestProperty("Accept-Language", "it")
        }
        try {
            if (c.responseCode !in 200..299) return@withContext null
            val arr = JSONArray(c.inputStream.bufferedReader().use { it.readText() })
            if (arr.length() == 0) return@withContext null
            val o = arr.getJSONObject(0)
            MapSearchResult(o.getString("lat").toDouble(), o.getString("lon").toDouble(), o.optString("display_name", q))
        } finally { c.disconnect() }
    } catch (_: Throwable) { null }
}

@Composable
private fun TrackEditorScreen(
    context: Context,
    bridge: PythonBridge,
    trackId: String?,
    onBack: () -> Unit,
    onSaved: () -> Unit,
    showMessage: (String) -> Unit
) {
    var loaded by remember(trackId) { mutableStateOf(trackId == null) }
    var id by remember(trackId) { mutableStateOf("") }
    var name by remember(trackId) { mutableStateOf("") }
    var country by remember(trackId) { mutableStateOf("IT") }
    var direction by remember(trackId) { mutableStateOf("unspecified") }
    var radius by remember(trackId) { mutableStateOf("20") }
    var startLine by remember(trackId) { mutableStateOf<TrackLineUi?>(null) }
    val sectors = remember(trackId) { mutableStateListOf<TrackLineUi>() }
    var drawMode by remember { mutableStateOf<String?>(null) }
    var pending by remember { mutableStateOf<Pair<Double, Double>?>(null) }
    var search by remember { mutableStateOf("") }
    var focusLat by remember { mutableDoubleStateOf(42.5) }
    var focusLon by remember { mutableDoubleStateOf(12.5) }
    var focusToken by remember { mutableIntStateOf(0) }
    var busy by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()

    LaunchedEffect(trackId) {
        if (trackId != null) {
            val detail = withContext(Dispatchers.IO) { bridge.track(trackId).toTrackDetail() }
            if (!detail.ok) {
                showMessage(detail.error.ifBlank { "Circuito non trovato" })
                onBack()
                return@LaunchedEffect
            }
            id = detail.id
            name = detail.name
            country = detail.country
            direction = detail.direction
            radius = detail.triggerRadius.toString()
            startLine = detail.startLine
            sectors.clear(); sectors.addAll(detail.sectors)
            detail.startLine?.let {
                focusLat = (it.lat1 + it.lat2) / 2.0
                focusLon = (it.lon1 + it.lon2) / 2.0
                focusToken++
            }
            loaded = true
        }
    }

    fun mapPoint(lat: Double, lon: Double) {
        val mode = drawMode ?: return
        val first = pending
        if (first == null) {
            pending = lat to lon
            showMessage("Primo punto acquisito: tocca il lato opposto della pista")
            return
        }
        if (mode == "finish") {
            startLine = TrackLineUi("Traguardo", first.first, first.second, lat, lon)
        } else {
            val n = sectors.size + 1
            sectors.add(TrackLineUi("Settore $n", first.first, first.second, lat, lon))
        }
        pending = null
        drawMode = null
    }

    if (!loaded) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
        return
    }

    LazyColumn(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        item {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
                Column {
                    Text(if (trackId == null) "Nuovo circuito" else "Circuito", fontSize = 25.sp, fontWeight = FontWeight.Bold)
                    Text("Editor compatibile con il formato GTC3 del Manager Windows", color = Muted, fontSize = 12.sp)
                }
                TextButton(onClick = onBack) { Text("INDIETRO") }
            }
        }
        item {
            Card(colors = CardDefaults.cardColors(containerColor = CardBg)) {
                Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(value = name, onValueChange = { name = it }, label = { Text("Nome circuito") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedTextField(value = country, onValueChange = { country = it.take(2).uppercase() }, label = { Text("Paese") }, modifier = Modifier.weight(1f), singleLine = true)
                        OutlinedTextField(value = radius, onValueChange = { radius = it.filter { c -> c.isDigit() || c == '.' } }, label = { Text("Raggio trigger m") }, modifier = Modifier.weight(1f), singleLine = true)
                    }
                    Text("Direzione", color = Muted, fontSize = 12.sp)
                    Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        FilterChip(selected = direction == "unspecified", onClick = { direction = "unspecified" }, label = { Text("NON DEFINITA") })
                        FilterChip(selected = direction == "clockwise", onClick = { direction = "clockwise" }, label = { Text("ORARIA") })
                        FilterChip(selected = direction == "counterclockwise", onClick = { direction = "counterclockwise" }, label = { Text("ANTIORARIA") })
                    }
                }
            }
        }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                OutlinedTextField(value = search, onValueChange = { search = it }, label = { Text("Cerca circuito / località") }, modifier = Modifier.weight(1f), singleLine = true)
                Button(enabled = search.isNotBlank() && !busy, onClick = {
                    scope.launch {
                        busy = true
                        val r = searchMapLocation(search)
                        busy = false
                        if (r == null) showMessage("Località non trovata") else {
                            focusLat = r.lat; focusLon = r.lon; focusToken++
                            if (name.isBlank()) name = r.label.substringBefore(',')
                        }
                    }
                }) { Text("CERCA") }
            }
        }
        item {
            Card(colors = CardDefaults.cardColors(containerColor = CardBg)) {
                Column(Modifier.padding(10.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                        Text("Mappa circuito", fontWeight = FontWeight.Bold)
                        Text(
                            when {
                                drawMode == "finish" && pending == null -> "Traguardo: tocca il primo bordo"
                                drawMode == "finish" -> "Traguardo: tocca il secondo bordo"
                                drawMode == "sector" && pending == null -> "Settore: tocca il primo bordo"
                                drawMode == "sector" -> "Settore: tocca il secondo bordo"
                                else -> "Pinch zoom • trascina"
                            },
                            color = if (drawMode != null) Accent else Muted,
                            fontSize = 11.sp
                        )
                    }
                    TrackEditorMap(
                        startLine = startLine,
                        sectors = sectors,
                        pending = pending,
                        focusLat = focusLat,
                        focusLon = focusLon,
                        focusToken = focusToken,
                        drawing = drawMode != null,
                        onMapTap = ::mapPoint,
                        modifier = Modifier.fillMaxWidth().height(430.dp)
                    )
                    Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { pending = null; drawMode = "finish" }) { Text(if (startLine == null) "DISEGNA TRAGUARDO" else "RIDISEGNA TRAGUARDO") }
                        Button(enabled = sectors.size < 12, onClick = { pending = null; drawMode = "sector" }) { Text("AGGIUNGI SETTORE") }
                        if (drawMode != null) OutlinedButton(onClick = { drawMode = null; pending = null }) { Text("ANNULLA DISEGNO") }
                    }
                }
            }
        }
        item {
            Card(colors = CardDefaults.cardColors(containerColor = CardBg)) {
                Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text("Linee circuito", fontWeight = FontWeight.Bold)
                    if (startLine == null) Text("Traguardo non ancora definito", color = Danger, fontSize = 12.sp)
                    else Text("Traguardo definito", color = Accent, fontSize = 12.sp)
                    sectors.forEachIndexed { index, sec ->
                        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                            OutlinedTextField(
                                value = sec.name,
                                onValueChange = { newName -> sectors[index] = sec.copy(name = newName) },
                                label = { Text("Linea settore ${index + 1}") },
                                modifier = Modifier.weight(1f),
                                singleLine = true
                            )
                            TextButton(onClick = {
                                sectors.removeAt(index)
                                for (i in sectors.indices) if (sectors[i].name.startsWith("Settore ")) sectors[i] = sectors[i].copy(name = "Settore ${i + 1}")
                            }) { Text("ELIMINA", color = Danger) }
                        }
                    }
                    if (sectors.isNotEmpty()) OutlinedButton(onClick = { sectors.clear() }) { Text("CANCELLA TUTTI I SETTORI") }
                    Text("Settori reali: ${sectors.size + 1}", color = Muted, fontSize = 12.sp)
                }
            }
        }
        item {
            Button(
                enabled = !busy && name.isNotBlank() && startLine != null,
                modifier = Modifier.fillMaxWidth(),
                onClick = {
                    scope.launch {
                        busy = true
                        try {
                            val st = startLine ?: throw IllegalStateException("Disegnare il traguardo")
                            val obj = JSONObject().apply {
                                put("schema_version", 3)
                                put("id", id.ifBlank { name })
                                put("name", name.trim())
                                put("country", country.ifBlank { "IT" })
                                put("direction", direction)
                                put("trigger_radius_m", radius.toDoubleOrNull() ?: 20.0)
                                put("start_line", JSONObject().apply {
                                    put("lat1", st.lat1); put("lon1", st.lon1); put("lat2", st.lat2); put("lon2", st.lon2)
                                })
                                put("sectors", JSONArray().apply {
                                    sectors.forEachIndexed { i, sec ->
                                        put(JSONObject().apply {
                                            put("id", "sector_${i + 1}")
                                            put("name", sec.name.ifBlank { "Settore ${i + 1}" })
                                            put("lat1", sec.lat1); put("lon1", sec.lon1); put("lat2", sec.lat2); put("lon2", sec.lon2)
                                        })
                                    }
                                })
                            }
                            withContext(Dispatchers.IO) { bridge.saveTrack(obj.toString()) }
                            val warning = syncAfterLocalChange(context, bridge)
                            onSaved()
                            if (warning != null) showMessage(warning)
                        } catch (t: Throwable) {
                            showMessage(t.cause?.message ?: t.message ?: "Errore salvataggio circuito")
                        }
                        busy = false
                    }
                }
            ) { Text(if (busy) "SALVATAGGIO..." else "SALVA CIRCUITO") }
        }
        item { Spacer(Modifier.height(16.dp)) }
    }
}

private fun satNormToLat(y: Double): Double = Math.toDegrees(atan(sinh(PI * (1.0 - 2.0 * y))))
private fun satNormToLon(x: Double): Double = satWrap01(x) * 360.0 - 180.0

@Composable
private fun TrackEditorMap(
    startLine: TrackLineUi?,
    sectors: List<TrackLineUi>,
    pending: Pair<Double, Double>?,
    focusLat: Double,
    focusLon: Double,
    focusToken: Int,
    drawing: Boolean,
    onMapTap: (Double, Double) -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    var viewSize by remember { mutableStateOf(IntSize.Zero) }
    var centerX by remember { mutableDoubleStateOf(satNormX(focusLon)) }
    var centerY by remember { mutableDoubleStateOf(satNormY(focusLat)) }
    var zoom by remember { mutableIntStateOf(if (startLine == null) 6 else 18) }
    var gestureScale by remember { mutableFloatStateOf(1f) }
    val tileImages = remember { mutableStateMapOf<SatTileKey, androidx.compose.ui.graphics.ImageBitmap>() }
    val loadingTiles = remember { mutableStateMapOf<SatTileKey, Boolean>() }
    var hadTileFailure by remember { mutableStateOf(false) }

    fun fitLines() {
        if (viewSize.width <= 0 || viewSize.height <= 0) return
        val pts = buildList {
            startLine?.let { add(it.lat1 to it.lon1); add(it.lat2 to it.lon2) }
            sectors.forEach { add(it.lat1 to it.lon1); add(it.lat2 to it.lon2) }
        }
        if (pts.isEmpty()) return
        val xs = pts.map { satNormX(it.second) }
        val ys = pts.map { satNormY(it.first) }
        val minX = xs.minOrNull() ?: return
        val maxX = xs.maxOrNull() ?: return
        val minY = ys.minOrNull() ?: return
        val maxY = ys.maxOrNull() ?: return
        centerX = (minX + maxX) / 2.0
        centerY = (minY + maxY) / 2.0
        val usableW = max(100.0, viewSize.width.toDouble() - 70.0)
        val usableH = max(100.0, viewSize.height.toDouble() - 70.0)
        var zsel = 18
        for (z in SAT_MAX_ZOOM downTo SAT_MIN_ZOOM) {
            val world = satWorldSize(z)
            if ((maxX - minX) * world <= usableW && (maxY - minY) * world <= usableH) { zsel = z; break }
        }
        zoom = zsel.coerceAtMost(20)
    }

    fun panBy(delta: Offset) {
        if (viewSize.width <= 0 || viewSize.height <= 0) return
        val world = satWorldSize(zoom)
        centerX = satWrap01(centerX - delta.x / world)
        centerY = (centerY - delta.y / world).coerceIn(0.0, 1.0)
    }

    fun zoomAt(newZoom: Int, anchor: Offset) {
        val next = newZoom.coerceIn(SAT_MIN_ZOOM, SAT_MAX_ZOOM)
        if (next == zoom || viewSize.width <= 0 || viewSize.height <= 0) return
        val oldWorld = satWorldSize(zoom)
        val anchorNormX = (centerX * oldWorld + anchor.x - viewSize.width / 2.0) / oldWorld
        val anchorNormY = (centerY * oldWorld + anchor.y - viewSize.height / 2.0) / oldWorld
        val newWorld = satWorldSize(next)
        centerX = satWrap01((anchorNormX * newWorld - anchor.x + viewSize.width / 2.0) / newWorld)
        centerY = ((anchorNormY * newWorld - anchor.y + viewSize.height / 2.0) / newWorld).coerceIn(0.0, 1.0)
        zoom = next
    }

    LaunchedEffect(viewSize, startLine) { if (startLine != null) fitLines() }
    LaunchedEffect(focusToken) {
        centerX = satNormX(focusLon)
        centerY = satNormY(focusLat)
        zoom = 18
    }

    val nativeTileZoom = min(zoom, SAT_NATIVE_MAX_ZOOM)
    val tileDisplayScale = 2.0.pow((zoom - nativeTileZoom).toDouble())
    val visibleTiles = remember(viewSize, centerX, centerY, zoom, nativeTileZoom) {
        if (viewSize.width <= 0 || viewSize.height <= 0) emptyList() else {
            val displayWorld = satWorldSize(zoom)
            val nativeN = 1 shl nativeTileZoom
            val tileSpan = SAT_TILE_SIZE * tileDisplayScale
            val centerPxX = centerX * displayWorld
            val centerPxY = centerY * displayWorld
            val leftWorld = centerPxX - viewSize.width / 2.0
            val topWorld = centerPxY - viewSize.height / 2.0
            val x0 = floor(leftWorld / tileSpan).toInt() - 1
            val x1 = floor((leftWorld + viewSize.width) / tileSpan).toInt() + 1
            val y0 = floor(topWorld / tileSpan).toInt() - 1
            val y1 = floor((topWorld + viewSize.height) / tileSpan).toInt() + 1
            buildList {
                for (rawY in y0..y1) {
                    if (rawY !in 0 until nativeN) continue
                    for (rawX in x0..x1) {
                        add(SatTilePlacement(SatTileKey(nativeTileZoom, satWrapTileX(rawX, nativeN), rawY), (rawX * tileSpan - leftWorld).toFloat(), (rawY * tileSpan - topWorld).toFloat()))
                    }
                }
            }
        }
    }
    val visibleKeys = remember(visibleTiles) { visibleTiles.map { it.key }.distinct() }

    LaunchedEffect(visibleKeys) {
        coroutineScope {
            visibleKeys.forEach { key ->
                if (tileImages[key] == null && loadingTiles[key] != true) {
                    loadingTiles[key] = true
                    launch {
                        try {
                            val image = loadSatelliteTile(context, key)
                            if (image != null) tileImages[key] = image else hadTileFailure = true
                        } finally { loadingTiles.remove(key) }
                    }
                }
            }
        }
    }

    Box(modifier.background(Color(0xFF0E151D), RoundedCornerShape(8.dp)).onSizeChanged { viewSize = it }) {
        Canvas(
            Modifier.fillMaxSize()
                .pointerInput(Unit) {
                    detectTransformGestures { centroid, panChange, zoomChange, _ ->
                        panBy(panChange)
                        gestureScale *= zoomChange
                        if (gestureScale >= 1.10f && zoom < SAT_MAX_ZOOM) { zoomAt(zoom + 1, centroid); gestureScale = 1f }
                        else if (gestureScale <= 0.91f && zoom > SAT_MIN_ZOOM) { zoomAt(zoom - 1, centroid); gestureScale = 1f }
                    }
                }
                .pointerInput(drawing, centerX, centerY, zoom, viewSize) {
                    detectTapGestures { pos ->
                        if (!drawing || viewSize.width <= 0 || viewSize.height <= 0) return@detectTapGestures
                        val world = satWorldSize(zoom)
                        val nx = (centerX * world + pos.x - viewSize.width / 2.0) / world
                        val ny = ((centerY * world + pos.y - viewSize.height / 2.0) / world).coerceIn(0.0, 1.0)
                        onMapTap(satNormToLat(ny), satNormToLon(nx))
                    }
                }
        ) {
            visibleTiles.forEach { placement ->
                val image = tileImages[placement.key]
                val tileSize = (SAT_TILE_SIZE * tileDisplayScale).toInt().coerceAtLeast(1)
                if (image != null) drawImage(image, dstOffset = androidx.compose.ui.unit.IntOffset(placement.left.toInt(), placement.top.toInt()), dstSize = IntSize(tileSize, tileSize))
                else drawRect(Color(0xFF18222D), topLeft = Offset(placement.left, placement.top), size = Size(tileSize.toFloat(), tileSize.toFloat()))
            }
            val world = satWorldSize(zoom)
            val cx = centerX * world
            val cy = centerY * world
            fun point(lat: Double, lon: Double): Offset = Offset(
                (viewSize.width / 2.0 + (satNormX(lon) * world - cx)).toFloat(),
                (viewSize.height / 2.0 + (satNormY(lat) * world - cy)).toFloat()
            )
            fun paintTrackLine(line: TrackLineUi, color: Color, width: Float) {
                val a = point(line.lat1, line.lon1)
                val b = point(line.lat2, line.lon2)
                drawLine(Color.Black.copy(alpha = 0.75f), a, b, strokeWidth = width + 5f, cap = StrokeCap.Round)
                drawLine(color, a, b, strokeWidth = width, cap = StrokeCap.Round)
                drawCircle(Color.White, 5f, a); drawCircle(Color.White, 5f, b)
            }
            startLine?.let { paintTrackLine(it, Accent, 6f) }
            sectors.forEach { paintTrackLine(it, Accent2, 5f) }
            pending?.let { drawCircle(Color.Yellow, 8f, point(it.first, it.second)) }
        }
        Column(Modifier.align(Alignment.TopStart).padding(8.dp).background(Color(0xD90C1219), RoundedCornerShape(6.dp)).padding(horizontal = 7.dp, vertical = 4.dp)) {
            Text("SAT • Z$zoom", color = Color.White, fontSize = 10.sp, fontWeight = FontWeight.Bold)
            if (hadTileFailure) Text("alcune tile offline", color = Muted, fontSize = 9.sp)
        }
        Row(Modifier.align(Alignment.BottomEnd).padding(8.dp), horizontalArrangement = Arrangement.spacedBy(5.dp)) {
            FilledTonalButton(
                onClick = { zoomAt(zoom - 1, Offset(viewSize.width / 2f, viewSize.height / 2f)) },
                contentPadding = PaddingValues(horizontal = 10.dp, vertical = 2.dp)
            ) { Text("−") }
            FilledTonalButton(
                onClick = { zoomAt(zoom + 1, Offset(viewSize.width / 2f, viewSize.height / 2f)) },
                contentPadding = PaddingValues(horizontal = 10.dp, vertical = 2.dp)
            ) { Text("+") }
            if (startLine != null) FilledTonalButton(
                onClick = { fitLines() },
                contentPadding = PaddingValues(horizontal = 8.dp, vertical = 2.dp)
            ) { Text("FIT", fontSize = 10.sp) }
        }
    }
}

@Composable
private fun InfoScreen(usb: UsbSerialManager) {
    LazyColumn(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item { PageHeader("Informazioni", "GOATS RT Manager per Android") }
        item {
            Card(colors = CardDefaults.cardColors(containerColor = CardBg)) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text("Versione Android 0.2.2", fontWeight = FontWeight.Bold)
                    Text("Motore dati allineato a GOATS RT Manager V5.4.13.8 BRAKE DELTA DISPLAY EXACT FIX", color = Muted)
                    Text("Python 3.13 incorporato • SQLite locale • UI Kotlin/Jetpack Compose", color = Muted)
                    Text("USB: ${usb.status}", color = if (usb.connected) Accent else Muted)
                }
            }
        }
        item {
            Card(colors = CardDefaults.cardColors(containerColor = CardBg)) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text("Già incluso", fontWeight = FontWeight.Bold)
                    Text("• Import GRT8 / GSA2 / GSA3 / CSV / JSON\n• Archivio SQLite e note lato motore\n• Analisi traiettoria e velocità offline\n• Catalogo circuiti GTC3 + editor grafico Android\n• Creazione traguardo/settori su mappa satellitare\n• Merge non distruttivo e upload/download circuiti USB\n• Import sessioni Wi-Fi da hotspot lap timer\n• Cloud Sync sessioni e circuiti con Windows V5.4.15.6\n• Cartella condivisa tramite provider Android compatibile\n• Varianti conservate in caso di modifiche concorrenti\n• Analisi GPS con mappa satellitare nativa e traiettorie multi-giro", color = Muted)
                }
            }
        }
        item {
            Card(colors = CardDefaults.cardColors(containerColor = CardBg)) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text("Da completare nel porting", fontWeight = FontWeight.Bold)
                    Text("• replay avanzato e analisi frenate complete come PC\n• confronto sessioni completo\n• eventuale trasporto GSES2 su Wi-Fi/TCP oltre al REST\n• ulteriori strumenti di confronto e report", color = Muted)
                }
            }
        }
    }
}

private fun copyUriToCache(context: Context, uri: Uri, prefix: String): String {
    val resolver = context.contentResolver
    var name = "${prefix}_${System.currentTimeMillis()}"
    resolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { c ->
        if (c.moveToFirst()) {
            val idx = c.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if (idx >= 0) name = c.getString(idx) ?: name
        }
    }
    val clean = name.replace(Regex("[^A-Za-z0-9._-]"), "_")
    val dir = File(context.cacheDir, "goats_import").apply { mkdirs() }
    val dest = File(dir, "${System.currentTimeMillis()}_$clean")
    resolver.openInputStream(uri).use { input ->
        requireNotNull(input) { "Impossibile leggere il file selezionato" }
        dest.outputStream().use { output -> input.copyTo(output) }
    }
    return dest.absolutePath
}
