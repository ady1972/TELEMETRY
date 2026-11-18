package com.goatsrt.manager

import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.hardware.usb.UsbDevice
import android.hardware.usb.UsbManager
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.core.content.ContextCompat
import com.hoho.android.usbserial.driver.UsbSerialDriver
import com.hoho.android.usbserial.driver.UsbSerialPort
import com.hoho.android.usbserial.driver.UsbSerialProber
import java.io.ByteArrayOutputStream
import java.nio.charset.StandardCharsets
import java.util.zip.CRC32

private const val ACTION_USB_PERMISSION = "com.goatsrt.manager.USB_PERMISSION"

data class UsbDeviceUi(
    val deviceId: Int,
    val label: String,
    val vendorId: Int,
    val productId: Int,
)

class UsbSerialManager(private val context: Context) {
    private val usbManager = context.getSystemService(Context.USB_SERVICE) as UsbManager
    private var drivers: List<UsbSerialDriver> = emptyList()
    private var activeDriver: UsbSerialDriver? = null
    private var activePort: UsbSerialPort? = null
    private var activeConnection: android.hardware.usb.UsbDeviceConnection? = null
    private var pendingDeviceId: Int? = null

    var status by mutableStateOf("USB non collegata")
        private set
    var connected by mutableStateOf(false)
        private set
    var progress by mutableFloatStateOf(0f)
        private set

    private val receiver = object : BroadcastReceiver() {
        override fun onReceive(ctx: Context?, intent: Intent?) {
            if (intent?.action != ACTION_USB_PERMISSION) return
            val device: UsbDevice? = intent.getParcelableExtra(UsbManager.EXTRA_DEVICE)
            val granted = intent.getBooleanExtra(UsbManager.EXTRA_PERMISSION_GRANTED, false)
            if (granted && device != null && device.deviceId == pendingDeviceId) {
                try {
                    openDevice(device.deviceId)
                } catch (e: Exception) {
                    status = "Errore USB: ${e.message}"
                }
            } else {
                status = "Permesso USB negato"
            }
            pendingDeviceId = null
        }
    }

    init {
        ContextCompat.registerReceiver(
            context,
            receiver,
            IntentFilter(ACTION_USB_PERMISSION),
            ContextCompat.RECEIVER_NOT_EXPORTED
        )
        refreshDevices()
    }

    fun close() {
        disconnect()
        try { context.unregisterReceiver(receiver) } catch (_: Exception) {}
    }

    fun refreshDevices(): List<UsbDeviceUi> {
        drivers = UsbSerialProber.getDefaultProber().findAllDrivers(usbManager)
        if (drivers.isEmpty() && !connected) status = "Nessuna seriale USB rilevata"
        return drivers.map { d ->
            val dev = d.device
            UsbDeviceUi(
                deviceId = dev.deviceId,
                label = "${dev.deviceName} • VID %04X PID %04X".format(dev.vendorId, dev.productId),
                vendorId = dev.vendorId,
                productId = dev.productId,
            )
        }
    }

    fun connect(deviceId: Int) {
        val driver = drivers.firstOrNull { it.device.deviceId == deviceId }
            ?: UsbSerialProber.getDefaultProber().findAllDrivers(usbManager)
                .firstOrNull { it.device.deviceId == deviceId }
            ?: throw IllegalStateException("Dispositivo USB non trovato")
        val device = driver.device
        if (!usbManager.hasPermission(device)) {
            pendingDeviceId = deviceId
            status = "Richiesta permesso USB..."
            val pi = PendingIntent.getBroadcast(
                context, 0, Intent(ACTION_USB_PERMISSION).setPackage(context.packageName),
                PendingIntent.FLAG_MUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
            )
            usbManager.requestPermission(device, pi)
            return
        }
        openDevice(deviceId)
    }

    private fun openDevice(deviceId: Int) {
        disconnect()
        drivers = UsbSerialProber.getDefaultProber().findAllDrivers(usbManager)
        val driver = drivers.firstOrNull { it.device.deviceId == deviceId }
            ?: throw IllegalStateException("Driver seriale non trovato")
        val connection = usbManager.openDevice(driver.device)
            ?: throw IllegalStateException("Impossibile aprire il dispositivo USB")
        val port = driver.ports.firstOrNull()
            ?: throw IllegalStateException("Nessuna porta seriale nel dispositivo")
        port.open(connection)
        port.setParameters(
            115200, 8,
            UsbSerialPort.STOPBITS_1,
            UsbSerialPort.PARITY_NONE
        )
        try { port.purgeHwBuffers(true, true) } catch (_: Exception) {}
        activeDriver = driver
        activePort = port
        activeConnection = connection
        connected = true
        status = "Connesso: ${driver.device.deviceName} @ 115200"
        progress = 0f
    }

    fun disconnect() {
        try { activePort?.close() } catch (_: Exception) {}
        try { activeConnection?.close() } catch (_: Exception) {}
        activePort = null
        activeDriver = null
        activeConnection = null
        connected = false
        progress = 0f
        status = "USB non collegata"
    }

    private fun port(): UsbSerialPort = activePort ?: throw IllegalStateException("Collega prima il laptimer via USB OTG")

    private fun write(data: ByteArray, timeoutMs: Int = 5000) {
        port().write(data, timeoutMs)
    }

    private fun readLine(timeoutMs: Long = 5000): String {
        val p = port()
        val deadline = System.currentTimeMillis() + timeoutMs
        val out = ByteArrayOutputStream()
        val one = ByteArray(1)
        while (System.currentTimeMillis() < deadline) {
            val n = try { p.read(one, 100) } catch (_: Exception) { 0 }
            if (n > 0) {
                val b = one[0]
                if (b == '\n'.code.toByte()) {
                    return out.toString(StandardCharsets.US_ASCII.name()).trim()
                }
                if (b != '\r'.code.toByte()) {
                    out.write(b.toInt())
                    if (out.size() > 1024) throw IllegalStateException("Riga protocollo USB troppo lunga")
                }
            }
        }
        return out.toString(StandardCharsets.US_ASCII.name()).trim()
    }

    private fun readExact(size: Int, timeoutMs: Long = 15000): ByteArray {
        val p = port()
        val out = ByteArrayOutputStream(size)
        val buf = ByteArray(4096)
        var deadline = System.currentTimeMillis() + timeoutMs
        while (out.size() < size && System.currentTimeMillis() < deadline) {
            val request = minOf(buf.size, size - out.size())
            val temp = if (request == buf.size) buf else ByteArray(request)
            val n = try { p.read(temp, 200) } catch (_: Exception) { 0 }
            if (n > 0) {
                out.write(temp, 0, n)
                deadline = System.currentTimeMillis() + timeoutMs
            }
        }
        if (out.size() != size) throw IllegalStateException("Ricevuti ${out.size()} byte su $size attesi")
        return out.toByteArray()
    }

    private fun crc32(data: ByteArray): Long {
        val crc = CRC32()
        crc.update(data)
        return crc.value
    }

    @Synchronized
    fun readTrackCatalogBase64(): String {
        val p = port()
        try { p.purgeHwBuffers(true, false) } catch (_: Exception) {}
        status = "Lettura circuiti dal laptimer..."
        write("GTRK_GET\n".toByteArray(StandardCharsets.US_ASCII))
        val header = readLine(6000)
        val m = Regex("GTRK_DATA\\s+(\\d+)\\s+([0-9A-Fa-f]{8})").matchEntire(header)
            ?: throw IllegalStateException("Risposta GTRK non valida: ${if (header.isBlank()) "nessuna" else header}")
        val size = m.groupValues[1].toInt()
        val expected = m.groupValues[2].toLong(16)
        require(size in 8..60000) { "Dimensione catalogo non valida: $size" }
        val payload = readExact(size, 15000)
        val ending = readLine(4000)
        if (ending != "GTRK_END") throw IllegalStateException("Fine catalogo non valida: $ending")
        val actual = crc32(payload)
        if (actual != expected) throw IllegalStateException("CRC catalogo errato: %08X / %08X".format(actual, expected))
        status = "Catalogo letto: $size byte"
        return android.util.Base64.encodeToString(payload, android.util.Base64.NO_WRAP)
    }

    @Synchronized
    fun uploadTrackCatalogBase64(payloadB64: String): String {
        val payload = android.util.Base64.decode(payloadB64, android.util.Base64.DEFAULT)
        val crc = crc32(payload)
        val p = port()
        status = "Invio catalogo circuiti..."
        progress = 0f
        try { p.purgeHwBuffers(true, false) } catch (_: Exception) {}
        write("GTRK_BEGIN ${payload.size} %08X\n".format(crc).toByteArray(StandardCharsets.US_ASCII))
        val ready = readLine(5000)
        if (ready != "GTRK_READY") throw IllegalStateException("Laptimer non pronto: $ready")
        write(payload, 12000)
        progress = 1f
        val result = readLine(10000)
        if (!result.startsWith("GTRK_OK")) throw IllegalStateException("Trasferimento circuiti rifiutato: $result")
        status = "Circuiti inviati correttamente"
        return result
    }


}
