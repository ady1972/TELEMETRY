package com.goatsrt.manager

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.provider.DocumentsContract
import android.provider.OpenableColumns
import java.io.File
import java.security.MessageDigest

/**
 * Archivio locale + sincronizzazione cartella cloud.
 *
 * Android non lega l'app a un provider specifico: l'utente sceglie una cartella
 * tramite il selettore di sistema (Google Drive, OneDrive, Dropbox, memoria locale,
 * ecc. se il relativo provider documenti è installato). L'autorizzazione viene
 * resa persistente e la stessa cartella può essere sincronizzata dal Manager PC.
 */
data class CloudSyncResult(
    val imported: Int,
    val uploaded: Int,
    val downloaded: Int,
    val errors: Int,
    val tracksImported: Int = 0,
    val conflicts: Int = 0,
    val errorMessages: List<String> = emptyList()
)

object SessionArchive {
    private val supportedExt = setOf("csv", "grt", "gsa", "bin", "json")

    fun dir(context: Context): File = File(context.filesDir, "goats_rt_manager/session_files").apply { mkdirs() }

    fun isSupported(name: String): Boolean = name.substringAfterLast('.', "").lowercase() in supportedExt

    private fun cleanName(name: String): String {
        val cleaned = name.replace(Regex("[^A-Za-z0-9._-]"), "_").trim('_')
        return cleaned.ifBlank { "sessione_${System.currentTimeMillis()}.bin" }.take(160)
    }

    private fun sha256(file: File): String {
        val md = MessageDigest.getInstance("SHA-256")
        file.inputStream().use { input ->
            val buf = ByteArray(128 * 1024)
            while (true) {
                val n = input.read(buf)
                if (n <= 0) break
                md.update(buf, 0, n)
            }
        }
        return md.digest().joinToString("") { "%02x".format(it) }
    }

    private fun chooseDestination(context: Context, preferredName: String, source: File? = null): File {
        val root = dir(context)
        val clean = cleanName(preferredName)
        val base = clean.substringBeforeLast('.', clean)
        val ext = clean.substringAfterLast('.', "")
        var candidate = File(root, clean)
        if (!candidate.exists()) return candidate
        if (source != null && candidate.length() == source.length()) {
            try {
                if (sha256(candidate) == sha256(source)) return candidate
            } catch (_: Throwable) { }
        }
        var i = 2
        while (candidate.exists()) {
            val suffix = if (ext.isBlank()) "_${i}" else "_${i}.$ext"
            candidate = File(root, "$base$suffix")
            i++
        }
        return candidate
    }

    fun storeFile(context: Context, source: File, preferredName: String = source.name): File {
        require(source.exists()) { "File sessione non trovato" }
        val dest = chooseDestination(context, preferredName, source)
        if (dest.absolutePath != source.absolutePath && !dest.exists()) source.copyTo(dest)
        return dest
    }

    fun displayName(context: Context, uri: Uri): String {
        var name = "sessione_${System.currentTimeMillis()}"
        context.contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { c ->
            if (c.moveToFirst()) {
                val idx = c.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                if (idx >= 0) name = c.getString(idx) ?: name
            }
        }
        return cleanName(name)
    }

    fun storeUri(context: Context, uri: Uri): File {
        val name = displayName(context, uri)
        val root = dir(context)
        val tmp = File(root, ".incoming_${System.nanoTime()}_${name}")
        context.contentResolver.openInputStream(uri).use { input ->
            requireNotNull(input) { "Impossibile leggere il file selezionato" }
            tmp.outputStream().use { output -> input.copyTo(output) }
        }
        return try {
            val dest = chooseDestination(context, name, tmp)
            if (dest.exists()) {
                tmp.delete()
                dest
            } else {
                if (!tmp.renameTo(dest)) {
                    tmp.copyTo(dest)
                    tmp.delete()
                }
                dest
            }
        } catch (t: Throwable) {
            tmp.delete()
            throw t
        }
    }

    fun files(context: Context): List<File> = dir(context).listFiles()
        ?.filter { it.isFile && !it.name.startsWith(".") && isSupported(it.name) }
        ?.sortedBy { it.name.lowercase() }
        ?: emptyList()
}

object CloudSessionSync {
    private const val PREFS = "goats_cloud_sync"
    private const val KEY_URI = "folder_uri"
    private const val KEY_AUTO = "auto_sync"

    data class CloudDoc(val uri: Uri, val name: String, val size: Long)

    private fun prefs(context: Context) = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    fun folderUri(context: Context): Uri? = prefs(context).getString(KEY_URI, null)?.let(Uri::parse)
    fun autoSync(context: Context): Boolean = prefs(context).getBoolean(KEY_AUTO, false)
    fun setAutoSync(context: Context, value: Boolean) = prefs(context).edit().putBoolean(KEY_AUTO, value).apply()

    fun setFolder(context: Context, uri: Uri) {
        context.contentResolver.takePersistableUriPermission(
            uri,
            Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION
        )
        prefs(context).edit().putString(KEY_URI, uri.toString()).apply()
    }

    fun clearFolder(context: Context) {
        prefs(context).edit().remove(KEY_URI).putBoolean(KEY_AUTO, false).apply()
    }

    fun folderLabel(context: Context): String {
        val tree = folderUri(context) ?: return "Nessuna cartella selezionata"
        return try {
            val docId = DocumentsContract.getTreeDocumentId(tree)
            val docUri = DocumentsContract.buildDocumentUriUsingTree(tree, docId)
            context.contentResolver.query(docUri, arrayOf(DocumentsContract.Document.COLUMN_DISPLAY_NAME), null, null, null)?.use { c ->
                if (c.moveToFirst()) c.getString(0) else null
            } ?: tree.toString()
        } catch (_: Throwable) {
            tree.toString()
        }
    }

    private fun rootUri(tree: Uri): Uri = DocumentsContract.buildDocumentUriUsingTree(tree, DocumentsContract.getTreeDocumentId(tree))

    private fun children(context: Context, tree: Uri, parent: Uri): List<CloudDoc> {
        val uri = DocumentsContract.buildChildDocumentsUriUsingTree(tree, DocumentsContract.getDocumentId(parent))
        val out = mutableListOf<CloudDoc>()
        context.contentResolver.query(uri, arrayOf(DocumentsContract.Document.COLUMN_DOCUMENT_ID,
            DocumentsContract.Document.COLUMN_DISPLAY_NAME, DocumentsContract.Document.COLUMN_SIZE), null, null, null)?.use { c ->
            while (c.moveToNext()) {
                val name = c.getString(1) ?: continue
                if (name.isBlank() || name in setOf(".", "..") || name.contains('/') || name.contains('\\') || name.contains('\u0000')) continue
                out += CloudDoc(DocumentsContract.buildDocumentUriUsingTree(tree, c.getString(0)), name, if (c.isNull(2)) 0L else c.getLong(2))
            }
        } ?: throw IllegalStateException("Impossibile leggere la cartella selezionata. Controlla accesso e connessione del provider.")
        return out
    }

    private fun sha256(file: File): String = file.inputStream().use { input -> hashStream(input) }

    private fun hashStream(input: java.io.InputStream): String {
        val digest = MessageDigest.getInstance("SHA-256")
        val buffer = ByteArray(256 * 1024)
        while (true) {
            val count = input.read(buffer)
            if (count <= 0) break
            digest.update(buffer, 0, count)
        }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }

    private fun mimeFor(name: String): String = when (name.substringAfterLast('.', "").lowercase()) {
        "csv" -> "text/csv"
        "json" -> "application/json"
        else -> "application/octet-stream"
    }

    private fun download(context: Context, docs: List<CloudDoc>, target: File, errors: MutableList<String>): MutableSet<String> {
        target.mkdirs()
        val hashes = mutableSetOf<String>()
        for (doc in docs.filter { SessionArchive.isSupported(it.name) }) {
            var partial: File? = null
            try {
                var file = File(target, doc.name)
                var suffix = 2
                while (file.exists()) {
                    file = File(target, doc.name.substringBeforeLast('.') + "_${suffix}." + doc.name.substringAfterLast('.'))
                    suffix++
                }
                partial = file
                context.contentResolver.openInputStream(doc.uri).use { input ->
                    requireNotNull(input) { "Impossibile leggere ${doc.name}" }
                    file.outputStream().use { output -> input.copyTo(output, 256 * 1024) }
                }
                check(doc.size <= 0L || file.length() == doc.size) { "Download incompleto: ${doc.name}" }
                hashes += sha256(file)
                partial = null
            } catch (t: Exception) {
                partial?.delete()
                errors += "${doc.name}: ${t.message}"
            }
        }
        return hashes
    }

    private fun uploadNew(context: Context, parent: Uri, files: List<File>, knownHashes: MutableSet<String>, errors: MutableList<String>): Int {
        var uploaded = 0
        for (file in files) {
            try {
                val expected = sha256(file)
                if (expected in knownHashes) continue
                // Always create: an existing cloud file is never truncated.
                val uri = DocumentsContract.createDocument(context.contentResolver, parent, mimeFor(file.name), file.name)
                    ?: throw IllegalStateException("Il provider non consente di creare ${file.name}")
                context.contentResolver.openOutputStream(uri, "w").use { output ->
                    requireNotNull(output) { "Impossibile scrivere ${file.name}" }
                    file.inputStream().use { input -> input.copyTo(output, 256 * 1024) }
                }
                val actual = context.contentResolver.openInputStream(uri).use { input ->
                    requireNotNull(input) { "Impossibile verificare ${file.name}" }
                    hashStream(input)
                }
                check(actual == expected) { "Verifica integrità fallita per ${file.name}; l'originale locale è conservato" }
                knownHashes += expected
                uploaded++
            } catch (t: Exception) { errors += "${file.name}: ${t.message}" }
        }
        return uploaded
    }

    fun syncIfEnabled(context: Context, bridge: PythonBridge): CloudSyncResult? =
        if (autoSync(context) && folderUri(context) != null) sync(context, bridge) else null

    @Synchronized
    fun sync(context: Context, bridge: PythonBridge): CloudSyncResult {
        val tree = folderUri(context) ?: throw IllegalStateException("Seleziona la stessa cartella cloud del Manager Windows")
        val root = rootUri(tree)
        val staging = File(context.cacheDir, "goats_sync_${System.nanoTime()}").apply { mkdirs() }
        val errors = mutableListOf<String>()
        try {
            val rootDocs = children(context, tree, root)
            val tracksDoc = rootDocs.firstOrNull { it.name == "circuiti" }
            val rootHashes = download(context, rootDocs, staging, errors)
            val tracksStage = File(staging, "circuiti")
            val trackHashes = download(context, tracksDoc?.let { children(context, tree, it.uri) } ?: emptyList(), tracksStage, errors)
            val result = bridge.syncCloudFolder(staging.absolutePath)
            val engineErrors = result.optJSONArray("errors")
            if (engineErrors != null) for (i in 0 until engineErrors.length()) errors += engineErrors.getString(i)
            var uploaded = uploadNew(context, root, staging.listFiles()?.filter { it.isFile && SessionArchive.isSupported(it.name) } ?: emptyList(), rootHashes, errors)
            val trackFiles = tracksStage.listFiles()?.filter { it.isFile && it.extension.lowercase() == "json" } ?: emptyList()
            if (trackFiles.isNotEmpty()) {
                try {
                    val parent = tracksDoc?.uri ?: DocumentsContract.createDocument(context.contentResolver, root,
                        DocumentsContract.Document.MIME_TYPE_DIR, "circuiti")
                        ?: throw IllegalStateException("Il provider non consente di creare la cartella circuiti")
                    uploaded += uploadNew(context, parent, trackFiles, trackHashes, errors)
                } catch (t: Exception) { errors += "Circuiti: ${t.message}" }
            }
            return CloudSyncResult(result.optInt("imported"), uploaded, result.optInt("downloaded"), errors.size,
                result.optInt("tracks_imported"), result.optInt("conflicts"), errors.take(5))
        } finally { staging.deleteRecursively() }
    }
}
