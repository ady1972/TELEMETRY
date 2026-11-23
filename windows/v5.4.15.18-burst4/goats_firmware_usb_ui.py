"""Firmware update page for the Windows Manager."""

from pathlib import Path
import sys

from PySide6.QtCore import QProcess, QStandardPaths, Qt
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QLabel, QLineEdit, QMessageBox, QPushButton, QTextEdit,
)
from serial.tools.list_ports import comports

from goats_firmware_usb import DOWNLOAD_VERSION, load_firmware, supports_usb_reset


MODEL_NAMES = {"GUITION_43": "Guition 4.3", "RLCD_MONO_42": "RLCD 4.2 monocromatico"}
FIRMWARE_CHANGELOGS = {
    ("GUITION_43", "RC3"): (
        "Aggiornamento firmware via USB dal Manager Windows.",
        "Caratteri in grassetto, inclusi i widget con font predefinito.",
    ),
    ("GUITION_43", "RC3.1"): (
        "Il cronometro si riarma anche quando il riepilogo di fine sessione si chiude da solo.",
    ),
    ("RLCD_MONO_42", "RC3"): (
        "Aggiornamento firmware via USB dal Manager Windows.",
        "Interfaccia con caratteri Roboto Condensed in grassetto.",
    ),
    ("RLCD_MONO_42", "RC3.1"): (
        "Azzeramento delle statistiche di velocità del giro alla chiusura della sessione.",
    ),
}


def populate_update_page(window, layout):
    port = QComboBox()
    refresh = QPushButton("Aggiorna elenco porte")
    boot_detect = QPushButton("Entra in BOOT e rileva")
    restart = QPushButton("Riavvia laptimer")
    model_label = QLabel()
    package = QLineEdit()
    package.setReadOnly(True)
    package.setPlaceholderText("File firmware")
    package_version = QLabel()
    changelog = QLabel()
    changelog.setTextFormat(Qt.PlainText)
    changelog.setWordWrap(True)
    changelog.hide()
    comparison = QLabel()
    comparison.setWordWrap(True)
    comparison.setTextFormat(Qt.PlainText)
    download = QPushButton(f"Scarica {DOWNLOAD_VERSION} da GitHub")
    browse = QPushButton("Apri file firmware locale")
    start = QPushButton("Aggiorna firmware via USB")
    log = QTextEdit()
    log.setReadOnly(True)
    process = QProcess(window)
    window.firmware_update_process = process
    process.setProcessChannelMode(QProcess.MergedChannels)
    script = Path(__file__).with_name("goats_firmware_usb.py")
    detected_model = None
    selected_version = None
    installed_matches = False
    running_action = None
    operation_output = bytearray()
    native_usb_ports = set()

    def update_controls():
        idle = process.state() == QProcess.NotRunning
        port.setEnabled(idle)
        refresh.setEnabled(idle)
        boot_detect.setEnabled(idle and bool(port.currentData()))
        restart.setEnabled(idle and detected_model is not None)
        download.setEnabled(idle and detected_model is not None)
        browse.setEnabled(idle and detected_model is not None)
        start.setEnabled(idle and detected_model is not None and bool(package.text()) and not installed_matches)
        model_label.setText(MODEL_NAMES.get(detected_model, "Modello da rilevare"))

    def show_comparison(message, color=None):
        comparison.setStyleSheet(
            f"color: {color}; font-size: 18pt; font-weight: 700;" if color else ""
        )
        comparison.setText(message)

    def clear_device():
        nonlocal detected_model, selected_version, installed_matches
        detected_model = None
        selected_version = None
        installed_matches = False
        package_version.clear()
        changelog.clear()
        changelog.hide()
        show_comparison("")
        package.clear()
        update_controls()

    def refresh_ports():
        selected = port.currentData()
        port.clear()
        devices = sorted(comports())
        native_usb_ports.clear()
        native_usb_ports.update(device.device for device in devices if supports_usb_reset(device))
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
        nonlocal detected_model, installed_matches
        read_output()
        if code or status != QProcess.NormalExit:
            log.append("Operazione interrotta. Controlla il log prima di riprovare.")
            if running_action == "compare":
                show_comparison("Verifica non riuscita. Il Manager riproverà prima di scrivere.")
        else:
            lines = operation_output.decode("utf-8", errors="replace").splitlines()
            result = next((line.removeprefix("GOATS_COMPARISON=") for line in lines
                           if line.startswith("GOATS_COMPARISON=")), "")
            if running_action in ("compare", "update") and result == "same":
                installed_matches = True
                show_comparison(
                    f"AGGIORNAMENTO NON NECESSARIO\nFirmware {selected_version} già installato.",
                    "#ff7474",
                )
            elif running_action == "compare":
                if result == "newer":
                    show_comparison("NUOVA VERSIONE FIRMWARE DISPONIBILE", "#59de8b")
                elif result == "older":
                    show_comparison("Il pacchetto selezionato è di una versione precedente.")
                elif result == "different":
                    show_comparison("Il firmware installato è diverso dal pacchetto selezionato.")
                else:
                    show_comparison("Verifica non riuscita. Il Manager riproverà prima di scrivere.")
            elif running_action in ("detect", "detect_usb_boot"):
                result = next((line.removeprefix("GOATS_MODEL=") for line in lines
                               if line.startswith("GOATS_MODEL=")), "")
                if result in MODEL_NAMES:
                    detected_model = result
                    log.append(f"Rilevato: {MODEL_NAMES[result]}")
            elif running_action == "download":
                result = next((line.removeprefix("GOATS_PACKAGE=") for line in lines
                               if line.startswith("GOATS_PACKAGE=")), "")
                if result:
                    set_package(Path(result))
            elif running_action in ("update", "restart"):
                clear_device()
        update_controls()

    def failed_to_start(error):
        if error == QProcess.FailedToStart:
            log.append(process.errorString())
            if running_action == "compare":
                show_comparison("Verifica non riuscita. Il Manager riproverà prima di scrivere.")
            update_controls()

    def enter_boot_and_detect():
        selected = port.currentData()
        action = "detect"
        if selected in native_usb_ports:
            message = (
                f"Rilevare il laptimer sulla porta {selected}?\n\n"
                "Se necessario il Manager lo riavvierà in modalità BOOT. "
                "Termina e salva eventuali sessioni prima di confermare."
            )
            if QMessageBox.question(window, "Modalità BOOT", message) != QMessageBox.Yes:
                return
            action = "detect_usb_boot"
        clear_device()
        launch(action, selected)

    def restart_device():
        launch("restart", detected_model, port.currentData())

    def download_package():
        cache = Path(QStandardPaths.writableLocation(QStandardPaths.CacheLocation)) / "firmware"
        launch("download", detected_model, str(cache))

    def set_package(manifest):
        nonlocal selected_version, installed_matches
        try:
            version, _ = load_firmware(detected_model, manifest)
        except (OSError, ValueError, KeyError) as exc:
            QMessageBox.warning(window, "Firmware incompatibile", str(exc))
            return
        selected_version = version
        installed_matches = False
        changes = FIRMWARE_CHANGELOGS.get((detected_model, version), ("Changelog non disponibile.",))
        changelog.setText(f"Changelog {version} · {MODEL_NAMES[detected_model]}\n"
                          + "\n".join(f"• {change}" for change in changes))
        changelog.show()
        show_comparison("Verifica del firmware installato…")
        package_version.setText(f"Firmware selezionato: {version}")
        package.setText(str(manifest))
        launch("compare", detected_model, str(manifest), port.currentData())

    def select_package():
        path, _ = QFileDialog.getOpenFileName(
            window, "Firmware GOATS", "", "Firmware GOATS (*.bin *.json)")
        if path:
            set_package(Path(path).with_suffix(".json"))

    def begin():
        message = (
            f"Installare {selected_version} su {MODEL_NAMES[detected_model]}, porta {port.currentData()}?\n\n"
            "Termina e salva eventuali sessioni. Il Manager può riavviare il laptimer "
            "in modalità BOOT sulla porta USB selezionata. Mantieni il cavo collegato."
        )
        if QMessageBox.question(window, "Conferma aggiornamento", message) == QMessageBox.Yes:
            launch("update", detected_model, package.text(), port.currentData())

    for widget in (QLabel("Porta USB"), port, refresh, boot_detect, restart, model_label, package_version, package,
                   download, browse, changelog, comparison, start, log):
        layout.addWidget(widget)
    process.readyReadStandardOutput.connect(read_output)
    process.finished.connect(finished)
    process.errorOccurred.connect(failed_to_start)
    port.currentIndexChanged.connect(clear_device)
    package.textChanged.connect(update_controls)
    refresh.clicked.connect(refresh_ports)
    boot_detect.clicked.connect(enter_boot_and_detect)
    restart.clicked.connect(restart_device)
    download.clicked.connect(download_package)
    browse.clicked.connect(select_package)
    start.clicked.connect(begin)
    refresh_ports()
