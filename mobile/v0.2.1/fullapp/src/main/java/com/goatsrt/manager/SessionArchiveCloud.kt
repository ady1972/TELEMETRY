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
    val errors: Int
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

    private fun children(context: Context, tree: Uri): List<CloudDoc> {
        val resolver = context.contentResolver
        val treeId = DocumentsContract.getTreeDocumentId(tree)
        val childrenUri = DocumentsContract.buildChildDocumentsUriUsingTree(tree, treeId)
        val out = mutableListOf<CloudDoc>()
        val projection = arrayOf(
            DocumentsContract.Document.COLUMN_DOCUMENT_ID,
            DocumentsContract.Document.COLUMN_DISPLAY_NAME,
            DocumentsContract.Document.COLUMN_MIME_TYPE,
            DocumentsContract.Document.COLUMN_SIZE
        )
        resolver.query(childrenUri, projection, null, null, null)?.use { c ->
            val idIdx = c.getColumnIndex(DocumentsContract.Document.COLUMN_DOCUMENT_ID)
            val nameIdx = c.getColumnIndex(DocumentsContract.Document.COLUMN_DISPLAY_NAME)
            val mimeIdx = c.getColumnIndex(DocumentsContract.Document.COLUMN_MIME_TYPE)
            val sizeIdx = c.getColumnIndex(DocumentsContract.Document.COLUMN_SIZE)
            while (c.moveToNext()) {
                val mime = if (mimeIdx >= 0) c.getString(mimeIdx) else ""
                if (mime == DocumentsContract.Document.MIME_TYPE_DIR) continue
                val name = if (nameIdx >= 0) c.getString(nameIdx) ?: "" else ""
                if (!SessionArchive.isSupported(name)) continue
                val id = c.getString(idIdx)
                val uri = DocumentsContract.buildDocumentUriUsingTree(tree, id)
                val size = if (sizeIdx >= 0 && !c.isNull(sizeIdx)) c.getLong(sizeIdx) else 0L
                out += CloudDoc(uri, name, size)
            }
        }
        return out
    }

    private fun mimeFor(name: String): String = when (name.substringAfterLast('.', "").lowercase()) {
        "csv" -> "text/csv"
        "json" -> "application/json"
        else -> "application/octet-stream"
    }

    private fun uploadOne(context: Context, tree: Uri, source: File, existing: MutableMap<String, CloudDoc>): Boolean {
        val resolver = context.contentResolver
        val found = existing[source.name]
        if (found != null && found.size == source.length()) return false
        val target = found?.uri ?: run {
            val rootId = DocumentsContract.getTreeDocumentId(tree)
            val rootUri = DocumentsContract.buildDocumentUriUsingTree(tree, rootId)
            DocumentsContract.createDocument(resolver, rootUri, mimeFor(source.name), source.name)
                ?: throw IllegalStateException("Impossibile creare ${source.name} nel cloud")
        }
        resolver.openOutputStream(target, "wt").use { output ->
            requireNotNull(output) { "Impossibile scrivere ${source.name} nel cloud" }
            source.inputStream().use { input -> input.copyTo(output) }
        }
        existing[source.name] = CloudDoc(target, source.name, source.length())
        return true
    }

    fun uploadFileIfEnabled(context: Context, file: File): Boolean {
        if (!autoSync(context)) return false
        val tree = folderUri(context) ?: return false
        val existing = children(context, tree).associateBy { it.name }.toMutableMap()
        return uploadOne(context, tree, file, existing)
    }

    fun sync(context: Context, bridge: PythonBridge): CloudSyncResult {
        val tree = folderUri(context) ?: throw IllegalStateException("Seleziona prima una cartella cloud")
        var imported = 0
        var uploaded = 0
        var downloaded = 0
        var errors = 0
        val existing = children(context, tree).associateBy { it.name }.toMutableMap()

        // Cloud -> archivio locale -> database Android.
        for (doc in existing.values.sortedBy { it.name.lowercase() }) {
            try {
                val local = File(SessionArchive.dir(context), doc.name.replace(Regex("[^A-Za-z0-9._-]"), "_"))
                val needDownload = !local.exists() || (doc.size > 0 && local.length() != doc.size)
                if (needDownload) {
                    context.contentResolver.openInputStream(doc.uri).use { input ->
                        requireNotNull(input) { "Impossibile leggere ${doc.name}" }
                        local.outputStream().use { output -> input.copyTo(output) }
                    }
                    downloaded++
                }
                val result = bridge.importFile(local.absolutePath)
                imported += result.optInt("count", 0)
            } catch (_: Throwable) {
                errors++
            }
        }

        // Archivio locale -> cloud.
        for (file in SessionArchive.files(context)) {
            try {
                if (uploadOne(context, tree, file, existing)) uploaded++
            } catch (_: Throwable) {
                errors++
            }
        }
        return CloudSyncResult(imported, uploaded, downloaded, errors)
    }
}
