"""Firmware update page for the Windows Manager."""

from pathlib import Path
import sys

from PySide6.QtCore import QProcess, QStandardPaths
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QLabel, QLineEdit, QMessageBox, QPushButton, QTextEdit,
)
from serial.tools.list_ports import comports

from goats_firmware_usb import load_firmware


MODEL_NAMES = {"GUITION_43": "Guition 4.3", "RLCD_MONO_42": "RLCD 4.2 monocromatico"}


def populate_update_page(window, layout):
    port = QComboBox()
    refresh = QPushButton("Aggiorna elenco porte")
    detect = QPushButton("Rileva laptimer")
    model_label = QLabel()
    package = QLineEdit()
    package.setReadOnly(True)
    package.setPlaceholderText("Firmware RC3")
    download = QPushButton("Scarica firmware da GitHub")
    browse = QPushButton("Apri file firmware locale")
    start = QPushButton("Aggiorna firmware via USB")
    log = QTextEdit()
    log.setReadOnly(True)
    process = QProcess(window)
    window.firmware_update_process = process
    process.setProcessChannelMode(QProcess.MergedChannels)
    script = Path(__file__).with_name("goats_firmware_usb.py")
    detected_model = None
    running_action = None
    operation_output = bytearray()

    def update_controls():
        idle = process.state() == QProcess.NotRunning
        port.setEnabled(idle)
        refresh.setEnabled(idle)
        detect.setEnabled(idle and bool(port.currentData()))
        download.setEnabled(idle and detected_model is not None)
        browse.setEnabled(idle and detected_model is not None)
        start.setEnabled(idle and detected_model is not None and bool(package.text()))
        model_label.setText(MODEL_NAMES.get(detected_model, "Modello da rilevare"))

    def clear_device():
        nonlocal detected_model
        detected_model = None
        package.clear()
        update_controls()

    def refresh_ports():
        selected = port.currentData()
        port.clear()
        devices = sorted(comports())
        for device in devices:
            port.addItem(f"{device.device} — {device.description}", device.device)
        port.setCurrentIndex(port.findData(selected) if selected else -1)
        if len(devices) == 1 and port.currentIndex() == -1:
            port.setCurrentIndex(0)
        clear_device()

    def launch(action, *args):
        nonlocal running_action
        running_action = action
        operation_output.clear()
        log.clear()
        process.start(sys.executable, ["-X", "utf8", "-u", str(script), action, *args])
        update_controls()

    def read_output():
        chunk = bytes(process.readAllStandardOutput())
        operation_output.extend(chunk)
        log.insertPlainText(chunk.decode("utf-8", errors="replace"))
        log.ensureCursorVisible()

    def finished(code, status):
        nonlocal detected_model
        read_output()
        if code or status != QProcess.NormalExit:
            log.append("Operazione interrotta. Controlla il log prima di riprovare.")
        else:
            lines = operation_output.decode("utf-8", errors="replace").splitlines()
            if running_action == "detect":
                result = next((line.removeprefix("GOATS_MODEL=") for line in lines
                               if line.startswith("GOATS_MODEL=")), "")
                if result in MODEL_NAMES:
                    detected_model = result
                    log.append(f"Rilevato: {MODEL_NAMES[result]}")
            elif running_action == "download":
                result = next((line.removeprefix("GOATS_PACKAGE=") for line in lines
                               if line.startswith("GOATS_PACKAGE=")), "")
                if result:
                    package.setText(result)
            elif running_action == "update":
                clear_device()
        update_controls()

    def failed_to_start(error):
        if error == QProcess.FailedToStart:
            log.append(process.errorString())
            update_controls()

    def detect_device():
        clear_device()
        launch("detect", port.currentData())

    def download_package():
        cache = Path(QStandardPaths.writableLocation(QStandardPaths.CacheLocation)) / "firmware"
        launch("download", detected_model, str(cache))

    def select_package():
        path, _ = QFileDialog.getOpenFileName(
            window, "Firmware RC3", "", "Firmware RC3 (*.bin *.json)")
        if path:
            manifest = Path(path).with_suffix(".json")
            try:
                load_firmware(detected_model, manifest)
            except (OSError, ValueError, KeyError) as exc:
                QMessageBox.warning(window, "Firmware incompatibile", str(exc))
                return
            package.setText(str(manifest))

    def begin():
        message = (
            f"Aggiornare {MODEL_NAMES[detected_model]} sulla porta {port.currentData()}?\n\n"
            "Mantieni il cavo collegato fino al completamento."
        )
        if QMessageBox.question(window, "Conferma aggiornamento", message) == QMessageBox.Yes:
            launch("update", detected_model, package.text(), port.currentData())

    for widget in (QLabel("Porta USB"), port, refresh, detect, model_label, package,
                   download, browse, start, log):
        layout.addWidget(widget)
    process.readyReadStandardOutput.connect(read_output)
    process.finished.connect(finished)
    process.errorOccurred.connect(failed_to_start)
    port.currentIndexChanged.connect(clear_device)
    package.textChanged.connect(update_controls)
    refresh.clicked.connect(refresh_ports)
    detect.clicked.connect(detect_device)
    download.clicked.connect(download_package)
    browse.clicked.connect(select_package)
    start.clicked.connect(begin)
    refresh_ports()
