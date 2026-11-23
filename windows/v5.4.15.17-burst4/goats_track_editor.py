import os
import csv
import json
import re
import math
import statistics
import sys
import argparse
import ctypes
import urllib.parse
import urllib.request
import urllib.error
import struct
import time
import zlib
from datetime import datetime
from pathlib import Path

import serial
import urllib.request
import urllib.parse
from serial.tools import list_ports


# V5.4.11.6 QT WINDOWS FIX - isolate the bundled/venv PySide6 runtime.
def _goats_prepare_qt_windows():
    if os.name != "nt":
        return
    for key in ("QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH", "QML2_IMPORT_PATH"):
        os.environ.pop(key, None)
    for base in sys.path:
        pyside_dir = Path(base) / "PySide6"
        if not pyside_dir.is_dir():
            continue
        platforms = pyside_dir / "plugins" / "platforms"
        if platforms.is_dir():
            os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(platforms)
        os.environ["PATH"] = str(pyside_dir) + os.pathsep + os.environ.get("PATH", "")
        if hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(str(pyside_dir))
            except OSError:
                pass
        break

_goats_prepare_qt_windows()

from PySide6.QtCore import QObject, QUrl, Signal, Slot, Qt, QSettings
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QTableWidget, QTableWidgetItem, QAbstractItemView, QCheckBox, QLabel, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout,
    QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget, QMainWindow,
    QMessageBox, QPushButton, QSplitter, QStatusBar, QToolBar, QVBoxLayout,
    QWidget, QGroupBox, QHeaderView, QTabWidget, QProgressDialog
)
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from goats_formats import parse_any
from goats_store import SessionStore

from PySide6.QtCharts import (
    QBarCategoryAxis, QBarSeries, QBarSet, QChart, QChartView,
    QLineSeries, QValueAxis
)

APP_DIR = Path(__file__).resolve().parent
TRACKS_DIR = APP_DIR / "tracks"
TRACKS_DIR.mkdir(exist_ok=True)

def set_tracks_dir(folder):
    """Imposta la cartella circuiti usata da tutte le istanze TrackManager."""
    global TRACKS_DIR
    target = Path(folder).expanduser()
    target.mkdir(parents=True, exist_ok=True)
    TRACKS_DIR = target
    return TRACKS_DIR

DATA_DIR = APP_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "goats_rt_sessions.sqlite3"


def slugify(value: str) -> str:
    chars = []
    for ch in value.lower().strip():
        if ch.isalnum():
            chars.append(ch)
        elif ch in " -_":
            chars.append("_")
    result = "".join(chars)
    while "__" in result:
        result = result.replace("__", "_")
    return result.strip("_") or "nuovo_circuito"


def haversine_m(lat1, lon1, lat2, lon2):
    radius = 6371000.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    value = (
        math.sin(dp / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    )
    return 2 * radius * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def real_sector_count(track_or_sectors) -> int:
    """Numero di settori cronometrati reali.

    Nel formato GOATS/GTC3 ``sectors`` contiene esclusivamente le linee split
    intermedie. Con N linee intermedie il giro e' diviso in N+1 settori:
    finish->split1, ... , ultimo split->finish.
    Senza split intermedi il giro resta un unico settore logico.
    """
    if isinstance(track_or_sectors, dict):
        lines = track_or_sectors.get("sectors", []) or []
    else:
        lines = track_or_sectors or []
    return len(lines) + 1


class Bridge(QObject):
    point_selected = Signal(float, float)

    @Slot(float, float)
    def receivePoint(self, lat, lon):
        self.point_selected.emit(lat, lon)



class AssistNowDeviceDialog(QDialog):
    """Crea o modifica un profilo dispositivo AssistNow locale."""

    def __init__(self, parent=None, name="", description=""):
        super().__init__(parent)
        self.setWindowTitle("AssistNow - Profilo dispositivo")
        self.resize(620, 210)
        layout = QVBoxLayout(self)
        info = QLabel(
            "Ogni prototipo può avere credenziali AssistNow, chipcode e cache Predictive indipendenti. "
            "La descrizione serve solo nel Manager e non viene inviata a Thingstream."
        )
        info.setWordWrap(True)
        layout.addWidget(info)
        form = QFormLayout()
        self.name_edit = QLineEdit(str(name or ""))
        self.name_edit.setPlaceholderText("es. Telemetria V1.5 - M9N AK97")
        self.description_edit = QLineEdit(str(description or ""))
        self.description_edit.setPlaceholderText("es. prototipo RLCD, antenna esterna, kart test")
        form.addRow("Nome dispositivo:", self.name_edit)
        form.addRow("Descrizione:", self.description_edit)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept_validated)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _accept_validated(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "AssistNow", "Inserire un nome per il dispositivo.")
            return
        self.accept()

    def values(self):
        return self.name_edit.text().strip(), self.description_edit.text().strip()


class AssistNowRegistrationDialog(QDialog):
    """Registrazione ZTP per AssistNow (u-blox Gen9/Gen10)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AssistNow - Registrazione dispositivo ZTP")
        self.resize(800, 500)
        layout = QVBoxLayout(self)
        info = QLabel(
            "Inserisci il token del Device Profile Thingstream e le risposte UBX complete "
            "del ricevitore a SEC-UNIQID e MON-VER, codificate in esadecimale continuo. "
            "I dati possono essere memorizzati localmente nel profilo Windows del Manager."
        )
        info.setWordWrap(True)
        layout.addWidget(info)
        form = QFormLayout()
        self.token_edit = QLineEdit()
        self.token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_edit.setPlaceholderText("ZTP token del Device Profile Thingstream")
        self.uniqid_edit = QLineEdit()
        self.uniqid_edit.setPlaceholderText("B5622703... risposta UBX-SEC-UNIQID completa")
        self.monver_edit = QLineEdit()
        self.monver_edit.setPlaceholderText("B5620A04... risposta UBX-MON-VER completa")
        form.addRow("ZTP token:", self.token_edit)
        form.addRow("UBX-SEC-UNIQID:", self.uniqid_edit)
        form.addRow("UBX-MON-VER:", self.monver_edit)
        layout.addLayout(form)

        parent = self.parent()
        if parent is not None and hasattr(parent, "_current_assist_device"):
            dev = parent._current_assist_device() or {}
            self.token_edit.setText(str(dev.get("token", "") or ""))
            self.uniqid_edit.setText(str(dev.get("uniqid", "") or ""))
            self.monver_edit.setText(str(dev.get("monver", "") or ""))
        note = QLabel(
            "Comandi di polling u-blox (solo per ottenere le risposte): "
            "SEC-UNIQID = B5 62 27 03 00 00 2A A5; "
            "MON-VER = B5 62 0A 04 00 00 0E 34. "
            "Nei campi sopra va incollata la RISPOSTA completa, non il comando di polling."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        auto_row = QHBoxLayout()
        self.auto_status = QLabel("Porta USB: usa la COM selezionata nell'Editor Piste")
        self.auto_status.setWordWrap(True)
        auto_read = QPushButton("LEGGI DATI DAL M9N")
        auto_read.setToolTip("Invia GGID_GET al firmware GOATS RT V10.2+ e legge SEC-UNIQID e MON-VER direttamente dal M9N")
        auto_read.clicked.connect(self._read_from_laptimer)
        clear_saved = QPushButton("CANCELLA DATI SALVATI")
        clear_saved.clicked.connect(self._clear_saved)
        auto_row.addWidget(auto_read)
        auto_row.addWidget(clear_saved)
        auto_row.addWidget(self.auto_status, 1)
        layout.addLayout(auto_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _read_from_laptimer(self):
        parent = self.parent()
        if parent is None or not hasattr(parent, "read_gnss_identity"):
            QMessageBox.critical(self, "AssistNow", "Funzione di lettura GNSS non disponibile.")
            return
        try:
            uniqid, monver = parent.read_gnss_identity()
            self.uniqid_edit.setText(uniqid)
            self.monver_edit.setText(monver)
            port = parent.port_combo.currentData() if hasattr(parent, "port_combo") else ""
            self.auto_status.setText(f"M9N letto correttamente da {port or 'USB'}")
            QMessageBox.information(
                self, "AssistNow - M9N",
                "Identità GNSS letta correttamente.\n\n"
                "I campi SEC-UNIQID e MON-VER sono stati compilati automaticamente."
            )
        except Exception as exc:
            self.auto_status.setText("Lettura M9N non riuscita")
            QMessageBox.critical(self, "AssistNow - Lettura M9N", str(exc))

    def _clear_saved(self):
        parent = self.parent()
        if parent is not None and hasattr(parent, "clear_assistnow_credentials"):
            parent.clear_assistnow_credentials(show_message=False)
        self.token_edit.clear()
        self.uniqid_edit.clear()
        self.monver_edit.clear()
        self.auto_status.setText("Dati AssistNow salvati cancellati")

    @staticmethod
    def _clean_hex(value):
        return re.sub(r"[^0-9A-Fa-f]", "", value or "").upper()

    def values(self):
        return (
            self.token_edit.text().strip(),
            self._clean_hex(self.uniqid_edit.text()),
            self._clean_hex(self.monver_edit.text()),
        )


class SessionSelectionDialog(QDialog):
    """Permette di scegliere quali sessioni esportare."""

    def __init__(self, sessions, parent=None):
        super().__init__(parent)
        self.sessions = sessions
        self.setWindowTitle("Seleziona sessioni da scaricare")
        self.resize(860, 430)

        layout = QVBoxLayout(self)

        info = QLabel(
            "Seleziona le sessioni da esportare. "
            "L'archivio viene letto dal laptimer, ma saranno salvate "
            "solo le righe spuntate."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self.table = QTableWidget(len(sessions), 7)
        self.table.setHorizontalHeaderLabels([
            "Scarica", "Data", "Ora", "Circuito",
            "Giri", "Best Lap", "Durata"
        ])
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table.verticalHeader().setVisible(False)

        for row, session in enumerate(sessions):
            checkbox = QCheckBox()
            checkbox.setChecked(True)
            container = QWidget()
            container_layout = QHBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            container_layout.addWidget(checkbox)
            self.table.setCellWidget(row, 0, container)
            self.table.setItem(row, 1, QTableWidgetItem(session["date"]))
            self.table.setItem(row, 2, QTableWidgetItem(session["time"]))
            self.table.setItem(
                row, 3, QTableWidgetItem(session["track_name"])
            )
            self.table.setItem(
                row, 4, QTableWidgetItem(str(session["lap_count"]))
            )
            self.table.setItem(
                row, 5, QTableWidgetItem(session["best_lap"])
            )
            self.table.setItem(
                row, 6, QTableWidgetItem(session["duration"])
            )

        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        controls = QHBoxLayout()
        select_all = QPushButton("SELEZIONA TUTTE")
        select_all.clicked.connect(lambda: self._set_all(True))
        clear_all = QPushButton("DESELEZIONA TUTTE")
        clear_all.clicked.connect(lambda: self._set_all(False))
        controls.addWidget(select_all)
        controls.addWidget(clear_all)
        controls.addStretch()
        layout.addLayout(controls)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(
            QDialogButtonBox.StandardButton.Ok
        ).setText("SCARICA SELEZIONATE")
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _checkbox(self, row):
        container = self.table.cellWidget(row, 0)
        return container.findChild(QCheckBox) if container else None

    def _set_all(self, checked):
        for row in range(self.table.rowCount()):
            checkbox = self._checkbox(row)
            if checkbox:
                checkbox.setChecked(checked)

    def selected_sessions(self):
        selected = []
        for row, session in enumerate(self.sessions):
            checkbox = self._checkbox(row)
            if checkbox and checkbox.isChecked():
                selected.append(session)
        return selected

    def _accept_if_valid(self):
        if not self.selected_sessions():
            QMessageBox.warning(
                self,
                "Nessuna sessione",
                "Seleziona almeno una sessione da scaricare."
            )
            return
        self.accept()



class SessionAnalysisDialog(QDialog):
    """Archivio e analisi delle sessioni esportate dal GOATS RT."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GOATS RT Analysis")
        self.resize(1220, 780)
        self.sessions = []
        self.current_folder = None

        root = QVBoxLayout(self)

        top = QHBoxLayout()
        self.folder_label = QLabel("Nessuna cartella caricata")
        self.folder_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        open_button = QPushButton("APRI CARTELLA SESSIONI")
        open_button.clicked.connect(self.open_folder)
        archive_button = QPushButton("APRI ARCHIVIO JSON")
        archive_button.clicked.connect(self.open_archive)
        top.addWidget(open_button)
        top.addWidget(archive_button)
        top.addWidget(self.folder_label, 1)
        root.addLayout(top)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        self._build_session_tab()
        self._build_compare_tab()

        close_buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close
        )
        close_buttons.rejected.connect(self.reject)
        close_buttons.clicked.connect(self.close)
        root.addWidget(close_buttons)

    def _build_session_tab(self):
        page = QWidget()
        layout = QHBoxLayout(page)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Sessioni disponibili"))

        self.session_table = QTableWidget(0, 6)
        self.session_table.setHorizontalHeaderLabels([
            "Data", "Ora", "Circuito", "Giri", "Best", "Durata"
        ])
        self.session_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.session_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.session_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.session_table.verticalHeader().setVisible(False)
        self.session_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.session_table.horizontalHeader().setStretchLastSection(True)
        self.session_table.currentCellChanged.connect(
            self._session_selection_changed
        )
        left_layout.addWidget(self.session_table, 1)
        layout.addWidget(left, 4)

        right = QWidget()
        right_layout = QVBoxLayout(right)

        self.summary_group = QGroupBox("Riepilogo sessione")
        summary_layout = QFormLayout(self.summary_group)
        self.summary_track = QLabel("--")
        self.summary_laps = QLabel("0")
        self.summary_best = QLabel("--:--.---")
        self.summary_average = QLabel("--:--.---")
        self.summary_consistency = QLabel("--")
        self.summary_vmax = QLabel("0.0 km/h")
        self.summary_vavg = QLabel("0.0 km/h")
        self.summary_quality = QLabel("--")
        summary_layout.addRow("Circuito", self.summary_track)
        summary_layout.addRow("Giri validi", self.summary_laps)
        summary_layout.addRow("Best Lap", self.summary_best)
        summary_layout.addRow("Media giri", self.summary_average)
        summary_layout.addRow("Costanza", self.summary_consistency)
        summary_layout.addRow("Velocità massima", self.summary_vmax)
        summary_layout.addRow("Velocità media", self.summary_vavg)
        summary_layout.addRow("Qualità GPS", self.summary_quality)
        right_layout.addWidget(self.summary_group)

        self.detail_tabs = QTabWidget()

        laps_page = QWidget()
        laps_layout = QVBoxLayout(laps_page)
        self.lap_table = QTableWidget(0, 7)
        self.lap_table.setHorizontalHeaderLabels([
            "Giro", "Tempo", "Δ Best", "V max", "V media",
            "Scostamento", "Esito"
        ])
        self.lap_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.lap_table.verticalHeader().setVisible(False)
        self.lap_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        laps_layout.addWidget(self.lap_table)
        self.detail_tabs.addTab(laps_page, "Giri")

        self.lap_chart_view = QChartView()
        self.lap_chart_view.setRenderHint(
            self.lap_chart_view.renderHints()
        )
        self.detail_tabs.addTab(self.lap_chart_view, "Tempi giro")

        self.speed_chart_view = QChartView()
        self.detail_tabs.addTab(self.speed_chart_view, "Velocità")

        self.trace_map_view = QWebEngineView()
        self.detail_tabs.addTab(
            self.trace_map_view, "Mappa satellitare"
        )

        right_layout.addWidget(self.detail_tabs, 1)
        layout.addWidget(right, 7)

        self.tabs.addTab(page, "Analisi sessione")

    def _build_compare_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        selectors = QHBoxLayout()
        self.compare_a = QComboBox()
        self.compare_b = QComboBox()
        self.compare_a.currentIndexChanged.connect(self.update_compare)
        self.compare_b.currentIndexChanged.connect(self.update_compare)
        selectors.addWidget(QLabel("Sessione A"))
        selectors.addWidget(self.compare_a, 1)
        selectors.addWidget(QLabel("Sessione B"))
        selectors.addWidget(self.compare_b, 1)
        layout.addLayout(selectors)

        self.compare_table = QTableWidget(6, 4)
        self.compare_table.setHorizontalHeaderLabels([
            "Indicatore", "Sessione A", "Sessione B", "Differenza B - A"
        ])
        self.compare_table.setVerticalHeaderLabels([
            "", "", "", "", "", ""
        ])
        self.compare_table.verticalHeader().setVisible(False)
        self.compare_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.compare_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.compare_table)

        self.compare_chart_view = QChartView()
        layout.addWidget(self.compare_chart_view, 1)

        note = QLabel(
            "Il confronto usa i dati disponibili nell'archivio attuale: "
            "tempi giro e velocità aggregate. La telemetria GPS punto per "
            "punto richiederà una futura estensione del firmware."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        self.tabs.addTab(page, "Confronto sessioni")

    @staticmethod
    def _session_label(session):
        return (
            f"{session.get('date', '--')} {session.get('time', '--')} - "
            f"{session.get('track_name', 'Circuito')} "
            f"({session.get('lap_count', len(session.get('laps', [])))} giri)"
        )

    @staticmethod
    def _format_ms(milliseconds):
        if milliseconds is None:
            return "--:--.---"
        milliseconds = int(round(milliseconds))
        minutes = milliseconds // 60000
        seconds = (milliseconds // 1000) % 60
        millis = milliseconds % 1000
        return f"{minutes:02d}:{seconds:02d}.{millis:03d}"

    @staticmethod
    def _valid_laps(session):
        return [
            lap for lap in session.get("laps", [])
            if int(lap.get("lap_time_ms", 0)) > 0
        ]

    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Seleziona cartella sessioni GOATS RT"
        )
        if not folder:
            return
        try:
            sessions = self._load_folder(Path(folder))
            self._set_sessions(sessions, Path(folder))
        except Exception as exc:
            QMessageBox.critical(self, "Errore analisi", str(exc))

    def open_archive(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Apri archivio sessioni",
            "",
            "Archivio GOATS RT (*.json);;Tutti i file (*.*)",
        )
        if not path:
            return
        try:
            sessions = self._load_json_file(Path(path))
            self._set_sessions(sessions, Path(path).parent)
        except Exception as exc:
            QMessageBox.critical(self, "Errore analisi", str(exc))

    def _load_folder(self, folder):
        archive = folder / "goats_sessions_archive.json"
        if archive.exists():
            return self._load_json_file(archive)

        sessions = []
        for path in sorted(folder.glob("session_*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("format") == "GOATS_RT_SESSION":
                sessions.append(data)
        if not sessions:
            for path in folder.rglob("goats_sessions_archive.json"):
                sessions.extend(self._load_json_file(path))
        if not sessions:
            raise ValueError(
                "Nella cartella non sono stati trovati file sessione validi."
            )
        return sessions

    @staticmethod
    def _load_json_file(path):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("format") == "GOATS_RT_SESSION_ARCHIVE":
            return list(data.get("sessions", []))
        if data.get("format") == "GOATS_RT_SESSION":
            return [data]
        raise ValueError("Il file JSON non è un archivio GOATS RT valido.")

    def _set_sessions(self, sessions, folder):
        self.sessions = sorted(
            sessions,
            key=lambda item: (
                item.get("date", ""),
                item.get("time", ""),
                int(item.get("session_id", 0)),
            ),
            reverse=True,
        )
        self.current_folder = folder
        self.folder_label.setText(str(folder))

        self.session_table.setRowCount(len(self.sessions))
        for row, session in enumerate(self.sessions):
            values = [
                session.get("date", "--"),
                session.get("time", "--"),
                session.get("track_name", "Circuito"),
                str(session.get("lap_count", len(session.get("laps", [])))),
                session.get("best_lap", self._format_ms(
                    session.get("best_lap_ms", 0)
                )),
                session.get("duration", "--:--"),
            ]
            for col, value in enumerate(values):
                self.session_table.setItem(
                    row, col, QTableWidgetItem(str(value))
                )

        self.compare_a.blockSignals(True)
        self.compare_b.blockSignals(True)
        self.compare_a.clear()
        self.compare_b.clear()
        for session in self.sessions:
            label = self._session_label(session)
            self.compare_a.addItem(label)
            self.compare_b.addItem(label)
        if len(self.sessions) > 1:
            self.compare_b.setCurrentIndex(1)
        self.compare_a.blockSignals(False)
        self.compare_b.blockSignals(False)

        if self.sessions:
            self.session_table.selectRow(0)
            self.show_session(0)
        else:
            self.clear_session()
        self.update_compare()

    def _session_selection_changed(
        self, current_row, current_column, previous_row, previous_column
    ):
        if current_row >= 0:
            self.show_session(current_row)

    def clear_session(self):
        self.summary_track.setText("--")
        self.summary_laps.setText("0")
        self.summary_best.setText("--:--.---")
        self.summary_average.setText("--:--.---")
        self.summary_consistency.setText("--")
        self.summary_vmax.setText("0.0 km/h")
        self.summary_vavg.setText("0.0 km/h")
        self.summary_quality.setText("--")
        self.lap_table.setRowCount(0)
        self.lap_chart_view.setChart(QChart())
        self.speed_chart_view.setChart(QChart())
        self.trace_map_view.setHtml(
            "<html><body style='background:#111;color:white;"
            "font-family:Arial;padding:30px'>"
            "<h2>Nessuna traccia GPS disponibile</h2></body></html>"
        )

    def show_session(self, index):
        if index < 0 or index >= len(self.sessions):
            self.clear_session()
            return
        session = self.sessions[index]
        laps = self._valid_laps(session)
        lap_times = [int(lap["lap_time_ms"]) for lap in laps]
        best_ms = min(lap_times) if lap_times else 0
        average_ms = statistics.fmean(lap_times) if lap_times else 0
        std_ms = statistics.pstdev(lap_times) if len(lap_times) > 1 else 0
        consistency_pct = (
            max(0.0, 100.0 - (std_ms / average_ms * 100.0))
            if average_ms else 0.0
        )

        self.summary_track.setText(session.get("track_name", "Circuito"))
        self.summary_laps.setText(str(len(laps)))
        self.summary_best.setText(self._format_ms(best_ms))
        self.summary_average.setText(self._format_ms(average_ms))
        self.summary_consistency.setText(
            f"{consistency_pct:.1f}%  (σ {std_ms / 1000.0:.3f} s)"
        )
        self.summary_vmax.setText(
            f"{float(session.get('max_speed_kmh', 0.0)):.1f} km/h"
        )
        self.summary_vavg.setText(
            f"{float(session.get('average_speed_kmh', 0.0)):.1f} km/h"
        )
        self.summary_quality.setText(
            f"HDOP {float(session.get('average_hdop', 0.0)):.2f} - "
            f"SAT {float(session.get('average_satellites', 0.0)):.1f}"
        )

        self.lap_table.setRowCount(len(laps))
        for row, lap in enumerate(laps):
            lap_ms = int(lap.get("lap_time_ms", 0))
            delta_ms = lap_ms - best_ms
            deviation_pct = (
                delta_ms / best_ms * 100.0 if best_ms else 0.0
            )
            result = "BEST" if delta_ms == 0 else (
                "REGOLARE" if deviation_pct <= 2.0 else "DA MIGLIORARE"
            )
            values = [
                str(lap.get("number", row + 1)),
                self._format_ms(lap_ms),
                f"+{delta_ms / 1000.0:.3f} s",
                f"{float(lap.get('max_speed_kmh', 0.0)):.1f}",
                f"{float(lap.get('average_speed_kmh', 0.0)):.1f}",
                f"{deviation_pct:.2f}%",
                result,
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col in (0, 2, 3, 4, 5):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.lap_table.setItem(row, col, item)

        self._build_lap_chart(session, laps, best_ms)
        self._build_speed_chart(session, laps)
        self._build_trace_map(session, laps, best_ms)

    def _build_lap_chart(self, session, laps, best_ms):
        chart = QChart()
        chart.setTitle(
            f"Tempi giro - {session.get('track_name', 'Circuito')}"
        )
        series = QLineSeries()
        series.setName("Tempo giro")

        min_value = None
        max_value = None
        for index, lap in enumerate(laps, start=1):
            seconds = int(lap.get("lap_time_ms", 0)) / 1000.0
            series.append(index, seconds)
            min_value = seconds if min_value is None else min(min_value, seconds)
            max_value = seconds if max_value is None else max(max_value, seconds)

        chart.addSeries(series)
        axis_x = QValueAxis()
        axis_x.setTitleText("Giro")
        axis_x.setLabelFormat("%d")
        axis_x.setRange(1, max(1, len(laps)))
        axis_x.setTickCount(min(max(2, len(laps)), 12))

        axis_y = QValueAxis()
        axis_y.setTitleText("Secondi")
        if min_value is None:
            axis_y.setRange(0, 1)
        else:
            margin = max(0.5, (max_value - min_value) * 0.2)
            axis_y.setRange(max(0, min_value - margin), max_value + margin)
        axis_y.setLabelFormat("%.1f")

        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_x)
        series.attachAxis(axis_y)
        chart.legend().setVisible(True)
        self.lap_chart_view.setChart(chart)

    def _build_speed_chart(self, session, laps):
        chart = QChart()
        chart.setTitle(
            f"Velocità per giro - {session.get('track_name', 'Circuito')}"
        )
        max_set = QBarSet("V max")
        avg_set = QBarSet("V media")
        categories = []

        for index, lap in enumerate(laps, start=1):
            max_set.append(float(lap.get("max_speed_kmh", 0.0)))
            avg_set.append(float(lap.get("average_speed_kmh", 0.0)))
            categories.append(str(index))

        series = QBarSeries()
        series.append(max_set)
        series.append(avg_set)
        chart.addSeries(series)

        axis_x = QBarCategoryAxis()
        axis_x.append(categories or ["-"])
        axis_x.setTitleText("Giro")
        axis_y = QValueAxis()
        axis_y.setTitleText("km/h")
        axis_y.setRange(
            0,
            max(
                10.0,
                float(session.get("max_speed_kmh", 0.0)) * 1.15,
            ),
        )

        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_x)
        series.attachAxis(axis_y)
        self.speed_chart_view.setChart(chart)

    def _build_trace_map(self, session, laps, best_ms):
        traced_laps = [
            lap for lap in laps if len(lap.get("trace", [])) >= 2
        ]
        if not traced_laps:
            self.trace_map_view.setHtml(
                "<html><body style='background:#111;color:white;"
                "font-family:Arial;padding:30px'>"
                "<h2>Questa sessione non contiene traiettorie GPS.</h2>"
                "<p>Le tracce sono disponibili con firmware V6.0 o successivo."
                "</p></body></html>"
            )
            return

        colors = [
            "#00ff88", "#ff5252", "#40c4ff", "#ffd740",
            "#e040fb", "#ff9100", "#69f0ae", "#ffffff",
        ]
        layers_js = []
        bounds_points = []
        for index, lap in enumerate(traced_laps):
            points = []
            for point in lap["trace"]:
                lat = float(point["latitude"])
                lon = float(point["longitude"])
                speed = float(point.get("speed_kmh", 0.0))
                elapsed = int(point.get("elapsed_ms", 0))
                points.append([lat, lon, speed, elapsed])
                bounds_points.append([lat, lon])
            color = "#00ff66" if int(lap["lap_time_ms"]) == best_ms else colors[index % len(colors)]
            name = (
                f"Giro {lap.get('number', index + 1)} - "
                f"{lap.get('lap_time', '')}"
                + (" BEST" if int(lap["lap_time_ms"]) == best_ms else "")
            )
            layers_js.append(
                "addLap(" + json.dumps(name) + ","
                + json.dumps(points) + "," + json.dumps(color) + ");"
            )

        center = bounds_points[0]
        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
html,body,#map{{height:100%;margin:0;background:#111}}
.info{{background:rgba(10,12,16,.92);color:white;padding:8px 10px;
font:13px Arial;border-radius:6px}}
.leaflet-control-layers{{font:13px Arial}}
</style>
<link rel="stylesheet"
 href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
</head>
<body>
<div id="map"></div>
<script>
const map=L.map('map').setView([{center[0]},{center[1]}],18);
L.tileLayer(
 'https://server.arcgisonline.com/ArcGIS/rest/services/' +
 'World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}',
 {{maxZoom:20,attribution:'Tiles &copy; Esri'}}
).addTo(map);
const overlays={{}};
const all=[];
function fmt(ms){{
 const s=Math.floor(ms/1000), m=Math.floor(s/60);
 return String(m).padStart(2,'0')+':' +
        String(s%60).padStart(2,'0')+'.' +
        String(ms%1000).padStart(3,'0');
}}
function addLap(name,points,color){{
 const coords=points.map(p=>[p[0],p[1]]);
 const line=L.polyline(coords,{{color:color,weight:4,opacity:.88}});
 line.bindTooltip(name);
 points.forEach((p,i)=>{{
   if(i%10===0){{
     L.circleMarker([p[0],p[1]],{{radius:3,color:color,fillOpacity:.9}})
      .bindPopup('<b>'+name+'</b><br>Tempo: '+fmt(p[3])+
                 '<br>Velocita: '+p[2].toFixed(1)+' km/h')
      .addTo(line);
   }}
 }});
 line.addTo(map); overlays[name]=line; all.push(...coords);
}}
{''.join(layers_js)}
L.control.layers(null,overlays,{{collapsed:false}}).addTo(map);
if(all.length) map.fitBounds(all,{{padding:[20,20]}});
const info=L.control({{position:'bottomleft'}});
info.onAdd=()=>{{const d=L.DomUtil.create('div','info');
d.innerHTML='<b>{session.get("track_name","Circuito")}</b><br>'+
'{len(traced_laps)} traiettorie disponibili';return d;}};
info.addTo(map);
</script>
</body>
</html>"""
        self.trace_map_view.setHtml(html)

    @staticmethod
    def _metrics(session):
        laps = SessionAnalysisDialog._valid_laps(session)
        times = [int(lap["lap_time_ms"]) for lap in laps]
        best = min(times) if times else 0
        average = statistics.fmean(times) if times else 0.0
        std = statistics.pstdev(times) if len(times) > 1 else 0.0
        consistency = (
            max(0.0, 100.0 - std / average * 100.0)
            if average else 0.0
        )
        return {
            "laps": len(times),
            "best": best,
            "average": average,
            "consistency": consistency,
            "vmax": float(session.get("max_speed_kmh", 0.0)),
            "vavg": float(session.get("average_speed_kmh", 0.0)),
        }

    def update_compare(self):
        if not self.sessions:
            self.compare_table.clearContents()
            self.compare_chart_view.setChart(QChart())
            return

        ia = self.compare_a.currentIndex()
        ib = self.compare_b.currentIndex()
        if ia < 0 or ib < 0:
            return
        a = self.sessions[ia]
        b = self.sessions[ib]
        ma = self._metrics(a)
        mb = self._metrics(b)

        rows = [
            ("Giri validi", ma["laps"], mb["laps"], mb["laps"] - ma["laps"]),
            (
                "Best Lap",
                self._format_ms(ma["best"]),
                self._format_ms(mb["best"]),
                f"{(mb['best'] - ma['best']) / 1000.0:+.3f} s",
            ),
            (
                "Media giri",
                self._format_ms(ma["average"]),
                self._format_ms(mb["average"]),
                f"{(mb['average'] - ma['average']) / 1000.0:+.3f} s",
            ),
            (
                "Costanza",
                f"{ma['consistency']:.1f}%",
                f"{mb['consistency']:.1f}%",
                f"{mb['consistency'] - ma['consistency']:+.1f}%",
            ),
            (
                "Velocità massima",
                f"{ma['vmax']:.1f} km/h",
                f"{mb['vmax']:.1f} km/h",
                f"{mb['vmax'] - ma['vmax']:+.1f} km/h",
            ),
            (
                "Velocità media",
                f"{ma['vavg']:.1f} km/h",
                f"{mb['vavg']:.1f} km/h",
                f"{mb['vavg'] - ma['vavg']:+.1f} km/h",
            ),
        ]

        for row, values in enumerate(rows):
            for col, value in enumerate(values):
                self.compare_table.setItem(
                    row, col, QTableWidgetItem(str(value))
                )

        self._build_compare_chart(a, b)

    def _build_compare_chart(self, session_a, session_b):
        chart = QChart()
        chart.setTitle("Confronto tempi giro")

        for session, name in (
            (session_a, "Sessione A"),
            (session_b, "Sessione B"),
        ):
            series = QLineSeries()
            series.setName(name)
            for index, lap in enumerate(
                self._valid_laps(session), start=1
            ):
                series.append(
                    index, int(lap.get("lap_time_ms", 0)) / 1000.0
                )
            chart.addSeries(series)

        all_laps = (
            self._valid_laps(session_a) + self._valid_laps(session_b)
        )
        values = [
            int(lap.get("lap_time_ms", 0)) / 1000.0
            for lap in all_laps
        ]
        max_laps = max(
            len(self._valid_laps(session_a)),
            len(self._valid_laps(session_b)),
            1,
        )

        axis_x = QValueAxis()
        axis_x.setTitleText("Giro")
        axis_x.setLabelFormat("%d")
        axis_x.setRange(1, max_laps)
        axis_x.setTickCount(min(max_laps + 1, 12))

        axis_y = QValueAxis()
        axis_y.setTitleText("Secondi")
        if values:
            margin = max(0.5, (max(values) - min(values)) * 0.2)
            axis_y.setRange(
                max(0, min(values) - margin), max(values) + margin
            )
        else:
            axis_y.setRange(0, 1)

        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        for series in chart.series():
            series.attachAxis(axis_x)
            series.attachAxis(axis_y)
        self.compare_chart_view.setChart(chart)


class TrackManager(QMainWindow):
    def __init__(self, mode="tracks"):
        super().__init__()
        self.mode = mode if mode in ("tracks", "sessions", "assistnow", "all") else "tracks"
        titles = {
            "tracks": "GOATS RT Manager V5.4.13.6 - Circuiti",
            "sessions": "GOATS RT Manager V5.4.13.6 - Sessioni USB",
            "assistnow": "GOATS RT Manager V5.4.13.6 - AssistNow",
            "all": "GOATS RT Manager V5.4.13.6 - Strumenti completi",
        }
        self.setWindowTitle(titles[self.mode])
        self.resize(1360, 820)

        self.current_path = None
        self.finish_a = None
        self.finish_b = None
        self.sectors = []
        self.drawing_mode = None
        self.pending_point = None
        self.files = []
        self.assist_settings = QSettings("GOATS RT", "Manager")
        self.assist_last_diag = ""
        self.assist_devices = []
        self.assist_current_device_id = ""
        self._assist_loaded_device_id = ""
        self._assist_switching = False

        self.build_ui()
        if self.mode in ("tracks", "all"):
            self.load_map()
            self.refresh_tracks()
        self.refresh_ports()

    def build_ui(self):
        toolbar = QToolBar("Azioni")
        self.track_toolbar = toolbar
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        actions = [
            ("Nuovo", self.new_track),
            ("Salva", self.save_track),
            ("Elimina dal Manager", self.delete_track),
            ("Importa JSON", self.import_json),
            ("Esporta pacchetto", self.export_catalog),
        ]
        for label, callback in actions:
            action = QAction(label, self)
            action.triggered.connect(callback)
            toolbar.addAction(action)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        search_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(
            "Cerca circuito o luogo, es. Ottobiano Motorsport"
        )
        self.search_edit.returnPressed.connect(self.search_osm)
        search_button = QPushButton("Cerca su OpenStreetMap")
        self.search_button = search_button
        search_button.clicked.connect(self.search_osm)

        search_row.addWidget(QLabel("Ricerca:"))
        search_row.addWidget(self.search_edit, 1)
        search_row.addWidget(search_button)
        root.addLayout(search_row)

        # ------------------------------------------------------------
        # COMUNE: selezione porta USB
        # ------------------------------------------------------------
        self.usb_common_widget = QWidget()
        usb_common = QHBoxLayout(self.usb_common_widget)
        usb_common.setContentsMargins(0, 0, 0, 0)
        usb_common.setSpacing(8)
        usb_common.addWidget(QLabel("Laptimer USB:"))
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(230)
        self.port_combo.setMaximumWidth(330)
        refresh_port_button = QPushButton("AGGIORNA PORTE")
        self.refresh_port_button = refresh_port_button
        refresh_port_button.clicked.connect(self.refresh_ports)
        usb_common.addWidget(self.port_combo)
        usb_common.addWidget(refresh_port_button)
        usb_common.addStretch()
        root.addWidget(self.usb_common_widget)

        # ------------------------------------------------------------
        # CIRCUITI: comandi dedicati
        # ------------------------------------------------------------
        self.track_usb_widget = QWidget()
        track_usb = QHBoxLayout(self.track_usb_widget)
        track_usb.setContentsMargins(0, 0, 0, 0)
        track_usb.setSpacing(8)

        send_usb_button = QPushButton("INVIA CIRCUITI SELEZIONATI")
        self.send_usb_button = send_usb_button
        send_usb_button.setToolTip(
            "Invia i circuiti selezionati facendo il merge con quelli già presenti sul laptimer"
        )
        send_usb_button.clicked.connect(self.send_to_laptimer)

        download_tracks_button = QPushButton("IMPORTA CIRCUITI DAL LAPTIMER")
        self.download_tracks_button = download_tracks_button
        download_tracks_button.setToolTip(
            "Legge i circuiti presenti nel laptimer e permette di selezionare quelli da importare"
        )
        download_tracks_button.clicked.connect(self.download_tracks_from_laptimer)

        delete_local_button = QPushButton("ELIMINA DAL DATABASE MANAGER")
        self.delete_local_button = delete_local_button
        delete_local_button.setToolTip(
            "Elimina dal database locale del Manager i circuiti selezionati; non modifica il laptimer"
        )
        delete_local_button.clicked.connect(self.delete_tracks_from_manager)

        delete_usb_button = QPushButton("ELIMINA SELEZIONATO DAL LAPTIMER")
        self.delete_usb_button = delete_usb_button
        delete_usb_button.clicked.connect(self.delete_selected_from_laptimer)

        clear_usb_button = QPushButton("SVUOTA LAPTIMER")
        self.clear_usb_button = clear_usb_button
        clear_usb_button.clicked.connect(self.clear_laptimer)

        track_usb.addWidget(send_usb_button)
        track_usb.addWidget(download_tracks_button)
        track_usb.addWidget(delete_local_button)
        track_usb.addWidget(delete_usb_button)
        track_usb.addWidget(clear_usb_button)
        track_usb.addStretch()
        root.addWidget(self.track_usb_widget)

        # ------------------------------------------------------------
        # SESSIONI USB: pannello compatto dedicato
        # ------------------------------------------------------------
        self.sessions_usb_widget = QWidget()
        sessions_usb = QHBoxLayout(self.sessions_usb_widget)
        sessions_usb.setContentsMargins(0, 0, 0, 0)
        sessions_usb.setSpacing(10)

        download_sessions_button = QPushButton("SCARICA SESSIONI")
        self.download_sessions_button = download_sessions_button
        download_sessions_button.clicked.connect(self.download_sessions)

        analysis_button = QPushButton("ANALIZZA SESSIONI")
        self.analysis_button = analysis_button
        analysis_button.clicked.connect(self.open_session_analysis)

        clear_sessions_button = QPushButton("CANCELLA SESSIONI DAL LAPTIMER")
        self.clear_sessions_button = clear_sessions_button
        clear_sessions_button.clicked.connect(self.clear_sessions_laptimer)

        usb_sd_button = QPushButton("ATTIVA USB SD")
        self.usb_sd_button = usb_sd_button
        usb_sd_button.setToolTip(
            "Passa la microSD del laptimer a Windows e importa direttamente i CSV"
        )
        usb_sd_button.clicked.connect(self.activate_usb_sd_from_manager)

        sessions_usb.addWidget(usb_sd_button)
        sessions_usb.addWidget(download_sessions_button)
        sessions_usb.addWidget(analysis_button)
        sessions_usb.addWidget(clear_sessions_button)
        sessions_usb.addStretch()
        root.addWidget(self.sessions_usb_widget)

        # ------------------------------------------------------------
        # ASSISTNOW: pannello compatto a due righe, senza intestazione
        # "AssistNow Predictive" duplicata.
        # ------------------------------------------------------------
        self.assist_widget = QWidget()
        assist_layout = QVBoxLayout(self.assist_widget)
        assist_layout.setContentsMargins(0, 0, 0, 0)
        assist_layout.setSpacing(8)

        # Gestione multi-dispositivo AssistNow. Ogni profilo mantiene
        # credenziali ZTP/chipcode/cache separati e una descrizione locale.
        assist_device_row = QHBoxLayout()
        assist_device_row.setSpacing(8)
        self.assist_device_combo = QComboBox()
        self.assist_device_combo.setMinimumWidth(300)
        self.assist_device_combo.currentIndexChanged.connect(self._on_assist_device_changed)
        assist_new_device = QPushButton("NUOVO DISPOSITIVO")
        assist_new_device.clicked.connect(self.add_assistnow_device)
        assist_edit_device = QPushButton("MODIFICA")
        assist_edit_device.clicked.connect(self.edit_assistnow_device)
        assist_delete_device = QPushButton("ELIMINA PROFILO")
        assist_delete_device.clicked.connect(self.delete_assistnow_device)
        assist_device_row.addWidget(QLabel("Dispositivo:"))
        assist_device_row.addWidget(self.assist_device_combo, 1)
        assist_device_row.addWidget(assist_new_device)
        assist_device_row.addWidget(assist_edit_device)
        assist_device_row.addWidget(assist_delete_device)
        assist_layout.addLayout(assist_device_row)

        self.assist_device_desc_label = QLabel("Descrizione: -")
        self.assist_device_desc_label.setWordWrap(True)
        self.assist_device_desc_label.setStyleSheet("color:#aab6c2;")
        assist_layout.addWidget(self.assist_device_desc_label)

        assist_top = QHBoxLayout()
        assist_top.setSpacing(8)
        self.assist_chipcode_edit = QLineEdit()
        self.assist_chipcode_edit.setPlaceholderText(
            "Chipcode dispositivo (ottenuto con REGISTRA ZTP)"
        )
        self.assist_chipcode_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.assist_chipcode_edit.setMinimumWidth(320)
        self.assist_service_url = "https://assistnow.services.u-blox.com/GetAssistNowData.ashx"
        self.assist_allowed_data = []
        self.assist_period_combo = QComboBox()
        self.assist_period_combo.addItems(
            ["1 giorno", "3 giorni", "7 giorni", "14 giorni"]
        )
        self.assist_period_combo.currentIndexChanged.connect(self._assist_period_changed)
        assist_top.addWidget(QLabel("Chipcode:"))
        assist_top.addWidget(self.assist_chipcode_edit, 1)
        assist_top.addWidget(QLabel("Periodo:"))
        assist_top.addWidget(self.assist_period_combo)
        assist_layout.addLayout(assist_top)

        assist_buttons = QHBoxLayout()
        assist_buttons.setSpacing(8)

        assist_register = QPushButton("REGISTRA ZTP")
        self.assist_register = assist_register
        assist_register.clicked.connect(self.register_assistnow_device)

        assist_download = QPushButton("SCARICA DATI")
        self.assist_download = assist_download
        assist_download.clicked.connect(self.download_assistnow_predictive)

        assist_send = QPushButton("INVIA AL M9N")
        self.assist_send = assist_send
        assist_send.clicked.connect(self.send_cached_assistnow_predictive)

        assist_file = QPushButton("INVIA FILE UBX")
        self.assist_file = assist_file
        assist_file.clicked.connect(self.send_assistnow_file)

        assist_status = QPushButton("STATO")
        self.assist_status_button = assist_status
        assist_status.clicked.connect(self.assistnow_status)

        assist_clear = QPushButton("CANCELLA")
        self.assist_clear_button = assist_clear
        assist_clear.clicked.connect(self.clear_assistnow)

        assist_diag = QPushButton("DIAGNOSTICA")
        self.assist_diag_button = assist_diag
        assist_diag.clicked.connect(self.show_assistnow_diagnostics)

        assist_manual = QPushButton("MANUALE")
        self.assist_manual_button = assist_manual
        assist_manual.clicked.connect(self.open_manager_manual)

        for button in (
            assist_register, assist_download, assist_send, assist_file,
            assist_status, assist_clear, assist_diag, assist_manual
        ):
            assist_buttons.addWidget(button)
        assist_buttons.addStretch()
        assist_layout.addLayout(assist_buttons)

        self.assist_state_label = QLabel("Nessun pacchetto AssistNow selezionato")
        self.assist_state_label.setWordWrap(True)
        self.assist_state_label.setMaximumHeight(40)
        assist_layout.addWidget(self.assist_state_label)

        root.addWidget(self.assist_widget)
        self._load_assistnow_settings()
        self._update_predictive_cache_status()

        splitter = QSplitter()
        self.editor_splitter = splitter
        root.addWidget(splitter, 1)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Circuiti disponibili"))
        self.track_list = QListWidget()
        # Selezione multipla semplice: ogni click aggiunge/toglie un circuito.
        # Il circuito corrente continua ad essere caricato nell'editor.
        self.track_list.setSelectionMode(
            QAbstractItemView.SelectionMode.MultiSelection
        )
        self.track_list.currentRowChanged.connect(self.load_selected_track)
        left_layout.addWidget(self.track_list)
        splitter.addWidget(left)

        center = QWidget()
        center_layout = QVBoxLayout(center)
        self.map_view = QWebEngineView()
        center_layout.addWidget(self.map_view, 1)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Vista:"))
        self.map_mode = QComboBox()
        self.map_mode.addItems([
            "OpenStreetMap",
            "Satellite",
            "Satellite + riferimenti",
        ])
        self.map_mode.currentIndexChanged.connect(self.change_map_mode)

        self.finish_button = QPushButton("Disegna traguardo")
        self.finish_button.clicked.connect(self.start_finish_drawing)

        self.sector_button = QPushButton("Aggiungi settore")
        self.sector_button.clicked.connect(self.start_sector_drawing)

        clear_finish_button = QPushButton("Cancella traguardo")
        clear_finish_button.clicked.connect(self.clear_finish)

        clear_sectors_button = QPushButton("Cancella settori")
        clear_sectors_button.setToolTip("Elimina tutti i settori intermedi del circuito corrente")
        clear_sectors_button.clicked.connect(self.clear_sectors)

        controls.addWidget(self.map_mode)
        controls.addWidget(self.finish_button)
        controls.addWidget(self.sector_button)
        controls.addWidget(clear_finish_button)
        controls.addWidget(clear_sectors_button)
        controls.addStretch()
        center_layout.addLayout(controls)
        splitter.addWidget(center)

        right = QWidget()
        form = QFormLayout(right)

        self.id_edit = QLineEdit()
        self.name_edit = QLineEdit()
        self.country_edit = QLineEdit("IT")

        self.direction_combo = QComboBox()
        self.direction_combo.addItems([
            "Non specificato",
            "Orario",
            "Antiorario",
        ])

        self.radius_spin = QDoubleSpinBox()
        self.radius_spin.setRange(1.0, 100.0)
        self.radius_spin.setValue(20.0)
        self.radius_spin.setSuffix(" m")

        self.lat1_edit = QLineEdit()
        self.lon1_edit = QLineEdit()
        self.lat2_edit = QLineEdit()
        self.lon2_edit = QLineEdit()
        for widget in (
            self.lat1_edit,
            self.lon1_edit,
            self.lat2_edit,
            self.lon2_edit,
        ):
            widget.setReadOnly(True)

        self.finish_length = QLabel("--")

        form.addRow("ID", self.id_edit)
        form.addRow("Nome", self.name_edit)
        form.addRow("Paese", self.country_edit)
        form.addRow("Senso", self.direction_combo)
        form.addRow("Raggio attivazione", self.radius_spin)
        form.addRow("Traguardo A - Lat", self.lat1_edit)
        form.addRow("Traguardo A - Lon", self.lon1_edit)
        form.addRow("Traguardo B - Lat", self.lat2_edit)
        form.addRow("Traguardo B - Lon", self.lon2_edit)
        form.addRow("Lunghezza traguardo", self.finish_length)

        form.addRow(QLabel("Linee settore intermedie (N linee = N+1 settori)"))
        self.sector_list = QListWidget()
        self.sector_list.setMinimumHeight(150)
        form.addRow(self.sector_list)

        sector_controls = QHBoxLayout()
        rename_button = QPushButton("Rinomina")
        rename_button.clicked.connect(self.rename_sector)
        delete_button = QPushButton("Elimina")
        delete_button.clicked.connect(self.delete_sector)
        sector_controls.addWidget(rename_button)
        sector_controls.addWidget(delete_button)

        sector_widget = QWidget()
        sector_widget.setLayout(sector_controls)
        form.addRow(sector_widget)

        save_button = QPushButton("SALVA CIRCUITO")
        save_button.clicked.connect(self.save_track)
        form.addRow(save_button)

        splitter.addWidget(right)
        splitter.setSizes([220, 820, 320])

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Pronto")
        self._apply_mode_visibility()

    def detach_for_embedding(self):
        """Restituisce il contenuto del tool per l'uso dentro la finestra principale."""
        content = self.takeCentralWidget()
        toolbar = None
        if self.mode in ("tracks", "all"):
            toolbar = self.track_toolbar
            self.removeToolBar(toolbar)
            toolbar.setParent(None)
        if content is not None:
            content.setParent(None)
        return content, toolbar

    def _apply_mode_visibility(self):
        """Mostra solo il pannello necessario alla funzione scelta."""
        tracks = self.mode in ("tracks", "all")
        sessions = self.mode in ("sessions", "all")
        assist = self.mode in ("assistnow", "all")

        self.track_toolbar.setVisible(tracks)
        self.search_edit.setVisible(tracks)
        self.search_button.setVisible(tracks)
        self.editor_splitter.setVisible(tracks)

        self.usb_common_widget.setVisible(True)
        self.track_usb_widget.setVisible(tracks)
        self.sessions_usb_widget.setVisible(sessions)
        self.assist_widget.setVisible(assist)

        # Dimensioni adeguate alla funzione: niente grandi aree vuote.
        if self.mode == "sessions":
            self.resize(760, 205)
            self.setMinimumSize(680, 190)
            self.setMaximumHeight(300)
            self.statusBar().showMessage(
                "Sessioni USB: scegli la porta e scarica, analizza o cancella le sessioni"
            )
        elif self.mode == "assistnow":
            self.resize(900, 275)
            self.setMinimumSize(780, 245)
            self.setMaximumHeight(380)
            self.statusBar().showMessage(
                "AssistNow: registra il dispositivo, scarica i dati e inviali al M9N"
            )
        elif self.mode == "tracks":
            self.resize(1360, 820)
            self.setMinimumSize(1050, 650)
            self.setMaximumHeight(16777215)
            self.statusBar().showMessage(
                "Circuiti: crea, modifica, invia o importa circuiti dal laptimer"
            )
        else:
            self.resize(1360, 820)
            self.setMaximumHeight(16777215)

    def load_map(self):
        html = r'''
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
html, body, #map { height:100%; margin:0; }
body { background:#111; }
</style>
</head>
<body>
<div id="map"></div>
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const map = L.map('map').setView([45.0, 9.0], 6);

const osmLayer = L.tileLayer(
  'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
  {maxZoom:20, attribution:'&copy; OpenStreetMap contributors'}
);

const satelliteLayer = L.tileLayer(
  'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
  {maxZoom:20, attribution:'Tiles &copy; Esri'}
);

const referenceLayer = L.tileLayer(
  'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
  {maxZoom:20, attribution:'Labels &copy; Esri'}
);

osmLayer.addTo(map);

let bridge = null;
let drawing = false;
let finishLayers = [];
let sectorLayers = [];

new QWebChannel(qt.webChannelTransport, function(channel) {
  bridge = channel.objects.bridge;
});

window.setBaseLayer = function(mode) {
  [osmLayer, satelliteLayer, referenceLayer].forEach(layer => {
    if (map.hasLayer(layer)) map.removeLayer(layer);
  });

  if (mode === 0) {
    osmLayer.addTo(map);
  } else if (mode === 1) {
    satelliteLayer.addTo(map);
  } else {
    satelliteLayer.addTo(map);
    referenceLayer.addTo(map);
  }
};

window.setDrawing = function(enabled) {
  drawing = enabled;
  map.getContainer().style.cursor = enabled ? 'crosshair' : '';
};

window.clearFinishLine = function() {
  finishLayers.forEach(layer => map.removeLayer(layer));
  finishLayers = [];
};

window.setFinishLine = function(lat1, lon1, lat2, lon2) {
  window.clearFinishLine();
  const a = [lat1, lon1];
  const b = [lat2, lon2];

  const markerA = L.circleMarker(
    a, {radius:6, color:'#ff3030', fillColor:'#ff3030', fillOpacity:1}
  ).addTo(map).bindTooltip('Traguardo A');

  const markerB = L.circleMarker(
    b, {radius:6, color:'#ff3030', fillColor:'#ff3030', fillOpacity:1}
  ).addTo(map).bindTooltip('Traguardo B');

  const line = L.polyline(
    [a, b], {color:'#ff3030', weight:5}
  ).addTo(map).bindTooltip('TRAGUARDO');

  finishLayers.push(markerA, markerB, line);
};

window.clearSectors = function() {
  sectorLayers.forEach(layer => map.removeLayer(layer));
  sectorLayers = [];
};

window.setSectors = function(sectors) {
  window.clearSectors();

  sectors.forEach((sector, index) => {
    const a = [sector.lat1, sector.lon1];
    const b = [sector.lat2, sector.lon2];
    const label = sector.name || ('Settore ' + (index + 1));

    const markerA = L.circleMarker(
      a, {radius:5, color:'#ffd400', fillColor:'#ffd400', fillOpacity:1}
    ).addTo(map).bindTooltip(label + ' A');

    const markerB = L.circleMarker(
      b, {radius:5, color:'#ffd400', fillColor:'#ffd400', fillOpacity:1}
    ).addTo(map).bindTooltip(label + ' B');

    const line = L.polyline(
      [a, b], {color:'#ffd400', weight:4}
    ).addTo(map).bindTooltip(label);

    sectorLayers.push(markerA, markerB, line);
  });
};

window.centerMap = function(lat, lon, zoom) {
  map.setView([lat, lon], zoom || 18);
};

window.fitTrack = function(lat1, lon1, lat2, lon2) {
  map.fitBounds([[lat1, lon1], [lat2, lon2]], {
    padding:[80,80],
    maxZoom:20
  });
};

map.on('click', function(event) {
  if (!drawing || !bridge) return;
  bridge.receivePoint(event.latlng.lat, event.latlng.lng);
});
</script>
</body>
</html>
'''
        self.bridge = Bridge()
        self.bridge.point_selected.connect(self.map_point_selected)

        channel = QWebChannel(self.map_view.page())
        channel.registerObject("bridge", self.bridge)
        self.map_view.page().setWebChannel(channel)
        self.map_view.setHtml(html, QUrl("https://localhost/"))

    def run_js(self, code):
        self.map_view.page().runJavaScript(code)

    def change_map_mode(self, index):
        self.run_js(f"setBaseLayer({index});")

    def search_osm(self):
        query = self.search_edit.text().strip()
        if not query:
            return

        try:
            url = (
                "https://nominatim.openstreetmap.org/search?"
                + urllib.parse.urlencode(
                    {
                        "q": query,
                        "format": "jsonv2",
                        "limit": 1,
                        "addressdetails": 1,
                    }
                )
            )
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "GOATS-RT-Track-Manager/2.2"},
            )
            with urllib.request.urlopen(request, timeout=15) as response:
                results = json.loads(response.read().decode("utf-8"))

            if not results:
                QMessageBox.information(
                    self,
                    "Ricerca",
                    "Nessun risultato trovato.",
                )
                return

            item = results[0]
            lat = float(item["lat"])
            lon = float(item["lon"])
            self.run_js(f"centerMap({lat}, {lon}, 18);")

            display_name = item.get("display_name", query)
            if not self.name_edit.text().strip():
                self.name_edit.setText(display_name.split(",")[0])
            if not self.id_edit.text().strip():
                self.id_edit.setText(slugify(self.name_edit.text()))

            country = item.get("address", {}).get("country_code", "")
            if country:
                self.country_edit.setText(country.upper())

            self.statusBar().showMessage(f"Trovato: {display_name}")
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Errore ricerca",
                f"Impossibile interrogare OpenStreetMap.\n\n{exc}",
            )

    def start_finish_drawing(self):
        self.clear_finish()
        self.pending_point = None
        self.drawing_mode = "finish"
        self.finish_button.setText("Clicca due punti...")
        self.run_js("setDrawing(true);")
        self.statusBar().showMessage(
            "Clicca il primo bordo e poi il secondo bordo della pista."
        )

    def start_sector_drawing(self):
        self.pending_point = None
        self.drawing_mode = "sector"
        self.sector_button.setText("Clicca due punti...")
        self.run_js("setDrawing(true);")
        self.statusBar().showMessage(
            "Clicca i due lati della pista nel punto di fine settore."
        )

    def map_point_selected(self, lat, lon):
        if self.drawing_mode is None:
            return

        if self.pending_point is None:
            self.pending_point = (lat, lon)
            self.statusBar().showMessage(
                "Primo punto acquisito. Clicca il lato opposto della pista."
            )
            return

        second_point = (lat, lon)

        if self.drawing_mode == "finish":
            self.finish_a = self.pending_point
            self.finish_b = second_point
            self.update_finish_fields()
            self.update_finish_map()

        elif self.drawing_mode == "sector":
            index = len(self.sectors) + 1
            self.sectors.append(
                {
                    "id": f"sector_{index}",
                    "name": f"Settore {index}",
                    "lat1": self.pending_point[0],
                    "lon1": self.pending_point[1],
                    "lat2": second_point[0],
                    "lon2": second_point[1],
                }
            )
            self.refresh_sector_list()
            self.update_sector_map()

        self.pending_point = None
        self.drawing_mode = None
        self.run_js("setDrawing(false);")
        self.finish_button.setText("Disegna traguardo")
        self.sector_button.setText("Aggiungi settore")
        self.statusBar().showMessage("Linea completata.")

    def update_finish_fields(self):
        if not self.finish_a or not self.finish_b:
            return

        self.lat1_edit.setText(f"{self.finish_a[0]:.8f}")
        self.lon1_edit.setText(f"{self.finish_a[1]:.8f}")
        self.lat2_edit.setText(f"{self.finish_b[0]:.8f}")
        self.lon2_edit.setText(f"{self.finish_b[1]:.8f}")

        length = haversine_m(
            self.finish_a[0],
            self.finish_a[1],
            self.finish_b[0],
            self.finish_b[1],
        )
        self.finish_length.setText(f"{length:.1f} m")

        if length < 3 or length > 80:
            QMessageBox.warning(
                self,
                "Controlla il traguardo",
                f"La linea misura {length:.1f} m. "
                "Verifica che attraversi correttamente la pista.",
            )

    def update_finish_map(self):
        if not self.finish_a or not self.finish_b:
            self.run_js("clearFinishLine();")
            return

        self.run_js(
            "setFinishLine("
            f"{self.finish_a[0]}, {self.finish_a[1]}, "
            f"{self.finish_b[0]}, {self.finish_b[1]}"
            ");"
        )

    def update_sector_map(self):
        self.run_js(f"setSectors({json.dumps(self.sectors)});")

    def refresh_sector_list(self):
        self.sector_list.clear()
        for sector in self.sectors:
            length = haversine_m(
                sector["lat1"],
                sector["lon1"],
                sector["lat2"],
                sector["lon2"],
            )
            self.sector_list.addItem(
                f"{sector['name']}  ({length:.1f} m)"
            )

    def rename_sector(self):
        row = self.sector_list.currentRow()
        if row < 0 or row >= len(self.sectors):
            return

        current = self.sectors[row]["name"]
        new_name, accepted = QInputDialog.getText(
            self,
            "Rinomina settore",
            "Nome:",
            text=current,
        )
        if accepted and new_name.strip():
            self.sectors[row]["name"] = new_name.strip()
            self.refresh_sector_list()
            self.update_sector_map()

    def delete_sector(self):
        row = self.sector_list.currentRow()
        if row < 0 or row >= len(self.sectors):
            return

        del self.sectors[row]
        for index, sector in enumerate(self.sectors, start=1):
            sector["id"] = f"sector_{index}"

        self.refresh_sector_list()
        self.update_sector_map()

    def clear_sectors(self):
        if not self.sectors:
            QMessageBox.information(
                self,
                "Settori",
                "Il circuito non contiene settori intermedi.",
            )
            return

        count = len(self.sectors)
        answer = QMessageBox.question(
            self,
            "Cancella settori",
            f"Eliminare tutti i {count} settori intermedi del circuito corrente?\n\n"
            "Il traguardo non verrà modificato. La cancellazione diventa definitiva "
            "quando salvi il circuito.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self.sectors = []
        self.pending_point = None
        if self.drawing_mode == "sector":
            self.drawing_mode = None
            self.run_js("setDrawing(false);")
            self.sector_button.setText("Aggiungi settore")

        self.refresh_sector_list()
        self.update_sector_map()
        self.statusBar().showMessage("Tutti i settori intermedi sono stati cancellati")

    def clear_finish(self):
        self.finish_a = None
        self.finish_b = None
        self.pending_point = None
        self.drawing_mode = None

        self.lat1_edit.clear()
        self.lon1_edit.clear()
        self.lat2_edit.clear()
        self.lon2_edit.clear()
        self.finish_length.setText("--")

        self.run_js("clearFinishLine();")
        self.run_js("setDrawing(false);")
        self.finish_button.setText("Disegna traguardo")

    def new_track(self):
        self.current_path = None
        self.track_list.clearSelection()

        self.id_edit.clear()
        self.name_edit.clear()
        self.country_edit.setText("IT")
        self.direction_combo.setCurrentIndex(0)
        self.radius_spin.setValue(20.0)

        self.clear_finish()
        self.sectors = []
        self.refresh_sector_list()
        self.update_sector_map()
        self.statusBar().showMessage("Nuovo circuito")

    def collect_track_data(self):
        name = self.name_edit.text().strip()
        if not name:
            raise ValueError("Inserire il nome del circuito.")
        if not self.finish_a or not self.finish_b:
            raise ValueError("Disegnare la linea del traguardo.")

        track_id = self.id_edit.text().strip() or slugify(name)
        direction = {
            0: "unspecified",
            1: "clockwise",
            2: "counterclockwise",
        }[self.direction_combo.currentIndex()]

        return {
            "schema_version": 3,
            "id": track_id,
            "name": name,
            "country": self.country_edit.text().strip().upper() or "IT",
            "direction": direction,
            "start_line": {
                "lat1": self.finish_a[0],
                "lon1": self.finish_a[1],
                "lat2": self.finish_b[0],
                "lon2": self.finish_b[1],
            },
            "trigger_radius_m": self.radius_spin.value(),
            "sectors": self.sectors,
        }

    def save_track(self):
        try:
            data = self.collect_track_data()
        except Exception as exc:
            QMessageBox.warning(self, "Dati incompleti", str(exc))
            return

        path = TRACKS_DIR / f"{slugify(data['id'])}.json"
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        self.current_path = path
        self.id_edit.setText(data["id"])
        self.refresh_tracks(path)
        self.statusBar().showMessage(f"Salvato: {path.name}")

    def refresh_tracks(self, select_path=None):
        self.files = sorted(TRACKS_DIR.glob("*.json"))
        self.track_list.clear()
        selected_row = -1

        for index, path in enumerate(self.files):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                label = f"{data.get('name', path.stem)} [{data.get('country', '--')}]"
            except Exception:
                label = f"{path.stem} [FILE NON VALIDO]"

            self.track_list.addItem(label)
            if select_path and path.resolve() == select_path.resolve():
                selected_row = index

        if selected_row >= 0:
            self.track_list.setCurrentRow(selected_row)

    def load_selected_track(self, row):
        if row < 0 or row >= len(self.files):
            return

        path = self.files[row]
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            start_line = data["start_line"]

            self.current_path = path
            self.id_edit.setText(data.get("id", ""))
            self.name_edit.setText(data.get("name", ""))
            self.country_edit.setText(data.get("country", "IT"))
            self.direction_combo.setCurrentIndex(
                {
                    "unspecified": 0,
                    "clockwise": 1,
                    "counterclockwise": 2,
                }.get(data.get("direction", "unspecified"), 0)
            )
            self.radius_spin.setValue(
                float(data.get("trigger_radius_m", 20.0))
            )

            self.finish_a = (
                float(start_line["lat1"]),
                float(start_line["lon1"]),
            )
            self.finish_b = (
                float(start_line["lat2"]),
                float(start_line["lon2"]),
            )
            self.sectors = data.get("sectors", [])

            self.update_finish_fields()
            self.update_finish_map()
            self.refresh_sector_list()
            self.update_sector_map()

            self.run_js(
                "fitTrack("
                f"{self.finish_a[0]}, {self.finish_a[1]}, "
                f"{self.finish_b[0]}, {self.finish_b[1]}"
                ");"
            )
            self.statusBar().showMessage(f"Caricato: {path.name}")
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Errore",
                f"Impossibile leggere il circuito.\n\n{exc}",
            )

    def delete_track(self):
        # Compatibilità con il comando della toolbar: usa la stessa eliminazione
        # multipla e sicura del pulsante DATABASE MANAGER.
        self.delete_tracks_from_manager()

    def delete_tracks_from_manager(self):
        rows=sorted({idx.row() for idx in self.track_list.selectedIndexes()})
        paths=[self.files[r] for r in rows if 0 <= r < len(self.files)]
        if not paths and self.current_path is not None:
            paths=[self.current_path]
        if not paths:
            QMessageBox.information(
                self,"Circuiti","Selezionare uno o più circuiti da eliminare dal Manager."
            )
            return

        labels=[]
        for path in paths:
            try:
                data=json.loads(path.read_text(encoding='utf-8'))
                labels.append(str(data.get('name') or path.stem))
            except Exception:
                labels.append(path.stem)

        preview='\n'.join(f'• {x}' for x in labels[:12])
        if len(labels)>12:
            preview+=f'\n• ... e altri {len(labels)-12}'
        answer=QMessageBox.question(
            self,
            'Elimina dal database Manager',
            f'Eliminare {len(paths)} circuito/i dal database locale del Manager?\n\n'
            f'{preview}\n\n'
            'Questa operazione NON elimina i circuiti presenti sul laptimer.',
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        deleted=0; errors=[]
        for path in paths:
            try:
                path.unlink(missing_ok=True)
                deleted+=1
            except Exception as exc:
                errors.append(f'{path.name}: {exc}')

        self.new_track()
        self.refresh_tracks()
        if errors:
            QMessageBox.warning(
                self,'Eliminazione circuiti',
                f'Eliminati {deleted} circuito/i.\n\nErrori:\n'+'\n'.join(errors[:10])
            )
        else:
            self.statusBar().showMessage(
                f'Eliminati {deleted} circuito/i dal database del Manager'
            )

    def import_json(self):
        filenames, _ = QFileDialog.getOpenFileNames(
            self,
            "Importa circuiti",
            "",
            "File JSON (*.json)",
        )
        imported = 0

        for filename in filenames:
            try:
                data = json.loads(
                    Path(filename).read_text(encoding="utf-8")
                )
                tracks = data.get("tracks", [data])
                for track in tracks:
                    path = TRACKS_DIR / f"{slugify(track['id'])}.json"
                    path.write_text(
                        json.dumps(track, indent=2, ensure_ascii=False),
                        encoding="utf-8",
                    )
                    imported += 1
            except Exception as exc:
                QMessageBox.warning(
                    self,
                    "Errore importazione",
                    f"{filename}\n\n{exc}",
                )

        self.refresh_tracks()
        self.statusBar().showMessage(f"Importati {imported} circuiti")

    def _new_assist_device_id(self):
        return f"dev_{time.time_ns()}"

    def _default_assist_device(self, name="Dispositivo 1", description=""):
        return {
            "id": self._new_assist_device_id(),
            "name": str(name or "Dispositivo 1"),
            "description": str(description or ""),
            "token": "",
            "uniqid": "",
            "monver": "",
            "chipcode": "",
            "service_url": "https://assistnow.services.u-blox.com/GetAssistNowData.ashx",
            "allowed_data": [],
            "period_index": 0,
        }

    def _current_assist_device(self):
        current_id = str(self.assist_current_device_id or "")
        for dev in self.assist_devices:
            if str(dev.get("id", "")) == current_id:
                return dev
        return self.assist_devices[0] if self.assist_devices else None

    def _assist_device_by_id(self, device_id):
        for dev in self.assist_devices:
            if str(dev.get("id", "")) == str(device_id or ""):
                return dev
        return None

    def _save_assist_device_profiles(self):
        self.assist_settings.setValue(
            "assist/devices_json",
            json.dumps(self.assist_devices, ensure_ascii=False),
        )
        self.assist_settings.setValue("assist/current_device_id", self.assist_current_device_id)
        self.assist_settings.sync()

    def _load_assist_device_profiles(self):
        raw = str(self.assist_settings.value("assist/devices_json", "") or "")
        devices = []
        if raw:
            try:
                data = json.loads(raw)
                if isinstance(data, list):
                    devices = [d for d in data if isinstance(d, dict)]
            except Exception:
                devices = []

        # Migrazione automatica dalla vecchia configurazione a dispositivo singolo.
        if not devices:
            legacy_token = str(self.assist_settings.value("token", "") or "")
            legacy_uniqid = str(self.assist_settings.value("uniqid", "") or "")
            legacy_monver = str(self.assist_settings.value("monver", "") or "")
            legacy_chipcode = str(self.assist_settings.value("assist/chipcode", "") or "")
            legacy_service = str(self.assist_settings.value("assist/service_url", "") or "")
            legacy_allowed = str(self.assist_settings.value("assist/allowed_data", "") or "")
            legacy_period = int(self.assist_settings.value("assist/period_index", 0) or 0)
            migrated = any((legacy_token, legacy_uniqid, legacy_monver, legacy_chipcode))
            dev = self._default_assist_device(
                "Dispositivo 1",
                "Profilo importato dalla precedente configurazione AssistNow" if migrated else "",
            )
            dev.update({
                "token": legacy_token,
                "uniqid": legacy_uniqid,
                "monver": legacy_monver,
                "chipcode": legacy_chipcode,
                "service_url": legacy_service or dev["service_url"],
                "allowed_data": self._normalize_allowed_data(legacy_allowed),
                "period_index": legacy_period if 0 <= legacy_period <= 3 else 0,
            })
            devices = [dev]
            self.assist_devices = devices
            self.assist_current_device_id = dev["id"]
            self._save_assist_device_profiles()
            # Copia le vecchie cache nel profilo migrato, senza cancellare gli originali.
            for days in (1, 3, 7, 14):
                old_cache = APP_DIR / f"assistnow_predictive_{days}d.ubx"
                if old_cache.exists():
                    try:
                        new_cache = self._predictive_cache_path(days, device_id=dev["id"])
                        new_cache.parent.mkdir(parents=True, exist_ok=True)
                        if not new_cache.exists():
                            new_cache.write_bytes(old_cache.read_bytes())
                    except Exception:
                        pass
        else:
            # Normalizzazione schema per versioni future/vecchie.
            normalized = []
            for idx, dev in enumerate(devices, start=1):
                base = self._default_assist_device(f"Dispositivo {idx}")
                base.update(dev)
                base["id"] = str(base.get("id") or self._new_assist_device_id())
                base["name"] = str(base.get("name") or f"Dispositivo {idx}")
                base["description"] = str(base.get("description") or "")
                base["allowed_data"] = self._normalize_allowed_data(base.get("allowed_data"))
                try:
                    period = int(base.get("period_index", 0))
                except Exception:
                    period = 0
                base["period_index"] = period if 0 <= period <= 3 else 0
                normalized.append(base)
            devices = normalized
            self.assist_devices = devices
            saved_id = str(self.assist_settings.value("assist/current_device_id", "") or "")
            self.assist_current_device_id = saved_id if self._assist_device_by_id(saved_id) else devices[0]["id"]
            self._save_assist_device_profiles()

        self.assist_devices = devices
        if not self.assist_current_device_id and devices:
            self.assist_current_device_id = devices[0]["id"]

    def _refresh_assist_device_combo(self):
        if not hasattr(self, "assist_device_combo"):
            return
        self._assist_switching = True
        self.assist_device_combo.clear()
        selected_index = 0
        for idx, dev in enumerate(self.assist_devices):
            name = str(dev.get("name") or f"Dispositivo {idx+1}")
            self.assist_device_combo.addItem(name, str(dev.get("id") or ""))
            if str(dev.get("id") or "") == str(self.assist_current_device_id or ""):
                selected_index = idx
        if self.assist_device_combo.count():
            self.assist_device_combo.setCurrentIndex(selected_index)
        self._assist_switching = False

    def _save_assist_ui_to_device(self, device_id):
        dev = self._assist_device_by_id(device_id)
        if dev is None or not hasattr(self, "assist_chipcode_edit"):
            return
        dev["chipcode"] = self.assist_chipcode_edit.text().strip()
        dev["service_url"] = self.assist_service_url
        dev["allowed_data"] = list(self.assist_allowed_data)
        dev["period_index"] = self.assist_period_combo.currentIndex()

    def _load_assist_device_ui(self, device_id=None):
        dev = self._assist_device_by_id(device_id or self.assist_current_device_id)
        if dev is None:
            return
        self.assist_current_device_id = str(dev["id"])
        self._assist_loaded_device_id = self.assist_current_device_id
        self._assist_switching = True
        self.assist_chipcode_edit.setText(str(dev.get("chipcode", "") or ""))
        self.assist_service_url = str(dev.get("service_url") or "https://assistnow.services.u-blox.com/GetAssistNowData.ashx")
        self.assist_allowed_data = self._normalize_allowed_data(dev.get("allowed_data"))
        period = int(dev.get("period_index", 0) or 0)
        self.assist_period_combo.setCurrentIndex(period if 0 <= period < self.assist_period_combo.count() else 0)
        desc = str(dev.get("description", "") or "").strip()
        self.assist_device_desc_label.setText(f"Descrizione: {desc or '-'}")
        self._assist_switching = False
        self._update_predictive_cache_status()

    def _on_assist_device_changed(self, *_):
        if self._assist_switching or not hasattr(self, "assist_device_combo"):
            return
        new_id = str(self.assist_device_combo.currentData() or "")
        if not new_id:
            return
        if self._assist_loaded_device_id and self._assist_loaded_device_id != new_id:
            self._save_assist_ui_to_device(self._assist_loaded_device_id)
        self.assist_current_device_id = new_id
        self._load_assist_device_ui(new_id)
        self._save_assist_device_profiles()
        dev = self._current_assist_device() or {}
        self.statusBar().showMessage(f"AssistNow: dispositivo selezionato - {dev.get('name', '')}")

    def _assist_period_changed(self, *_):
        if self._assist_switching:
            return
        self._save_assist_ui_to_device(self.assist_current_device_id)
        self._save_assist_device_profiles()
        self._update_predictive_cache_status()

    def add_assistnow_device(self):
        dialog = AssistNowDeviceDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        name, description = dialog.values()
        dev = self._default_assist_device(name, description)
        self._save_assist_ui_to_device(self.assist_current_device_id)
        self.assist_devices.append(dev)
        self.assist_current_device_id = dev["id"]
        self._save_assist_device_profiles()
        self._refresh_assist_device_combo()
        self._load_assist_device_ui(dev["id"])
        self.statusBar().showMessage(f"AssistNow: creato profilo {name}")

    def edit_assistnow_device(self):
        dev = self._current_assist_device()
        if dev is None:
            return
        dialog = AssistNowDeviceDialog(
            self,
            str(dev.get("name", "")),
            str(dev.get("description", "")),
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        name, description = dialog.values()
        dev["name"] = name
        dev["description"] = description
        self._save_assist_ui_to_device(dev["id"])
        self._save_assist_device_profiles()
        self._refresh_assist_device_combo()
        self._load_assist_device_ui(dev["id"])

    def delete_assistnow_device(self):
        dev = self._current_assist_device()
        if dev is None:
            return
        if len(self.assist_devices) <= 1:
            QMessageBox.information(
                self, "AssistNow",
                "Deve rimanere almeno un profilo dispositivo. Puoi usare MODIFICA oppure cancellarne le credenziali."
            )
            return
        name = str(dev.get("name", "Dispositivo"))
        answer = QMessageBox.question(
            self, "AssistNow - Elimina profilo",
            f"Eliminare dal Manager il profilo '{name}'?\n\n"
            "Questa operazione elimina solo il profilo locale e la relativa cache Predictive. "
            "Non elimina il Thing dal portale Thingstream."
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        dev_id = str(dev.get("id", ""))
        self.assist_devices = [d for d in self.assist_devices if str(d.get("id", "")) != dev_id]
        cache_dir = APP_DIR / "assistnow_cache" / slugify(dev_id)
        if cache_dir.exists():
            try:
                for child in cache_dir.iterdir():
                    if child.is_file():
                        child.unlink()
                cache_dir.rmdir()
            except Exception:
                pass
        self.assist_current_device_id = str(self.assist_devices[0]["id"])
        self._save_assist_device_profiles()
        self._refresh_assist_device_combo()
        self._load_assist_device_ui(self.assist_current_device_id)

    def _load_assistnow_settings(self):
        self._load_assist_device_profiles()
        self._refresh_assist_device_combo()
        self._load_assist_device_ui(self.assist_current_device_id)

    def _save_assistnow_settings(self, token=None, uniqid=None, monver=None):
        dev = self._current_assist_device()
        if dev is None:
            return
        if token is not None:
            dev["token"] = token
        if uniqid is not None:
            dev["uniqid"] = uniqid
        if monver is not None:
            dev["monver"] = monver
        self._save_assist_ui_to_device(dev["id"])
        self._save_assist_device_profiles()

    def clear_assistnow_credentials(self, show_message=True):
        dev = self._current_assist_device()
        if dev is None:
            return
        for key in ("token", "uniqid", "monver", "chipcode"):
            dev[key] = ""
        dev["service_url"] = "https://assistnow.services.u-blox.com/GetAssistNowData.ashx"
        dev["allowed_data"] = []
        self.assist_chipcode_edit.clear()
        self.assist_allowed_data = []
        self.assist_service_url = dev["service_url"]
        self._save_assist_device_profiles()
        self._update_predictive_cache_status()
        if show_message:
            QMessageBox.information(
                self, "AssistNow",
                f"Credenziali e dati GNSS salvati per '{dev.get('name', 'dispositivo')}' cancellati dal Manager."
            )

    def open_manager_manual(self):
        candidates = [
            APP_DIR / "GOATS_RT_Manager_Manuale_V5.4.13.0.pdf",
            APP_DIR / "GOATS_RT_Manager_Manuale_V5.4.13.0.docx",
        ]
        for path in candidates:
            if path.exists():
                if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
                    QMessageBox.warning(self, "Manuale", f"Impossibile aprire automaticamente:\n{path}")
                return
        QMessageBox.information(
            self, "Manuale",
            "Manuale non trovato nella cartella del Manager. Reinstalla il pacchetto completo V5.4.13.6."
        )

    @staticmethod
    def _mask_secret(value, keep=4):
        value = str(value or "")
        if len(value) <= keep * 2:
            return "*" * len(value)
        return value[:keep] + "…" + value[-keep:]

    def _set_assist_diag(self, title, lines):
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dev = self._current_assist_device() or {}
        text = [
            f"GOATS RT Manager V5.4.13.6 - {title}",
            f"Data: {stamp}",
            f"Dispositivo: {dev.get('name', '-')}",
            f"Descrizione: {dev.get('description', '-') or '-'}",
            "",
        ] + list(lines)
        self.assist_last_diag = "\n".join(text)
        try:
            (APP_DIR / "assistnow_diagnostic.txt").write_text(self.assist_last_diag, encoding="utf-8")
        except Exception:
            pass

    def show_assistnow_diagnostics(self):
        text = self.assist_last_diag or "Nessuna diagnostica AssistNow disponibile in questa sessione."
        dlg = QDialog(self)
        dlg.setWindowTitle("AssistNow - Diagnostica")
        dlg.resize(820, 520)
        lay = QVBoxLayout(dlg)
        box = QLineEdit()
        # QLineEdit non e' adatto a testo multilinea: mostriamo la diagnostica in una label selezionabile.
        lab = QLabel(text)
        lab.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lab.setWordWrap(True)
        lay.addWidget(lab)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(dlg.reject)
        close.clicked.connect(dlg.accept)
        lay.addWidget(close)
        dlg.exec()

    def _send_assistnow_payload(self, payload):
        port = self.port_combo.currentData()
        if not port:
            raise RuntimeError("Selezionare la porta COM del laptimer.")
        if len(payload) < 8 or payload[:2] != b"\xB5\x62":
            raise ValueError("Il file non sembra uno stream UBX valido.")
        if len(payload) > 196608:
            raise ValueError("Pacchetto AssistNow oltre il limite di 192 KiB.")

        crc = zlib.crc32(payload) & 0xFFFFFFFF
        diag = [f"COM: {port}", f"Payload: {len(payload)} byte", f"CRC32: {crc:08X}"]
        dlg = QProgressDialog("Connessione al laptimer...", "Annulla", 0, len(payload), self)
        dlg.setWindowTitle("AssistNow - Invio Predictive")
        dlg.setMinimumDuration(0)
        dlg.setValue(0)
        QApplication.processEvents()

        try:
            with serial.Serial(port, 115200, timeout=4.0, write_timeout=15.0) as link:
                time.sleep(0.4)
                link.reset_input_buffer()
                link.write(f"GANO_BEGIN {len(payload)} {crc:08X}\n".encode("ascii"))
                link.flush()
                answer = link.readline().decode("ascii", errors="replace").strip()
                diag.append(f"RX begin: {answer or '<vuoto>'}")
                if answer != "GANO_READY":
                    raise RuntimeError(f"Laptimer non pronto: {answer or 'nessuna risposta'}")

                sent = 0
                chunk = 512
                while sent < len(payload):
                    if dlg.wasCanceled():
                        raise RuntimeError("Invio annullato.")
                    part = payload[sent:sent + chunk]

                    link.write(part)
                    link.flush()
                    ack = link.readline().decode("ascii", errors="replace").strip()
                    if not ack.startswith("GANO_CHUNK_OK"):
                        raise RuntimeError(
                            f"ACK non ricevuto dopo il blocco a {sent} byte: {ack or 'nessuna risposta'}"
                        )
                    parts = ack.split()
                    try:
                        received = int(parts[1])
                    except Exception:
                        received = sent + len(part)
                    sent += len(part)

                    dlg.setLabelText(
                        f"Invio Predictive al laptimer...\n"
                        f"{received:,} / {len(payload):,} byte"
                    )
                    dlg.setValue(min(received, len(payload)))
                    QApplication.processEvents()

                dlg.setLabelText("Trasferimento completo. Verifica CRC e salvataggio NVS...")
                QApplication.processEvents()

                old_timeout = link.timeout
                link.timeout = 2.0
                stages = []
                final = ""
                deadline = time.time() + 60.0
                while time.time() < deadline:
                    line = link.readline().decode("ascii", errors="replace").strip()
                    if not line:
                        continue
                    if line in ("GANO_RX_DONE", "GANO_CRC_OK", "GANO_NVS_BEGIN", "GANO_NVS_OK"):
                        stages.append(line)
                        dlg.setLabelText("Laptimer: " + line.replace("GANO_", "").replace("_", " "))
                        QApplication.processEvents()
                        continue
                    if line.startswith("GANO_OK") or line.startswith("GANO_ERR"):
                        final = line
                        break
                    stages.append("ALTRO: " + line)
                link.timeout = old_timeout

                diag.append(f"Chunk ACK completati: {sent} / {len(payload)} byte")
                if stages:
                    diag.append("Stadi: " + " -> ".join(stages))
                diag.append(f"RX finale: {final or '<vuoto>'}")
                if not final.startswith("GANO_OK"):
                    raise RuntimeError(
                        f"AssistNow rifiutato: {final or 'nessuna risposta'}\n\n"
                        "Apri DIAGNOSTICA per i dettagli."
                    )

                dlg.setValue(len(payload))
                return len(payload)
        finally:
            self._set_assist_diag("Trasferimento al laptimer", diag)
            dlg.close()

    def send_assistnow_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Seleziona pacchetto AssistNow", "",
            "u-blox UBX / binario (*.ubx *.bin);;Tutti i file (*.*)")
        if not filename:
            return
        try:
            payload = Path(filename).read_bytes()
            size = self._send_assistnow_payload(payload)
            QMessageBox.information(
                self, "AssistNow",
                f"Pacchetto AssistNow trasferito.\n\n{size} byte")
            self.statusBar().showMessage(f"AssistNow inviato: {size} byte")
        except Exception as exc:
            QMessageBox.critical(self, "AssistNow", str(exc))

    @staticmethod
    def _validate_full_ubx_hex(value, expected_class, expected_id, label):
        value = re.sub(r"[^0-9A-Fa-f]", "", value or "").upper()
        if len(value) < 16 or len(value) % 2:
            raise ValueError(f"{label}: risposta UBX non valida o incompleta.")
        raw = bytes.fromhex(value)
        if raw[:2] != b"\xB5\x62" or raw[2] != expected_class or raw[3] != expected_id:
            raise ValueError(f"{label}: non corrisponde al messaggio UBX atteso.")
        payload_len = raw[4] | (raw[5] << 8)
        if len(raw) != payload_len + 8:
            raise ValueError(
                f"{label}: lunghezza non coerente (attesi {payload_len + 8} byte, ricevuti {len(raw)})."
            )
        ck_a = 0
        ck_b = 0
        for byte in raw[2:-2]:
            ck_a = (ck_a + byte) & 0xFF
            ck_b = (ck_b + ck_a) & 0xFF
        if raw[-2] != ck_a or raw[-1] != ck_b:
            raise ValueError(f"{label}: checksum UBX non valido.")
        return value

    def read_gnss_identity(self):
        """Legge SEC-UNIQID e MON-VER dal M9N tramite il firmware GOATS RT V10.2+ (GGID_GET)."""
        port = self.port_combo.currentData()
        if not port:
            raise RuntimeError("Selezionare la porta COM del laptimer.")

        uniqid = ""
        monver = ""
        begin_seen = False
        transcript = []
        deadline = time.monotonic() + 8.0

        with serial.Serial(port, 115200, timeout=0.35, write_timeout=3.0) as link:
            time.sleep(0.35)
            link.reset_input_buffer()
            link.write(b"GGID_GET\n")
            link.flush()

            while time.monotonic() < deadline:
                raw = link.readline()
                if not raw:
                    continue
                line = raw.decode("ascii", errors="replace").strip()
                if not line:
                    continue
                transcript.append(line)

                if line == "GGID_BEGIN":
                    begin_seen = True
                    continue
                if line.startswith("GGID_ERR"):
                    reason = line.partition(" ")[2] or "errore sconosciuto"
                    if reason == "TIMEOUT_BOTH":
                        raise RuntimeError("Il laptimer non ha ricevuto né SEC-UNIQID né MON-VER dal M9N. Verificare RX/TX GPS e firmware V10.2+.")
                    if reason == "TIMEOUT_UNIQID":
                        raise RuntimeError("Il M9N non ha risposto a UBX-SEC-UNIQID.")
                    if reason == "TIMEOUT_MONVER":
                        raise RuntimeError("Il M9N non ha risposto a UBX-MON-VER.")
                    if reason == "BUSY":
                        raise RuntimeError("Il laptimer è già impegnato in una lettura GNSS. Riprovare tra qualche secondo.")
                    raise RuntimeError(f"Errore GGID del laptimer: {reason}")
                if line.startswith("GGID_UNIQID "):
                    uniqid = line.split(None, 1)[1].strip()
                    continue
                if line.startswith("GGID_MONVER "):
                    monver = line.split(None, 1)[1].strip()
                    continue
                if line == "GGID_END":
                    break

        if not begin_seen:
            preview = " | ".join(transcript[-5:]) if transcript else "nessuna risposta"
            raise RuntimeError(
                "Il laptimer non riconosce GGID_GET o non risponde. "
                "Serve il firmware GOATS RT V10.2.0 o successivo.\n\n"
                f"Risposta USB: {preview}"
            )
        if not uniqid or not monver:
            missing = []
            if not uniqid: missing.append("SEC-UNIQID")
            if not monver: missing.append("MON-VER")
            raise RuntimeError("Risposta GNSS incompleta: manca " + " e ".join(missing) + ".")

        uniqid = self._validate_full_ubx_hex(uniqid, 0x27, 0x03, "UBX-SEC-UNIQID")
        monver = self._validate_full_ubx_hex(monver, 0x0A, 0x04, "UBX-MON-VER")
        self._save_assistnow_settings(uniqid=uniqid, monver=monver)
        dev = self._current_assist_device() or {}
        self.statusBar().showMessage(
            f"M9N: SEC-UNIQID e MON-VER memorizzati per {dev.get('name', 'dispositivo')}"
        )
        return uniqid, monver

    def register_assistnow_device(self):
        dialog = AssistNowRegistrationDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        token, uniqid, monver = dialog.values()
        if not token:
            QMessageBox.warning(self, "AssistNow", "Inserire il token ZTP del Device Profile Thingstream.")
            return
        try:
            uniqid = self._validate_full_ubx_hex(uniqid, 0x27, 0x03, "UBX-SEC-UNIQID")
            monver = self._validate_full_ubx_hex(monver, 0x0A, 0x04, "UBX-MON-VER")
            # Thingstream ZTP requires the GNSS UBX frames inside the "messages" object.
            # The provisioning token must be lowercase.
            token = token.lower()
            body = json.dumps({
                "token": token,
                "messages": {
                    "UBX-SEC-UNIQID": uniqid,
                    "UBX-MON-VER": monver,
                },
            }).encode("utf-8")
            req = urllib.request.Request(
                "https://api.thingstream.io/ztp/assistnow/credentials",
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "GOATS-RT-Manager/5.4.4",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                raw_result = response.read()
                status = getattr(response, "status", 200)
                headers = dict(response.headers.items())
                result = json.loads(raw_result.decode("utf-8"))
            self._set_assist_diag("Registrazione ZTP", [
                "Endpoint: https://api.thingstream.io/ztp/assistnow/credentials",
                f"HTTP: {status}",
                f"Token: {self._mask_secret(token)}",
                f"SEC-UNIQID: {self._mask_secret(uniqid, 8)}",
                f"MON-VER bytes hex: {len(monver)//2}",
                f"Content-Type: {headers.get('Content-Type', '')}",
                f"Risposta: {raw_result.decode('utf-8', errors='replace')[:1500]}",
            ])
            chipcode = str(result.get("chipcode", "")).strip()
            if not chipcode:
                raise RuntimeError("La risposta ZTP non contiene il chipcode.")
            self.assist_chipcode_edit.setText(chipcode)
            self.assist_service_url = str(result.get("serviceUrl") or self.assist_service_url)
            self.assist_allowed_data = self._normalize_allowed_data(result.get("allowedData"))
            self._save_assistnow_settings(token=token, uniqid=uniqid, monver=monver)
            allowed = ", ".join(self.assist_allowed_data) if self.assist_allowed_data else "non dichiarati"
            dev = self._current_assist_device() or {}
            QMessageBox.information(
                self, "AssistNow - ZTP completato",
                f"Dispositivo '{dev.get('name', 'selezionato')}' registrato correttamente.\n\n"
                f"Chipcode ricevuto e caricato nel Manager.\n"
                f"Dati consentiti: {allowed}\n\n"
                "Token, identità M9N e chipcode sono stati memorizzati localmente nel profilo Windows del Manager."
            )
            self.statusBar().showMessage("AssistNow: registrazione ZTP completata")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:2000]
            self._set_assist_diag("Errore registrazione ZTP", [
                "Endpoint: https://api.thingstream.io/ztp/assistnow/credentials",
                f"HTTP: {exc.code}",
                f"Reason: {exc.reason}",
                f"Body: {detail or '<vuoto>'}",
            ])
            QMessageBox.critical(self, "AssistNow - ZTP", f"HTTP {exc.code}: {detail or exc.reason}\n\nDettagli salvati in DIAGNOSTICA.")
        except Exception as exc:
            QMessageBox.critical(self, "AssistNow - ZTP", str(exc))

    @staticmethod
    def _normalize_allowed_data(value):
        """Normalizza allowedData Thingstream sia se arriva come lista sia come stringa CSV/JSON."""
        if value is None:
            return []
        if isinstance(value, (list, tuple, set)):
            items = list(value)
        elif isinstance(value, str):
            text = value.strip()
            if not text:
                return []
            try:
                decoded = json.loads(text)
                if isinstance(decoded, list):
                    items = decoded
                else:
                    items = re.split(r"[,;\s]+", text)
            except Exception:
                items = re.split(r"[,;\s]+", text)
        else:
            items = [value]
        out = []
        for item in items:
            token = str(item).strip().strip('\"\'')
            if token and token not in out:
                out.append(token)
        return out

    def _predictive_days(self):
        return [1, 3, 7, 14][self.assist_period_combo.currentIndex()]

    def _predictive_cache_path(self, days=None, device_id=None):
        if days is None:
            days = self._predictive_days()
        if device_id is None:
            device_id = self.assist_current_device_id or "default"
        cache_dir = APP_DIR / "assistnow_cache" / slugify(str(device_id))
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / f"assistnow_predictive_{days}d.ubx"

    def _update_predictive_cache_status(self):
        if not hasattr(self, "assist_state_label"):
            return
        days = self._predictive_days()
        cache = self._predictive_cache_path(days)
        dev = self._current_assist_device() or {}
        dev_name = str(dev.get("name", "Dispositivo") or "Dispositivo")
        if cache.exists():
            size = cache.stat().st_size
            self.assist_state_label.setText(
                f"{dev_name} - Predictive {days} giorni scaricato - {size:,} byte - pronto per l'invio"
            )
        else:
            self.assist_state_label.setText(
                f"{dev_name} - Predictive {days} giorni: non ancora scaricato"
            )

    def download_assistnow_predictive(self):
        chipcode = self.assist_chipcode_edit.text().strip()
        if not chipcode:
            QMessageBox.information(
                self, "AssistNow",
                "Manca il chipcode del ricevitore.\n\n"
                "Premi REGISTRA ZTP oppure usa il chipcode già memorizzato."
            )
            return

        days = self._predictive_days()
        data_key = f"uporb_{days}"
        if self.assist_allowed_data and data_key not in self.assist_allowed_data:
            QMessageBox.warning(
                self, "AssistNow",
                f"Il profilo del dispositivo non dichiara '{data_key}'.\n"
                f"Dati consentiti: {', '.join(self.assist_allowed_data)}"
            )
            return

        params = urllib.parse.urlencode({
            "chipcode": chipcode,
            "gnss": "gps,gal,glo,bds",
            "data": f"{data_key},ualm",
        })
        url = self.assist_service_url + ("&" if "?" in self.assist_service_url else "?") + params

        dlg = QProgressDialog("Connessione a Thingstream...", None, 0, 0, self)
        dlg.setWindowTitle("AssistNow - Download Predictive")
        dlg.setMinimumDuration(0)
        dlg.show()
        QApplication.processEvents()

        try:
            req = urllib.request.Request(url, headers={
                "Accept": "application/octet-stream",
                "User-Agent": "GOATS-RT-Manager/5.4.8",
            })
            dlg.setLabelText(f"Download Predictive Orbits - validità {days} giorni...")
            QApplication.processEvents()
            with urllib.request.urlopen(req, timeout=45) as response:
                status = getattr(response, "status", 200)
                headers = dict(response.headers.items())
                payload = response.read(196609)

            safe_url = url.replace(chipcode, self._mask_secret(chipcode))
            self._set_assist_diag("Download Predictive Orbits", [
                f"URL: {safe_url}",
                f"HTTP: {status}",
                f"Content-Type: {headers.get('Content-Type', '')}",
                f"Content-Length header: {headers.get('Content-Length', '')}",
                f"Byte ricevuti: {len(payload)}",
                f"Primi 32 byte: {payload[:32].hex(' ').upper()}",
            ])
            self._save_assistnow_settings()

            if len(payload) < 8 or payload[:2] != b"\xB5\x62":
                preview = payload[:300].decode("utf-8", errors="replace")
                raise RuntimeError(f"Risposta AssistNow non valida: {preview or 'nessun dato'}")
            if len(payload) > 196608:
                raise RuntimeError("Pacchetto Predictive oltre il limite di 192 KiB.")

            cache = self._predictive_cache_path(days)
            cache.write_bytes(payload)
            self._update_predictive_cache_status()
            self.statusBar().showMessage(
                f"Predictive {days}d scaricato: {len(payload)} byte - pronto per l'invio"
            )
            QMessageBox.information(
                self, "AssistNow",
                f"Download completato.\n\n"
                f"Validità: {days} giorni\n"
                f"GNSS: GPS + Galileo + GLONASS + BeiDou\n"
                f"Dimensione: {len(payload):,} byte\n"
                f"Cache locale: {cache.name}\n\n"
                f"Premi INVIA PREDICTIVE quando vuoi trasferirlo al laptimer."
            )
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:2000]
            safe_url = url.replace(chipcode, self._mask_secret(chipcode))
            self._set_assist_diag("Errore download Predictive Orbits", [
                f"URL: {safe_url}", f"HTTP: {exc.code}",
                f"Reason: {exc.reason}", f"Body: {detail or '<vuoto>'}",
            ])
            QMessageBox.critical(
                self, "AssistNow",
                f"Download fallito - HTTP {exc.code}.\n\n{detail or exc.reason}"
            )
        except Exception as exc:
            QMessageBox.critical(self, "AssistNow", str(exc))
        finally:
            dlg.close()

    def send_cached_assistnow_predictive(self):
        days = self._predictive_days()
        cache = self._predictive_cache_path(days)
        if not cache.exists():
            QMessageBox.warning(
                self, "AssistNow",
                f"Non c'è ancora un pacchetto Predictive da {days} giorni.\n"
                "Premi prima SCARICA PREDICTIVE."
            )
            return
        try:
            payload = cache.read_bytes()
            size = self._send_assistnow_payload(payload)
            self.assist_state_label.setText(
                f"Predictive {days} giorni - {size:,} byte - inviato al laptimer"
            )
            self.statusBar().showMessage(f"Predictive {days}d inviato: {size} byte")
            QMessageBox.information(
                self, "AssistNow",
                f"Invio completato.\n\nValidità: {days} giorni\nDimensione: {size:,} byte"
            )
        except Exception as exc:
            QMessageBox.critical(self, "AssistNow", str(exc))


    def assistnow_status(self):
        port = self.port_combo.currentData()
        if not port:
            QMessageBox.warning(self, "AssistNow", "Selezionare una porta COM.")
            return
        try:
            with serial.Serial(port, 115200, timeout=2.0, write_timeout=2.0) as link:
                time.sleep(0.4)
                link.reset_input_buffer()
                link.write(b"GANO_STATUS\n"); link.flush()
                answer = link.readline().decode("ascii", errors="replace").strip()
            if not answer.startswith("GANO_STATUS"):
                raise RuntimeError(answer or "Nessuna risposta")
            size = int(answer.split()[1])
            QMessageBox.information(
                self, "AssistNow",
                "Cache presente sul laptimer: "
                + (f"{size} byte" if size else "NO"))
        except Exception as exc:
            QMessageBox.critical(self, "AssistNow", str(exc))

    def clear_assistnow(self):
        if QMessageBox.question(
            self, "AssistNow", "Cancellare la cache AssistNow dal laptimer?"
        ) != QMessageBox.StandardButton.Yes:
            return
        if self._send_simple_command("GANO_CLEAR", "GANO_CLEAR_OK"):
            QMessageBox.information(self, "AssistNow", "Cache AssistNow cancellata.")

    @staticmethod
    def _windows_goats_drives():
        """Return [(root, GOATS_dir)] for mounted Windows volumes containing GOATS."""
        found = []
        if os.name != "nt":
            return found
        try:
            mask = ctypes.windll.kernel32.GetLogicalDrives()
            get_type = ctypes.windll.kernel32.GetDriveTypeW
            for index in range(26):
                if not (mask & (1 << index)):
                    continue
                root = f"{chr(65 + index)}:\\"
                try:
                    drive_type = int(get_type(ctypes.c_wchar_p(root)))
                    goats_dir = Path(root) / "GOATS"
                    if drive_type in (2, 3) and goats_dir.is_dir():
                        found.append((root, goats_dir))
                except OSError:
                    continue
        except Exception:
            pass
        return found

    def _import_csv_paths_into_manager(self, paths):
        store = SessionStore(DB_PATH)
        imported = 0
        errors = []
        try:
            for path in paths:
                try:
                    for parsed in parse_any(path):
                        store.import_session(parsed)
                        imported += 1
                except Exception as exc:
                    errors.append(f"{Path(path).name}: {exc}")
        finally:
            try:
                store.conn.close()
            except Exception:
                pass
        return imported, errors

    def activate_usb_sd_from_manager(self):
        """
        Safe USB-SD workflow.

        The experimental USB_SD_MODE serial command caused an ESP32-S3 reset
        before TinyUSB MSC could take ownership. Do not send that command.
        Instead use the firmware's already proven MODALITA USB SD control,
        then this Manager detects the mounted GOATS volume and opens the CSVs.
        """
        QMessageBox.information(
            self,
            "Modalità USB SD",
            "Sul laptimer premi SET → MODALITÀ USB SD.\n\n"
            "Quando sul display compare la modalità USB SD e Windows monta "
            "la microSD, premi OK: il Manager cercherà automaticamente "
            "l'unità GOATS e aprirà le sessioni CSV."
        )

        progress = QProgressDialog(
            "Attendo che Windows monti la microSD GOATS...",
            "ANNULLA", 0, 200, self
        )
        progress.setWindowTitle("Modalità USB SD")
        progress.setMinimumDuration(0)
        progress.setValue(0)

        mounted = None
        for step in range(200):
            if progress.wasCanceled():
                break
            QApplication.processEvents()
            drives = self._windows_goats_drives()
            if drives:
                mounted = drives[0]
                break
            progress.setValue(step + 1)
            time.sleep(0.10)
        progress.close()

        if mounted is None:
            QMessageBox.warning(
                self,
                "Modalità USB SD",
                "Windows non ha ancora montato un'unità contenente GOATS.\n\n"
                "Lascia il laptimer in MODALITÀ USB SD e riprova."
            )
            return

        root, goats_dir = mounted
        selected, _ = QFileDialog.getOpenFileNames(
            self,
            "Importa Sessioni dalla microSD",
            str(goats_dir),
            "Sessioni CSV (*.CSV *.csv);;Tutti i file (*.*)"
        )
        if not selected:
            self.statusBar().showMessage(
                f"MicroSD GOATS rilevata su {root}; nessuna sessione selezionata"
            )
            return

        imported, errors = self._import_csv_paths_into_manager(selected)
        QMessageBox.information(
            self,
            "Importa Sessioni",
            f"Unità GOATS: {root}\n"
            f"CSV selezionati: {len(selected)}\n"
            f"Sessioni importate: {imported}"
            + ("\n\nErrori:\n" + "\n".join(errors[:8]) if errors else "")
            + "\n\nAl termine usa Espelli/Rimozione sicura in Windows "
              "prima di riavviare il laptimer."
        )
        self.statusBar().showMessage(
            f"MicroSD {root}: importate {imported} sessioni"
        )

    def refresh_ports(self):
        current = self.port_combo.currentData()
        self.port_combo.clear()
        for port in list_ports.comports():
            label = f"{port.device} - {port.description}"
            self.port_combo.addItem(label, port.device)
        if current:
            for index in range(self.port_combo.count()):
                if self.port_combo.itemData(index) == current:
                    self.port_combo.setCurrentIndex(index)
                    break
        self.statusBar().showMessage(
            f"Rilevate {self.port_combo.count()} porte seriali"
        )

    @staticmethod
    def _encode_text(value, max_bytes=63):
        encoded = str(value).encode("utf-8")[:max_bytes]
        return struct.pack("<B", len(encoded)) + encoded

    def build_binary_catalog(self, paths=None, tracks=None):
        if paths is not None and tracks is not None:
            raise ValueError("Specificare paths oppure tracks, non entrambi.")

        if tracks is None:
            source_paths = (
                list(paths) if paths is not None
                else sorted(TRACKS_DIR.glob("*.json"))
            )
            tracks = []
            for path in source_paths:
                data = json.loads(Path(path).read_text(encoding="utf-8"))
                tracks.append(data)
        else:
            tracks = list(tracks)

        if not tracks:
            raise ValueError("Non ci sono circuiti da inviare.")
        if len(tracks) > 50:
            raise ValueError("Il catalogo supporta al massimo 50 circuiti.")

        payload = bytearray()
        payload += b"GTC3"
        payload += struct.pack("<HH", 1, len(tracks))

        direction_codes = {
            "unspecified": 0,
            "clockwise": 1,
            "counterclockwise": 2,
        }

        for track in tracks:
            start = track["start_line"]
            sectors = track.get("sectors", [])
            if len(sectors) > 12:
                raise ValueError(
                    f"{track.get('name', 'Circuito')}: massimo 12 linee settore intermedie."
                )

            payload += self._encode_text(track.get("name", "Circuito"))
            payload += struct.pack(
                "<ddddfBB",
                float(start["lat1"]),
                float(start["lon1"]),
                float(start["lat2"]),
                float(start["lon2"]),
                float(track.get("trigger_radius_m", 20.0)),
                direction_codes.get(track.get("direction", "unspecified"), 0),
                # GTC3 memorizza il numero di LINEE split intermedie, non il
                # numero di settori reali. I settori reali sono len(sectors)+1.
                len(sectors),
            )

            for sector in sectors:
                payload += self._encode_text(sector.get("name", "Settore"))
                payload += struct.pack(
                    "<dddd",
                    float(sector["lat1"]),
                    float(sector["lon1"]),
                    float(sector["lat2"]),
                    float(sector["lon2"]),
                )

        return bytes(payload), len(tracks)

    @staticmethod
    def _decode_gtc3_text(payload, offset):
        if offset >= len(payload):
            raise ValueError("Catalogo circuiti incompleto.")
        length = payload[offset]
        offset += 1
        if offset + length > len(payload):
            raise ValueError("Testo circuito troncato.")
        value = payload[offset:offset + length].decode("utf-8", errors="replace")
        return value, offset + length

    @classmethod
    def parse_binary_catalog(cls, payload):
        if len(payload) < 8 or payload[:4] != b"GTC3":
            raise ValueError("Formato catalogo circuiti non valido.")
        version, count = struct.unpack_from("<HH", payload, 4)
        if version != 1 or count > 50:
            raise ValueError(
                f"Versione/catalogo non supportato: v{version}, circuiti={count}"
            )

        direction_names = {
            0: "unspecified",
            1: "clockwise",
            2: "counterclockwise",
        }

        tracks = []
        offset = 8
        for index in range(count):
            name, offset = cls._decode_gtc3_text(payload, offset)
            fixed_size = struct.calcsize("<ddddfBB")
            if offset + fixed_size > len(payload):
                raise ValueError(f"Circuito {index + 1}: dati troncati.")
            (
                lat1, lon1, lat2, lon2,
                trigger_radius_m, direction_code, sector_count
            ) = struct.unpack_from("<ddddfBB", payload, offset)
            offset += fixed_size
            if sector_count > 12:
                raise ValueError(
                    f"Circuito {index + 1}: numero linee settore intermedie non valido."
                )

            sectors = []
            for _ in range(sector_count):
                sector_name, offset = cls._decode_gtc3_text(payload, offset)
                sector_size = struct.calcsize("<dddd")
                if offset + sector_size > len(payload):
                    raise ValueError("Settore circuito troncato.")
                slat1, slon1, slat2, slon2 = struct.unpack_from(
                    "<dddd", payload, offset
                )
                offset += sector_size
                sectors.append({
                    "name": sector_name,
                    "lat1": slat1,
                    "lon1": slon1,
                    "lat2": slat2,
                    "lon2": slon2,
                })

            track_id = slugify(name)
            tracks.append({
                "schema_version": 3,
                "id": track_id,
                "name": name,
                "country": "",
                "direction": direction_names.get(direction_code, "unspecified"),
                "start_line": {
                    "lat1": lat1,
                    "lon1": lon1,
                    "lat2": lat2,
                    "lon2": lon2,
                },
                "trigger_radius_m": float(trigger_radius_m),
                "sectors": sectors,
            })

        if offset != len(payload):
            raise ValueError(
                f"Catalogo con {len(payload) - offset} byte extra non riconosciuti."
            )
        return tracks

    def _choose_laptimer_tracks(self, tracks):
        dialog = QDialog(self)
        dialog.setWindowTitle("Circuiti presenti nel laptimer")
        dialog.resize(620, 460)
        layout = QVBoxLayout(dialog)

        info = QLabel(
            "Seleziona i circuiti da scaricare nel catalogo locale del Manager."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        track_list = QListWidget()
        track_list.setSelectionMode(
            QAbstractItemView.SelectionMode.MultiSelection
        )
        for index, track in enumerate(tracks, start=1):
            split_line_count = len(track.get("sectors", []) or [])
            sector_count = real_sector_count(track)
            item_text = (
                f"{index:02d}  {track.get('name', 'Circuito')}  "
                f"• {sector_count} settori reali "
                f"({split_line_count} linee intermedie)"
            )
            track_list.addItem(item_text)
            track_list.item(track_list.count() - 1).setSelected(True)
        layout.addWidget(track_list, 1)

        actions = QHBoxLayout()
        select_all = QPushButton("SELEZIONA TUTTI")
        select_none = QPushButton("DESELEZIONA TUTTI")
        select_all.clicked.connect(
            lambda: [
                track_list.item(i).setSelected(True)
                for i in range(track_list.count())
            ]
        )
        select_none.clicked.connect(
            lambda: [
                track_list.item(i).setSelected(False)
                for i in range(track_list.count())
            ]
        )
        actions.addWidget(select_all)
        actions.addWidget(select_none)
        actions.addStretch()
        layout.addLayout(actions)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(
            "SCARICA SELEZIONATI"
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return []

        selected_rows = sorted(
            track_list.row(item)
            for item in track_list.selectedItems()
        )
        return [tracks[i] for i in selected_rows]

    def _read_tracks_from_connection(self, connection):
        """Legge e valida il catalogo usando una seriale già aperta.

        V5.4.11.6: durante l'invio incrementale la stessa connessione viene
        mantenuta aperta tra GTRK_GET e GTRK_BEGIN. Sul Guition la chiusura e
        riapertura ravvicinata della COM può provocare un reset USB/ESP32 e
        lasciare il Manager senza la risposta GTRK_READY.
        """
        connection.reset_input_buffer()
        connection.write(b"GTRK_GET\n")
        connection.flush()

        header = self._read_protocol_line(connection, timeout_seconds=6.0)
        match = re.fullmatch(
            r"GTRK_DATA\s+(\d+)\s+([0-9A-Fa-f]{8})",
            header,
        )
        if not match:
            if header.startswith("GTRK_ERR"):
                raise RuntimeError(header)
            raise RuntimeError(
                "Impossibile leggere il catalogo già presente sul laptimer. "
                "Invio annullato per evitare di cancellare circuiti esistenti. "
                f"Risposta: {header or 'nessuna risposta'}"
            )

        size = int(match.group(1))
        expected_crc = int(match.group(2), 16)
        if size < 8 or size > 60000:
            raise ValueError(f"Dimensione catalogo non valida: {size} byte")

        payload = self._read_exact(connection, size, timeout_seconds=15.0)
        ending = self._read_protocol_line(connection, timeout_seconds=4.0)
        if ending != "GTRK_END":
            raise RuntimeError(
                f"Fine trasferimento non valida: {ending or 'nessuna'}"
            )

        actual_crc = zlib.crc32(payload) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            raise ValueError(
                f"CRC catalogo errato: ricevuto {actual_crc:08X}, "
                f"atteso {expected_crc:08X}"
            )
        return self.parse_binary_catalog(payload)

    def _read_tracks_from_laptimer(self, port):
        """Legge e valida l'intero catalogo circuiti presente sul laptimer."""
        with serial.Serial(
            port=port,
            baudrate=115200,
            timeout=0.25,
            write_timeout=3.0,
        ) as connection:
            time.sleep(0.5)
            return self._read_tracks_from_connection(connection)

    @staticmethod
    def _track_merge_key(track):
        # Il protocollo GTC3 non trasporta l'id del JSON: sul laptimer
        # l'identità più stabile disponibile è quindi il nome normalizzato.
        return slugify(track.get("name") or track.get("id") or "")

    @classmethod
    def _merge_track_catalogs(cls, existing_tracks, selected_tracks):
        """Merge non distruttivo: aggiorna omonimi, aggiunge nuovi, conserva gli altri."""
        merged = list(existing_tracks)
        positions = {}
        for index, track in enumerate(merged):
            key = cls._track_merge_key(track)
            if key and key not in positions:
                positions[key] = index

        added = 0
        updated = 0
        for track in selected_tracks:
            key = cls._track_merge_key(track)
            if not key:
                raise ValueError("Circuito selezionato senza nome/id valido.")
            if key in positions:
                merged[positions[key]] = track
                updated += 1
            else:
                positions[key] = len(merged)
                merged.append(track)
                added += 1

        if len(merged) > 50:
            raise ValueError(
                f"Il catalogo risultante contiene {len(merged)} circuiti; "
                "il limite del laptimer è 50."
            )
        return merged, added, updated

    def download_tracks_from_laptimer(self):
        port = self.port_combo.currentData()
        if not port:
            QMessageBox.warning(
                self, "Porta USB",
                "Selezionare la porta COM del laptimer."
            )
            return

        try:
            self.statusBar().showMessage(
                "Lettura catalogo circuiti dal laptimer..."
            )
            QApplication.processEvents()

            with serial.Serial(
                port=port,
                baudrate=115200,
                timeout=3.0,
                write_timeout=3.0,
            ) as connection:
                time.sleep(0.4)
                connection.reset_input_buffer()
                connection.write(b"GTRK_GET\n")
                connection.flush()

                header = connection.readline().decode(
                    "ascii", errors="replace"
                ).strip()
                match = re.fullmatch(
                    r"GTRK_DATA\s+(\d+)\s+([0-9A-Fa-f]{8})",
                    header,
                )
                if not match:
                    if header.startswith("GTRK_ERR"):
                        raise RuntimeError(header)
                    raise RuntimeError(
                        "Il firmware non supporta il download circuiti "
                        f"oppure ha risposto in modo inatteso: {header or 'nessuna risposta'}"
                    )

                size = int(match.group(1))
                expected_crc = int(match.group(2), 16)
                if size < 8 or size > 60000:
                    raise ValueError(
                        f"Dimensione catalogo non valida: {size} byte"
                    )

                payload = self._read_exact(
                    connection, size, timeout_seconds=15.0
                )
                ending = connection.readline().decode(
                    "ascii", errors="replace"
                ).strip()
                if ending != "GTRK_END":
                    raise RuntimeError(
                        f"Fine trasferimento non valida: {ending or 'nessuna'}"
                    )

            actual_crc = zlib.crc32(payload) & 0xFFFFFFFF
            if actual_crc != expected_crc:
                raise ValueError(
                    f"CRC catalogo errato: ricevuto {actual_crc:08X}, "
                    f"atteso {expected_crc:08X}"
                )

            tracks = self.parse_binary_catalog(payload)
            if not tracks:
                QMessageBox.information(
                    self, "Circuiti",
                    "Il laptimer non contiene circuiti."
                )
                return

            selected = self._choose_laptimer_tracks(tracks)
            if not selected:
                self.statusBar().showMessage(
                    "Download circuiti annullato"
                )
                return

            conflicts = []
            for track in selected:
                path = TRACKS_DIR / f"{slugify(track['id'])}.json"
                if path.exists():
                    conflicts.append(path.name)

            overwrite = True
            if conflicts:
                answer = QMessageBox.question(
                    self,
                    "Circuiti già presenti",
                    f"{len(conflicts)} circuito/i selezionato/i esistono già "
                    "nel catalogo locale.\n\nSovrascriverli?",
                    QMessageBox.StandardButton.Yes |
                    QMessageBox.StandardButton.No |
                    QMessageBox.StandardButton.Cancel,
                )
                if answer == QMessageBox.StandardButton.Cancel:
                    return
                overwrite = answer == QMessageBox.StandardButton.Yes

            saved = 0
            skipped = 0
            used_ids = set()
            for track in selected:
                base_id = slugify(track.get("id") or track.get("name"))
                track["id"] = base_id
                path = TRACKS_DIR / f"{base_id}.json"

                if path.exists() and not overwrite:
                    skipped += 1
                    continue

                # Avoid duplicates inside the same received catalog.
                candidate = base_id
                suffix = 2
                while candidate in used_ids:
                    candidate = f"{base_id}_{suffix}"
                    suffix += 1
                used_ids.add(candidate)
                if candidate != base_id:
                    track["id"] = candidate
                    path = TRACKS_DIR / f"{candidate}.json"

                path.write_text(
                    json.dumps(track, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                saved += 1

            self.refresh_tracks()
            self.statusBar().showMessage(
                f"Scaricati {saved} circuiti dal laptimer"
            )
            QMessageBox.information(
                self,
                "Download circuiti completato",
                f"Circuiti salvati: {saved}\n"
                f"Circuiti saltati: {skipped}\n\n"
                "I circuiti sono ora disponibili nell'Editor Circuiti."
            )

        except Exception as exc:
            QMessageBox.critical(
                self,
                "Errore download circuiti",
                str(exc),
            )
            self.statusBar().showMessage(
                "Download circuiti non riuscito"
            )

    def _send_simple_command(self, command, expected_prefix):
        port = self.port_combo.currentData()
        if not port:
            QMessageBox.warning(self, "Porta USB", "Selezionare una porta COM.")
            return False
        try:
            with serial.Serial(port, 115200, timeout=2.0, write_timeout=2.0) as link:
                time.sleep(0.4)
                link.reset_input_buffer()
                link.write((command + "\n").encode("ascii"))
                link.flush()
                deadline = time.time() + 4.0
                while time.time() < deadline:
                    line = link.readline().decode("ascii", errors="ignore").strip()
                    if not line:
                        continue
                    if line.startswith(expected_prefix):
                        return True
                    if line.startswith("GTRK_ERR") or line.startswith("GSES_ERR"):
                        raise RuntimeError(line)
                raise TimeoutError("Nessuna conferma dal laptimer")
        except Exception as exc:
            QMessageBox.critical(self, "Errore USB", str(exc))
            return False

    def delete_selected_from_laptimer(self):
        row = self.track_list.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Circuito", "Selezionare il circuito da eliminare.")
            return
        name = self.track_list.currentItem().text()
        if QMessageBox.question(self, "Conferma", f"Eliminare dal laptimer: {name}?") != QMessageBox.StandardButton.Yes:
            return
        if self._send_simple_command(f"GTRK_DELETE {row}", "GTRK_DELETE_OK"):
            QMessageBox.information(self, "Laptimer", "Circuito eliminato dal laptimer.")

    def clear_laptimer(self):
        if QMessageBox.question(self, "Conferma", "Eliminare tutti i circuiti dal laptimer?") != QMessageBox.StandardButton.Yes:
            return
        if self._send_simple_command("GTRK_CLEAR", "GTRK_CLEAR_OK"):
            QMessageBox.information(self, "Laptimer", "Archivio circuiti svuotato.")

    def send_to_laptimer(self):
        port = self.port_combo.currentData()
        if not port:
            QMessageBox.warning(
                self, "Porta USB", "Selezionare la porta COM del laptimer."
            )
            return

        selected_rows = sorted({
            index.row() for index in self.track_list.selectedIndexes()
            if 0 <= index.row() < len(self.files)
        })
        if not selected_rows:
            QMessageBox.warning(
                self,
                "Circuiti",
                "Seleziona uno o più circuiti nell'elenco da inviare al laptimer."
            )
            return

        try:
            selected_tracks = []
            selected_names = []
            for row in selected_rows:
                path = self.files[row]
                data = json.loads(path.read_text(encoding="utf-8"))
                selected_tracks.append(data)
                selected_names.append(data.get("name", path.stem))

            # V5.4.11.6: UNA SOLA apertura della COM per lettura + invio.
            # La V5.4.10.5--V5.4.11.6 apriva la seriale per GTRK_GET, la
            # chiudeva e la riapriva subito per GTRK_BEGIN. Sul Guition questo
            # può innescare un reset della USB/ESP32 tra le due operazioni.
            self.statusBar().showMessage(
                "Connessione al laptimer e lettura catalogo esistente..."
            )
            QApplication.processEvents()

            with serial.Serial(
                port=port,
                baudrate=115200,
                timeout=0.25,
                write_timeout=5.0,
            ) as connection:
                time.sleep(0.5)
                existing_tracks = self._read_tracks_from_connection(connection)

                merged_tracks, added, updated = self._merge_track_catalogs(
                    existing_tracks, selected_tracks
                )
                preserved = max(0, len(existing_tracks) - updated)

                preview_names = "\n".join(
                    f"• {name}" for name in selected_names[:8]
                )
                if len(selected_names) > 8:
                    preview_names += f"\n• ... altri {len(selected_names) - 8}"

                answer = QMessageBox.question(
                    self,
                    "Invia circuiti",
                    f"Circuiti selezionati: {len(selected_tracks)}\n"
                    f"Già presenti sul laptimer: {len(existing_tracks)}\n"
                    f"Nuovi: {added}\n"
                    f"Aggiornati: {updated}\n"
                    f"Conservati invariati: {preserved}\n"
                    f"Totale finale: {len(merged_tracks)}\n\n"
                    f"{preview_names}\n\n"
                    "Gli altri circuiti presenti sul laptimer NON verranno cancellati.\n"
                    "Procedere?"
                )
                if answer != QMessageBox.StandardButton.Yes:
                    self.statusBar().showMessage("Invio circuiti annullato")
                    return

                payload, track_count = self.build_binary_catalog(
                    tracks=merged_tracks
                )
                crc = zlib.crc32(payload) & 0xFFFFFFFF

                self.statusBar().showMessage(
                    f"Invio catalogo unificato ({track_count} circuiti)..."
                )
                QApplication.processEvents()

                # Piccola pausa di protocollo, senza mai chiudere la COM.
                time.sleep(0.12)
                connection.reset_input_buffer()
                connection.write(
                    f"GTRK_BEGIN {len(payload)} {crc:08X}\n".encode("ascii")
                )
                connection.flush()
                response = self._read_protocol_line(
                    connection, timeout_seconds=5.0
                )
                if response != "GTRK_READY":
                    raise RuntimeError(
                        "Il laptimer non ha risposto correttamente a GTRK_BEGIN. "
                        f"Risposta: {response or 'nessuna'}. "
                        "La porta COM è stata mantenuta aperta per evitare reset USB."
                    )

                connection.write(payload)
                connection.flush()
                response = self._read_protocol_line(
                    connection, timeout_seconds=8.0
                )
                if not response.startswith("GTRK_OK"):
                    raise RuntimeError(
                        "Trasferimento rifiutato dal laptimer: "
                        f"{response or 'nessuna risposta'}"
                    )

            self.statusBar().showMessage(
                f"Invio completato: {len(selected_tracks)} selezionati, "
                f"{track_count} totali sul laptimer"
            )
            QMessageBox.information(
                self,
                "Trasferimento completato",
                f"Circuiti selezionati inviati: {len(selected_tracks)}\n"
                f"Nuovi: {added}\n"
                f"Aggiornati: {updated}\n"
                f"Circuiti conservati: {preserved}\n"
                f"Totale sul laptimer: {track_count}."
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Errore trasferimento USB",
                str(exc),
            )
            self.statusBar().showMessage("Trasferimento USB non riuscito")

    @staticmethod
    def _read_exact(connection, size, timeout_seconds=30.0):
        data = bytearray()
        deadline = time.monotonic() + timeout_seconds
        last_progress = time.monotonic()

        while len(data) < size:
            now = time.monotonic()
            if now >= deadline:
                break

            # Blocchi moderati evitano richieste seriali troppo grandi.
            requested = min(4096, size - len(data))
            chunk = connection.read(requested)

            if chunk:
                data.extend(chunk)
                last_progress = time.monotonic()
                # Ogni progresso rinnova il margine, utile su PC più lenti.
                deadline = last_progress + timeout_seconds
                QApplication.processEvents()
            elif not connection.is_open:
                break

        if len(data) != size:
            raise TimeoutError(
                f"Ricevuti {len(data)} byte su {size} attesi. "
                "Verificare goats_usb_tracks.h con invio USB a blocchi."
            )
        return bytes(data)

    @staticmethod
    def _read_protocol_line(connection, timeout_seconds=20.0):
        """Attende una riga protocollo senza dipendere dal timeout seriale breve."""
        deadline = time.monotonic() + timeout_seconds
        raw = bytearray()
        while time.monotonic() < deadline:
            chunk = connection.read(1)
            if chunk:
                if chunk == b"\n":
                    return raw.decode("ascii", errors="replace").strip()
                if chunk != b"\r":
                    raw.extend(chunk)
                # A protocol line is intentionally small.
                if len(raw) > 512:
                    raise RuntimeError("Riga protocollo USB troppo lunga.")
            else:
                QApplication.processEvents()
                time.sleep(0.01)
        return raw.decode("ascii", errors="replace").strip()

    def _download_session_archive_v2(self, connection):
        connection.reset_input_buffer()
        connection.write(b"GSES2_GET\n")
        connection.flush()

        # Since V11.0.1.34+ the firmware reconstructs the complete trace
        # from SD before sending GSES2_BEGIN. Thousands of CSV points can make
        # the first response take several seconds.
        header = self._read_protocol_line(
            connection, timeout_seconds=25.0
        )

        match = re.match(
            r"^GSES2_BEGIN\s+(\d+)\s+([0-9A-Fa-f]{8})"
            r"\s+(\d+)\s+(\d+)$",
            header,
        )
        if not match:
            raise RuntimeError(
                f"Risposta protocollo V2 non valida: "
                f"{header or 'nessuna'}"
            )

        total_size = int(match.group(1))
        expected_crc = int(match.group(2), 16)
        chunk_size = int(match.group(3))
        chunk_count = int(match.group(4))

        if total_size < 0 or chunk_size <= 0 or chunk_count < 0:
            raise RuntimeError("Parametri archivio non validi.")

        progress = QProgressDialog(
            "Download sessioni dal GOATS RT...",
            "Annulla",
            0,
            max(total_size, 1),
            self,
        )
        progress.setWindowTitle("Trasferimento sessioni")
        progress.setWindowModality(
            Qt.WindowModality.WindowModal
        )
        progress.setMinimumDuration(0)
        progress.setValue(0)

        payload = bytearray()
        expected_index = 0

        connection.write(b"GSES2_READY\n")
        connection.flush()

        try:
            while expected_index < chunk_count:
                if progress.wasCanceled():
                    connection.write(b"GSES2_CANCEL\n")
                    connection.flush()
                    raise RuntimeError(
                        "Download annullato dall'utente."
                    )

                line = self._read_protocol_line(
                    connection, timeout_seconds=8.0
                )

                if line.startswith("GSES2_ERR"):
                    raise RuntimeError(
                        f"Errore laptimer: {line}"
                    )

                chunk_match = re.match(
                    r"^GSES2_CHUNK\s+(\d+)\s+(\d+)"
                    r"\s+([0-9A-Fa-f]{8})$",
                    line,
                )
                if not chunk_match:
                    raise RuntimeError(
                        f"Intestazione pacchetto non valida: "
                        f"{line or 'nessuna'}"
                    )

                packet_index = int(chunk_match.group(1))
                packet_size = int(chunk_match.group(2))
                packet_crc = int(chunk_match.group(3), 16)

                if packet_index != expected_index:
                    connection.write(
                        f"GSES2_NACK {expected_index}\n".encode(
                            "ascii"
                        )
                    )
                    connection.flush()
                    continue

                if packet_size <= 0 or packet_size > chunk_size:
                    connection.write(
                        f"GSES2_NACK {packet_index}\n".encode(
                            "ascii"
                        )
                    )
                    connection.flush()
                    continue

                packet = self._read_exact(
                    connection,
                    packet_size,
                    timeout_seconds=5.0,
                )

                actual_packet_crc = (
                    zlib.crc32(packet) & 0xFFFFFFFF
                )
                if actual_packet_crc != packet_crc:
                    connection.write(
                        f"GSES2_NACK {packet_index}\n".encode(
                            "ascii"
                        )
                    )
                    connection.flush()
                    continue

                payload.extend(packet)
                connection.write(
                    f"GSES2_ACK {packet_index}\n".encode("ascii")
                )
                connection.flush()

                expected_index += 1
                progress.setValue(
                    min(len(payload), total_size)
                )
                progress.setLabelText(
                    f"Ricevuti {len(payload)} di "
                    f"{total_size} byte"
                )
                QApplication.processEvents()

            end_line = self._read_protocol_line(
                connection, timeout_seconds=8.0
            )

            if end_line != "GSES2_END":
                raise RuntimeError(
                    f"Fine trasferimento non valida: "
                    f"{end_line or 'nessuna'}"
                )

        finally:
            progress.close()

        if len(payload) != total_size:
            raise RuntimeError(
                f"Dimensione errata: ricevuti {len(payload)} "
                f"byte su {total_size}."
            )

        actual_crc = zlib.crc32(payload) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            raise RuntimeError(
                f"CRC archivio non valido: {actual_crc:08X} "
                f"invece di {expected_crc:08X}"
            )

        return bytes(payload)

    def _download_session_archive_legacy(self, connection):
        """Fallback per firmware che espongono ancora GSES_GET."""
        connection.reset_input_buffer()
        connection.write(b"GSES_GET\n")
        connection.flush()

        header = self._read_protocol_line(
            connection, timeout_seconds=25.0
        )
        match = re.match(
            r"^GSES_BEGIN\s+(\d+)\s+([0-9A-Fa-f]{8})$",
            header,
        )
        if not match:
            raise RuntimeError(
                f"Risposta protocollo legacy non valida: "
                f"{header or 'nessuna'}"
            )

        total_size = int(match.group(1))
        expected_crc = int(match.group(2), 16)
        if total_size < 8 or total_size > 16 * 1024 * 1024:
            raise RuntimeError(
                f"Dimensione archivio legacy non valida: {total_size}"
            )

        payload = self._read_exact(
            connection,
            total_size,
            timeout_seconds=30.0,
        )
        actual_crc = zlib.crc32(payload) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            raise RuntimeError(
                f"CRC archivio legacy non valido: {actual_crc:08X} "
                f"invece di {expected_crc:08X}"
            )
        return payload

    def _download_session_archive_auto(self, port):
        """
        Preferisce GSES2. Se il firmware dichiara esplicitamente un comando
        sconosciuto/non supportato, riapre la seriale e prova GSES_GET.
        Non effettua fallback prematuro su timeout brevi: il firmware può
        impiegare tempo a rileggere la traccia completa dalla microSD.
        """
        v2_error = None
        try:
            with serial.Serial(
                port, 115200, timeout=0.10, write_timeout=5.0
            ) as connection:
                time.sleep(0.7)
                return self._download_session_archive_v2(connection)
        except Exception as exc:
            v2_error = exc

        # Reopen the port cleanly before legacy protocol, so no pending state
        # or binary data from a failed V2 transfer can contaminate the stream.
        time.sleep(0.8)
        try:
            with serial.Serial(
                port, 115200, timeout=0.10, write_timeout=5.0
            ) as connection:
                time.sleep(0.7)
                return self._download_session_archive_legacy(connection)
        except Exception as legacy_exc:
            raise RuntimeError(
                "Download sessioni non riuscito.\n\n"
                f"Protocollo V2: {v2_error}\n"
                f"Protocollo legacy: {legacy_exc}"
            ) from legacy_exc

    def _download_session_trace(self, port, session_id):
        """Scarica Sxxxxxx.CSV direttamente via FatFS sul laptimer."""
        with serial.Serial(
            port, 115200, timeout=0.10, write_timeout=5.0
        ) as connection:
            time.sleep(0.5)
            connection.reset_input_buffer()
            connection.write(
                f"GSD_SESSION {int(session_id)}\n".encode("ascii")
            )
            connection.flush()

            # Il firmware V11.0.1.40 può dover rimontare la microSD prima
            # di aprire Sxxxxxx.CSV. GSDT_WAIT REMOUNT è uno stato intermedio,
            # non un errore: continuiamo ad attendere GSDT_BEGIN oppure un
            # vero GSDT_ERR. Timeout ampio per i tentativi di remount.
            deadline = time.monotonic() + 25.0
            header = ""
            match = None
            while time.monotonic() < deadline:
                remaining = max(0.2, deadline - time.monotonic())
                header = self._read_protocol_line(
                    connection, timeout_seconds=remaining
                )
                if not header:
                    break
                if header.startswith("GSDT_WAIT"):
                    QApplication.processEvents()
                    continue
                if header.startswith("GSDT_ERR"):
                    raise RuntimeError(
                        f"Traccia sessione {session_id} non disponibile: {header}"
                    )
                match = re.match(
                    r"^GSDT_BEGIN\s+(\d+)\s+(\d+)$",
                    header,
                )
                if match:
                    break
                # Ignora eventuali righe diagnostiche non appartenenti al
                # payload binario e continua ad attendere l'header traccia.

            if not match:
                raise RuntimeError(
                    f"Traccia sessione {session_id} non disponibile: "
                    f"{header or 'nessuna risposta dopo remount'}"
                )

            size = int(match.group(1))
            returned_id = int(match.group(2))
            if returned_id != int(session_id):
                raise RuntimeError(
                    f"ID traccia inatteso: {returned_id} invece di {session_id}"
                )
            if size <= 0 or size > 64 * 1024 * 1024:
                raise RuntimeError(
                    f"Dimensione traccia non valida: {size}"
                )

            payload = self._read_exact(
                connection, size, timeout_seconds=90.0
            )
            end_line = self._read_protocol_line(
                connection, timeout_seconds=10.0
            )
            if end_line != "GSDT_END":
                raise RuntimeError(
                    f"Fine traccia non valida: {end_line or 'nessuna'}"
                )
            return payload

    @staticmethod
    def _attach_sd_trace_csv(session, csv_bytes):
        """Converte Sxxxxxx.CSV nella struttura trace usata dal Manager."""
        text = csv_bytes.decode("utf-8", errors="replace")
        rows = []
        reader = csv.DictReader(
            line for line in text.splitlines()
            if line and not line.startswith("#")
        )
        for row in reader:
            try:
                rows.append({
                    "elapsed_ms": int(float(row.get("elapsed_ms", 0) or 0)),
                    "lap": int(float(row.get("lap", 0) or 0)),
                    "latitude": float(row.get("latitude", 0) or 0),
                    "longitude": float(row.get("longitude", 0) or 0),
                    "speed_kmh": float(row.get("speed_kmh", 0) or 0),
                    "hdop": float(row.get("hdop", 0) or 0),
                    "satellites": int(float(row.get("satellites", 0) or 0)),
                })
            except (TypeError, ValueError):
                continue

        if not rows or not session.get("laps"):
            return 0

        for lap in session["laps"]:
            lap["trace"] = []

        free_mode = (
            session.get("track_name") == "REGISTRAZIONE LIBERA"
            and len(session["laps"]) == 1
        )

        first_elapsed = {}
        accepted = 0
        for row in rows:
            target = None
            if free_mode:
                target = session["laps"][0]
            else:
                for lap in session["laps"]:
                    if int(lap.get("number", 0)) == row["lap"]:
                        target = lap
                        break
            if target is None:
                continue

            lap_no = int(target.get("number", 0))
            if lap_no not in first_elapsed:
                first_elapsed[lap_no] = row["elapsed_ms"]
            rel_ms = max(
                0, row["elapsed_ms"] - first_elapsed[lap_no]
            )
            target["trace"].append({
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "elapsed_ms": rel_ms,
                "speed_kmh": row["speed_kmh"],
                "hdop": row["hdop"],
                "satellites": row["satellites"],
            })
            accepted += 1

        # If metadata metrics were zero, derive useful session values from trace.
        if accepted:
            speeds = [r["speed_kmh"] for r in rows]
            hdops = [r["hdop"] for r in rows if r["hdop"] > 0]
            sats = [r["satellites"] for r in rows if r["satellites"] > 0]
            if float(session.get("max_speed_kmh", 0) or 0) <= 0 and speeds:
                session["max_speed_kmh"] = round(max(speeds), 3)
            if float(session.get("average_speed_kmh", 0) or 0) <= 0 and speeds:
                session["average_speed_kmh"] = round(sum(speeds) / len(speeds), 3)
            if float(session.get("average_hdop", 0) or 0) <= 0 and hdops:
                session["average_hdop"] = round(sum(hdops) / len(hdops), 3)
            if float(session.get("average_satellites", 0) or 0) <= 0 and sats:
                session["average_satellites"] = round(sum(sats) / len(sats), 3)

        return accepted

    @staticmethod
    def _parse_session_archive(payload):
        offset = 0

        def take(fmt):
            nonlocal offset
            size = struct.calcsize(fmt)
            if offset + size > len(payload):
                raise ValueError("Archivio sessioni troncato.")
            values = struct.unpack_from(fmt, payload, offset)
            offset += size
            return values[0] if len(values) == 1 else values

        def take_text():
            nonlocal offset
            length = take("<B")
            if offset + length > len(payload):
                raise ValueError("Stringa sessione troncata.")
            value = payload[offset:offset + length].decode(
                "utf-8", errors="replace"
            )
            offset += length
            return value

        if len(payload) < 8 or payload[:4] not in (b"GSA2", b"GSA3"):
            magic = payload[:4].hex(" ").upper() if payload else "VUOTO"
            raise ValueError(
                f"Formato sessioni non riconosciuto (magic={magic}, byte={len(payload)})."
            )
        archive_magic = payload[:4]
        offset = 4
        version, count = take("<HH")
        if not ((archive_magic == b"GSA2" and version in (1, 2)) or
                (archive_magic == b"GSA3" and version == 3)):
            raise ValueError(
                f"Versione archivio non supportata: {archive_magic.decode(errors='replace')} v{version}"
            )

        sessions = []
        for _ in range(count):
            session_id = take("<I")
            date = take_text()
            session_time = take_text()
            track_name = take_text()
            duration_ms, best_lap_ms, last_lap_ms = take("<III")
            max_speed, average_speed, average_hdop, average_satellites = take(
                "<ffff"
            )
            lap_count = take("<H")
            laps = []
            for _ in range(lap_count):
                number = take("<H")
                lap_time_ms = take("<I")
                lap_max, lap_average = take("<ff")
                trace = []
                if version >= 2:
                    trace_count = take("<H")
                    for _ in range(trace_count):
                        latitude_e7, longitude_e7 = take("<ii")
                        elapsed_tick, speed_tenth = take("<HH")
                        trace.append({
                            "latitude": latitude_e7 / 10000000.0,
                            "longitude": longitude_e7 / 10000000.0,
                            "elapsed_ms": elapsed_tick * (40 if archive_magic == b"GSA3" else 100),
                            "speed_kmh": speed_tenth / 10.0,
                        })
                laps.append({
                    "number": number,
                    "lap_time_ms": lap_time_ms,
                    "lap_time": TrackManager._format_ms(lap_time_ms),
                    "max_speed_kmh": round(lap_max, 3),
                    "average_speed_kmh": round(lap_average, 3),
                    "trace": trace,
                })
            sessions.append({
                "schema_version": 1,
                "format": "GOATS_RT_SESSION",
                "session_id": session_id,
                "date": date,
                "time": session_time,
                "track_name": track_name,
                "duration_ms": duration_ms,
                "duration": TrackManager._format_duration(duration_ms),
                "best_lap_ms": best_lap_ms,
                "best_lap": TrackManager._format_ms(best_lap_ms),
                "last_lap_ms": last_lap_ms,
                "last_lap": TrackManager._format_ms(last_lap_ms),
                "max_speed_kmh": round(max_speed, 3),
                "average_speed_kmh": round(average_speed, 3),
                "average_hdop": round(average_hdop, 3),
                "average_satellites": round(average_satellites, 3),
                "lap_count": len(laps),
                "laps": laps,
            })
        if offset != len(payload):
            raise ValueError("Dati extra non previsti nell'archivio.")
        return sessions

    @staticmethod
    def _format_ms(milliseconds):
        if not milliseconds:
            return "--:--.---"
        minutes = milliseconds // 60000
        seconds = (milliseconds // 1000) % 60
        millis = milliseconds % 1000
        return f"{minutes:02d}:{seconds:02d}.{millis:03d}"

    @staticmethod
    def _format_duration(milliseconds):
        seconds = milliseconds // 1000
        return f"{seconds // 60:02d}:{seconds % 60:02d}"

    def open_session_analysis(self):
        dialog = SessionAnalysisDialog(self)
        dialog.exec()

    def download_sessions(self):
        port = self.port_combo.currentData()
        if not port:
            QMessageBox.warning(
                self, "Porta USB", "Selezionare la porta COM del laptimer."
            )
            return
        destination = QFileDialog.getExistingDirectory(
            self, "Cartella di destinazione sessioni"
        )
        if not destination:
            return

        try:
            self.statusBar().showMessage(
                "Preparazione archivio sessioni dal laptimer..."
            )
            QApplication.processEvents()
            payload = self._download_session_archive_auto(port)

            sessions = self._parse_session_archive(payload)
            if not sessions:
                QMessageBox.information(
                    self,
                    "Archivio vuoto",
                    "Nel laptimer non sono presenti sessioni."
                )
                return

            selector = SessionSelectionDialog(sessions, self)
            if selector.exec() != QDialog.DialogCode.Accepted:
                self.statusBar().showMessage(
                    "Download sessioni annullato"
                )
                return

            sessions = selector.selected_sessions()

            # V5.4.11.6: metadata via GSES2, trace completa direttamente
            # dalla microSD con GSD_GET Sxxxxxx.CSV. Il laptimer non deve più
            # ricostruire grandi blob in RAM.
            trace_errors = []
            for pos, session in enumerate(sessions, start=1):
                session_id = int(session.get("session_id", 0) or 0)
                if session_id <= 0:
                    continue
                sd_name = f"S{session_id:06d}.CSV"
                self.statusBar().showMessage(
                    f"Traccia GPS {pos}/{len(sessions)}: {sd_name}"
                )
                QApplication.processEvents()
                try:
                    csv_payload = self._download_session_trace(port, session_id)
                    points = self._attach_sd_trace_csv(
                        session, csv_payload
                    )
                    if points == 0:
                        raise RuntimeError(
                            "file ricevuto ma nessun punto GPS valido"
                        )
                except Exception as trace_exc:
                    trace_errors.append(
                        f"{sd_name}: {trace_exc}"
                    )

            if trace_errors:
                QMessageBox.critical(
                    self,
                    "Errore traccia GPS",
                    "Le sessioni sono presenti, ma la traccia GPS non è stata "
                    "scaricata correttamente.\n\n"
                    + "\n".join(trace_errors[:8])
                    + "\n\nNessuna sessione verrà importata con 0 punti."
                )
                self.statusBar().showMessage(
                    "Download annullato: traccia GPS non disponibile"
                )
                return

            # V5.4.11.6: ogni sessione viene archiviata in una cartella
            # leggibile "<circuito>_<data>". Sessioni dello stesso circuito
            # e della stessa giornata condividono la cartella.
            base_output_dir = Path(destination)
            base_output_dir.mkdir(parents=True, exist_ok=True)

            summary_rows = []
            downloaded_json_files = []
            used_output_dirs = set()
            for session in sessions:
                safe_track = slugify(session["track_name"]) or "circuito"
                raw_date = str(session.get("date", "") or "").strip()
                date_token = re.sub(r"[^0-9A-Za-z_-]+", "-", raw_date).strip("-")
                if not date_token:
                    date_token = datetime.now().strftime("%Y-%m-%d")
                folder_name = f"{safe_track}_{date_token}"
                output_dir = base_output_dir / folder_name
                output_dir.mkdir(parents=True, exist_ok=True)
                used_output_dirs.add(output_dir)

                file_base = (
                    f"session_{session['session_id']:03d}_"
                    f"{safe_track}"
                )
                session_json_path = output_dir / f"{file_base}.json"
                session_json_path.write_text(
                    json.dumps(session, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                downloaded_json_files.append(session_json_path)
                with (output_dir / f"{file_base}_laps.csv").open(
                    "w", newline="", encoding="utf-8-sig"
                ) as csv_file:
                    writer = csv.DictWriter(
                        csv_file,
                        fieldnames=[
                            "number", "lap_time", "lap_time_ms",
                            "max_speed_kmh", "average_speed_kmh",
                        ],
                        delimiter=";",
                    )
                    writer.writeheader()
                    lap_fields = [
                        "number", "lap_time", "lap_time_ms",
                        "max_speed_kmh", "average_speed_kmh",
                    ]
                    for lap in session["laps"]:
                        writer.writerow({
                            key: lap.get(key, "")
                            for key in lap_fields
                        })

                # La traccia GPS non appartiene al CSV riepilogo giri:
                # viene esportata in un file punti separato.
                trace_rows = []
                for lap in session["laps"]:
                    for point_index, point in enumerate(lap.get("trace", []), start=1):
                        trace_rows.append({
                            "lap": lap.get("number", 0),
                            "point": point_index,
                            "elapsed_ms": point.get("elapsed_ms", 0),
                            "latitude": point.get("latitude", 0),
                            "longitude": point.get("longitude", 0),
                            "speed_kmh": point.get("speed_kmh", 0),
                        })
                if trace_rows:
                    with (output_dir / f"{file_base}_trace.csv").open(
                        "w", newline="", encoding="utf-8-sig"
                    ) as trace_file:
                        trace_writer = csv.DictWriter(
                            trace_file,
                            fieldnames=[
                                "lap", "point", "elapsed_ms",
                                "latitude", "longitude", "speed_kmh",
                            ],
                            delimiter=";",
                        )
                        trace_writer.writeheader()
                        trace_writer.writerows(trace_rows)

                summary_rows.append({
                    "session_id": session["session_id"],
                    "date": session["date"],
                    "time": session["time"],
                    "track_name": session["track_name"],
                    "lap_count": session["lap_count"],
                    "duration": session["duration"],
                    "best_lap": session["best_lap"],
                    "last_lap": session["last_lap"],
                    "max_speed_kmh": session["max_speed_kmh"],
                    "average_speed_kmh": session["average_speed_kmh"],
                    "average_hdop": session["average_hdop"],
                    "average_satellites": session["average_satellites"],
                })

            # Crea riepilogo e archivio JSON in ogni cartella circuito/data.
            grouped = {}
            for session in sessions:
                safe_track = slugify(session["track_name"]) or "circuito"
                raw_date = str(session.get("date", "") or "").strip()
                date_token = re.sub(r"[^0-9A-Za-z_-]+", "-", raw_date).strip("-")
                if not date_token:
                    date_token = datetime.now().strftime("%Y-%m-%d")
                folder = base_output_dir / f"{safe_track}_{date_token}"
                grouped.setdefault(folder, []).append(session)

            for folder, folder_sessions in grouped.items():
                fields = [
                    "session_id", "date", "time", "track_name",
                    "lap_count", "duration", "best_lap", "last_lap",
                    "max_speed_kmh", "average_speed_kmh",
                    "average_hdop", "average_satellites",
                ]
                with (folder / "sessions_summary.csv").open(
                    "w", newline="", encoding="utf-8-sig"
                ) as csv_file:
                    writer = csv.DictWriter(
                        csv_file, fieldnames=fields, delimiter=";"
                    )
                    writer.writeheader()
                    for session in folder_sessions:
                        writer.writerow({
                            "session_id": session["session_id"],
                            "date": session["date"],
                            "time": session["time"],
                            "track_name": session["track_name"],
                            "lap_count": session["lap_count"],
                            "duration": session["duration"],
                            "best_lap": session["best_lap"],
                            "last_lap": session["last_lap"],
                            "max_speed_kmh": session["max_speed_kmh"],
                            "average_speed_kmh": session["average_speed_kmh"],
                            "average_hdop": session["average_hdop"],
                            "average_satellites": session["average_satellites"],
                        })

                (folder / "goats_sessions_archive.json").write_text(
                    json.dumps({
                        "schema_version": 1,
                        "format": "GOATS_RT_SESSION_ARCHIVE",
                        "session_count": len(folder_sessions),
                        "sessions": folder_sessions,
                    }, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )

            # Importa immediatamente i JSON appena scaricati nel database
            # SQLite condiviso del Manager.
            imported = 0
            import_errors = []
            store = SessionStore(DB_PATH)
            try:
                for json_path in downloaded_json_files:
                    try:
                        for parsed_session in parse_any(json_path):
                            store.import_session(parsed_session)
                            imported += 1
                    except Exception as import_exc:
                        import_errors.append(
                            f"{json_path.name}: {import_exc}"
                        )
            finally:
                try:
                    store.conn.close()
                except Exception:
                    pass

            QMessageBox.information(
                self,
                "Sessioni scaricate",
                f"Esportate {len(sessions)} sessioni selezionate.\n"
                f"Importate nel Manager: {imported}.\n\n"
                f"Cartelle create: {len(grouped)}\n"
                f"Destinazione base:\n{base_output_dir}"
                + (
                    "\n\nAvvisi traccia GPS:\n" + "\n".join(trace_errors[:5])
                    if trace_errors else ""
                )
                + (
                    "\n\nErrori importazione:\n" + "\n".join(import_errors[:5])
                    if import_errors else ""
                ),
            )
            self.statusBar().showMessage(
                f"Scaricate {len(sessions)} sessioni; importate {imported} nel Manager"
            )
        except Exception as exc:
            QMessageBox.critical(self, "Errore download sessioni", str(exc))

    def clear_sessions_laptimer(self):
        if QMessageBox.question(
            self,
            "Conferma",
            "Eliminare definitivamente tutte le sessioni dal laptimer?",
        ) != QMessageBox.StandardButton.Yes:
            return
        if self._send_simple_command("GSES_CLEAR", "GSES_CLEAR_OK"):
            QMessageBox.information(
                self, "Sessioni", "Archivio sessioni eliminato definitivamente."
            )

    def export_catalog(self):
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Esporta catalogo",
            "goats_tracks.json",
            "File JSON (*.json)",
        )
        if not filename:
            return

        tracks = []
        for path in sorted(TRACKS_DIR.glob("*.json")):
            try:
                tracks.append(
                    json.loads(path.read_text(encoding="utf-8"))
                )
            except Exception:
                pass

        catalog = {
            "schema_version": 3,
            "format": "GOATS_RT_TRACK_CATALOG",
            "track_count": len(tracks),
            "tracks": tracks,
        }
        Path(filename).write_text(
            json.dumps(catalog, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        QMessageBox.information(
            self,
            "Esportazione completata",
            f"Creato catalogo con {len(tracks)} circuiti.",
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--mode", choices=["tracks", "sessions", "assistnow", "all"],
                        default="tracks")
    args, qt_args = parser.parse_known_args()
    application = QApplication([sys.argv[0], *qt_args])
    application.setApplicationName("GOATS RT Manager Tools")
    window = TrackManager(args.mode)
    window.show()
    sys.exit(application.exec())
