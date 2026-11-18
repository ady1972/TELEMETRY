from __future__ import annotations
import json,sys,subprocess,os,re,math,shutil
from pathlib import Path

# V5.4.10.6 QT WINDOWS FIX
# Python 3.14 on Windows can find qwindows.dll but fail to resolve the Qt DLLs
# if PATH/QT_PLUGIN_PATH contains entries inherited from another application.
# Prepare an isolated PySide6 runtime BEFORE importing Qt.
def _prepare_pyside6_windows_runtime():
    if os.name != "nt":
        return

    # Never inherit a foreign Qt installation (Anaconda, QGIS, old PyQt, etc.).
    for key in (
        "QT_PLUGIN_PATH",
        "QT_QPA_PLATFORM_PLUGIN_PATH",
        "QML2_IMPORT_PATH",
    ):
        os.environ.pop(key, None)

    candidates = []
    for base in sys.path:
        try:
            p = Path(base) / "PySide6"
            if p.is_dir():
                candidates.append(p)
        except Exception:
            pass

    if not candidates:
        return

    pyside_dir = candidates[0]
    platforms_dir = pyside_dir / "plugins" / "platforms"

    # Explicit platform-plugin directory used by Qt.
    if platforms_dir.is_dir():
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(platforms_dir)

    # qwindows.dll depends on Qt6Core/Gui/Widgets DLLs located in PySide6.
    os.environ["PATH"] = (
        str(pyside_dir)
        + os.pathsep
        + str(Path(sys.executable).resolve().parent)
        + os.pathsep
        + os.environ.get("PATH", "")
    )

    # Python >=3.8 uses restricted DLL search rules on Windows.
    if hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(str(pyside_dir))
        except OSError:
            pass

_prepare_pyside6_windows_runtime()

from PySide6.QtCore import Qt,QUrl,QTimer,QPointF,Signal
from PySide6.QtGui import QIcon,QPixmap,QPainter,QColor,QFont,QShortcut,QKeySequence
from PySide6.QtWidgets import QApplication,QMainWindow,QWidget,QFrame,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QStackedWidget,QTableWidget,QTableWidgetItem,QHeaderView,QLineEdit,QFileDialog,QMessageBox,QSplitter,QComboBox,QAbstractItemView,QProgressDialog,QGraphicsLineItem,QGraphicsEllipseItem,QScrollArea,QDialog,QTextEdit,QCheckBox
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCharts import QChart,QChartView,QLineSeries,QValueAxis
from goats_serial_sessions import SerialSessionsPanel
from goats_formats import parse_any
from goats_store import SessionStore
from goats_exporters import export_csv,export_json,export_gpx
from goats_track_editor import TrackManager,set_tracks_dir

APP_DIR=Path(__file__).resolve().parent
DATA_DIR=APP_DIR/'data'; DATA_DIR.mkdir(exist_ok=True)
SETTINGS_PATH=DATA_DIR/'manager_settings.json'
DB_FILENAME='goats_rt_sessions.sqlite3'
LOGO=APP_DIR/'goats_rt_logo.png'; TRACKS_DIR=APP_DIR/'tracks'

def _read_manager_settings():
    try:
        if SETTINGS_PATH.is_file():
            data=json.loads(SETTINGS_PATH.read_text(encoding='utf-8'))
            return data if isinstance(data,dict) else {}
    except Exception:
        pass
    return {}

def _write_manager_settings(data):
    SETTINGS_PATH.parent.mkdir(parents=True,exist_ok=True)
    tmp=SETTINGS_PATH.with_suffix('.tmp')
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    tmp.replace(SETTINGS_PATH)

def _configured_sessions_dir():
    raw=str(_read_manager_settings().get('sessions_dir','') or '').strip()
    return Path(raw).expanduser() if raw else DATA_DIR

def _prepare_sessions_dir(folder):
    folder=Path(folder).expanduser()
    folder.mkdir(parents=True,exist_ok=True)
    # Verifica reale di scrittura: utile per cartelle cloud/NAS momentaneamente offline.
    probe=folder/'.goats_write_test.tmp'
    probe.write_text('ok',encoding='utf-8')
    probe.unlink(missing_ok=True)
    return folder

def _configured_tracks_dir():
    raw=str(_read_manager_settings().get('tracks_dir','') or '').strip()
    return Path(raw).expanduser() if raw else TRACKS_DIR

def _prepare_tracks_dir(folder):
    folder=Path(folder).expanduser()
    folder.mkdir(parents=True,exist_ok=True)
    probe=folder/'.goats_tracks_write_test.tmp'
    probe.write_text('ok',encoding='utf-8')
    probe.unlink(missing_ok=True)
    return folder


def fmt_ms(ms):
    if not ms:return '--:--.---'
    return f'{ms//60000:02d}:{(ms//1000)%60:02d}.{ms%1000:03d}'
def fmt_dur(ms):
    s=ms//1000; return f'{s//3600:02d}:{(s//60)%60:02d}:{s%60:02d}'

class NavButton(QPushButton):
    def __init__(self,text):super().__init__(text);self.setCheckable(True);self.setMinimumHeight(44)

class AnalysisChartView(QChartView):
    cursorMoved = Signal(float, float)
    cursorLeft = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)

    def mouseMoveEvent(self, event):
        chart = self.chart()
        series = chart.series() if chart is not None else []
        if chart is not None and series:
            view_pos = event.position()
            scene_pos = self.mapToScene(int(view_pos.x()), int(view_pos.y()))
            chart_pos = chart.mapFromScene(scene_pos)
            if chart.plotArea().contains(chart_pos):
                value = chart.mapToValue(chart_pos, series[0])
                self.cursorMoved.emit(float(value.x()), float(chart_pos.y()))
            else:
                self.cursorLeft.emit()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.cursorLeft.emit()
        super().leaveEvent(event)

class Main(QMainWindow):
    def __init__(self):
        super().__init__(); self.current_session_id=None
        self.configured_sessions_dir=_configured_sessions_dir()
        self.storage_fallback_reason=''
        try:
            active_dir=_prepare_sessions_dir(self.configured_sessions_dir)
            self.store=SessionStore(active_dir/DB_FILENAME,cloud_safe=(active_dir.resolve()!=DATA_DIR.resolve()))
        except Exception as exc:
            self.storage_fallback_reason=str(exc)
            active_dir=_prepare_sessions_dir(DATA_DIR)
            self.store=SessionStore(active_dir/DB_FILENAME,cloud_safe=False)
        self.active_sessions_dir=Path(self.store.path).parent
        self.configured_tracks_dir=_configured_tracks_dir()
        self.tracks_storage_fallback_reason=''
        try:
            self.active_tracks_dir=_prepare_tracks_dir(self.configured_tracks_dir)
        except Exception as exc:
            self.tracks_storage_fallback_reason=str(exc)
            self.active_tracks_dir=_prepare_tracks_dir(TRACKS_DIR)
        set_tracks_dir(self.active_tracks_dir)
        self.embedded_tools={}
        self._analysis_hover_series=[]
        self._analysis_hover_rows={}
        self._analysis_hover_series_by_name={}
        self._analysis_cursor_line=None
        self._analysis_cursor_dot=None
        self._analysis_cursor_chart_view=None
        self._analysis_chart_views=[]
        self._analysis_chart_views_by_lap={}
        self._analysis_focus_lap=None
        self._analysis_lap_stats_by_no={}
        self._analysis_best_lap_no=None
        self._analysis_show_brakes=False
        # Modalità condivisa tra tabella analisi e tabelle sulla mappa:
        # 'brake' = solo frenata, 'speed' = solo velocità curva, 'both' = entrambe.
        self._analysis_brake_table_mode='both'
        self._analysis_brake_events=[]
        self._analysis_brake_groups=[]
        self._analysis_replay_running=False
        self._last_map_html=''
        self._lap_table_updating=False
        self._comparison_session_ids=[]
        self._analysis_return_page=None
        self.compare_page_index=None
        # Cache dei dati circuito e del giro potenziale. Viene invalidata
        # dopo import/cancellazione e quando si apre l'editor Circuiti.
        self._track_data_cache={}
        self._potential_lap_cache={}
        # Cloud Sync file-level per condividere le sessioni con l'app Android senza
        # dover aprire lo stesso database SQLite da due dispositivi.
        self.cloud_folder=''
        self.cloud_auto=False
        self._cloud_seen={}
        self._load_cloud_config()
        self.setWindowTitle('GOATS RT Manager V5.4.15.5 - Cloud Sync Android/PC'); self.resize(1440,880); self.setMinimumSize(1100,700)
        self._ui(); self._style(); self.refresh_sessions()
        self.db_refresh_timer=QTimer(self);self.db_refresh_timer.setInterval(1500);self.db_refresh_timer.timeout.connect(self.refresh_sessions);self.db_refresh_timer.start()
        self.cloud_timer=QTimer(self);self.cloud_timer.setInterval(15000);self.cloud_timer.timeout.connect(self._cloud_auto_tick);self.cloud_timer.start()
    def _ui(self):
        root=QWidget();self.setCentralWidget(root);hl=QHBoxLayout(root);hl.setContentsMargins(0,0,0,0);hl.setSpacing(0)
        side=QFrame();side.setObjectName('sidebar');side.setFixedWidth(230);sl=QVBoxLayout(side);sl.setContentsMargins(18,20,18,20)
        if LOGO.exists():
            logo=QLabel();logo.setAlignment(Qt.AlignCenter);logo.setPixmap(QPixmap(str(LOGO)).scaled(110,110,Qt.KeepAspectRatio,Qt.SmoothTransformation));sl.addWidget(logo)
        n=QLabel('GOATS RT');n.setObjectName('appName');n.setAlignment(Qt.AlignCenter);sl.addWidget(n)
        v=QLabel('MANAGER V5.4.15.5');v.setObjectName('appVersion');v.setAlignment(Qt.AlignCenter);sl.addWidget(v);sl.addSpacing(18)
        self.nav=[]
        nav_names=['Dashboard','Sessioni','Analisi','Importa Sessioni','Circuiti','AssistNow','Configurazione GNSS','Informazioni','Impostazioni']
        for i,name in enumerate(nav_names):
            b=NavButton(name);b.clicked.connect(lambda checked=False,x=i:self.show_page(x));sl.addWidget(b);self.nav.append(b)
        sl.addStretch();st=QLabel('GRT8 • GSA3 • GSA2\nSQLite • GPS 25 Hz');st.setObjectName('sideStatus');sl.addWidget(st);hl.addWidget(side)
        self.stack=QStackedWidget();hl.addWidget(self.stack,1)
        self.stack.addWidget(self.dashboard())
        self.stack.addWidget(self.sessions_page())
        self.stack.addWidget(self.analysis_page())
        self.stack.addWidget(self.import_page())
        self.stack.addWidget(self.tracks_page())
        self.stack.addWidget(self.assistnow_page())
        self.stack.addWidget(self.gnss_page())
        self.stack.addWidget(self.info_page())
        self.stack.addWidget(self.settings_page())
        # Pagina interna di confronto: non entra nella sidebar, così gli indici
        # storici di Dashboard/Sessioni/Analisi/etc. restano invariati.
        self.compare_page_index=self.stack.count()
        self.stack.addWidget(self.compare_sessions_page())
        self.show_page(0)
    def gnss_page(self):
        import goats_gnss as gnss
        import struct
        w,l=self.page('Configurazione GNSS','u-blox via adattatore USB-UART. La modalità ponte tramite laptimer richiede un firmware dedicato.')
        card=QFrame();card.setObjectName('card');v=QVBoxLayout(card)
        v.addWidget(QLabel('Connessione diretta al ricevitore (UART 3,3 V, GND comune)'))
        line=QHBoxLayout();v.addLayout(line)
        port=QComboBox();port.setMinimumWidth(170);line.addWidget(port)
        def refresh():
            previous=port.currentText();port.clear();port.addItems(gnss.ports());port.setCurrentText(previous)
        refresh()
        b=QPushButton('Aggiorna porte');b.clicked.connect(refresh);line.addWidget(b)
        baud=QComboBox();baud.addItems([str(x) for x in gnss.BAUDS]);baud.setCurrentText('230400');line.addWidget(baud)
        out=QTextEdit();out.setReadOnly(True);out.setMaximumHeight(180);v.addWidget(out)
        def detect():
            try:
                result=gnss.identify(port.currentText(),int(baud.currentText()))
                out.setPlainText('Ricevitore rilevato\n'+result)
            except Exception as e:QMessageBox.warning(w,'GNSS',str(e))
        b=QPushButton('LEGGI IDENTITÀ GNSS (MON-VER)');b.clicked.connect(detect);v.addWidget(b)
        v.addWidget(QLabel('Profilo sperimentale: modifiche applicate solo dopo conferma ACK del ricevitore.'))
        settings=QHBoxLayout();v.addLayout(settings)
        freq=QComboBox();freq.addItems(['10','20','25']);freq.setCurrentText('20');settings.addWidget(QLabel('Hz:'));settings.addWidget(freq)
        newbaud=QComboBox();newbaud.addItems([str(x) for x in gnss.BAUDS]);newbaud.setCurrentText('230400');settings.addWidget(QLabel('Nuovo baud:'));settings.addWidget(newbaud)
        persistent=QCheckBox('Salva anche in memoria non volatile (se supportata)');v.addWidget(persistent)
        def apply_rate():
            hz=int(freq.currentText())
            if QMessageBox.question(w,'Conferma GNSS',f'Impostare {hz} Hz? La frequenza potrebbe non essere supportata dal chipset.\nEsegui prima un backup tramite u-center.')!=QMessageBox.Yes:return
            try:
                gnss.valset(port.currentText(),int(baud.currentText()),gnss.CFG_RATE_MEAS,struct.pack('<H',1000//hz),persistent.isChecked())
                out.append(f'CFG-RATE-MEAS: richiesta {hz} Hz, ACK ricevuto. Verificare la frequenza reale.')
            except Exception as e:QMessageBox.warning(w,'GNSS',str(e))
        b=QPushButton('Imposta frequenza');b.clicked.connect(apply_rate);v.addWidget(b)
        def apply_baud():
            old=int(baud.currentText());new=int(newbaud.currentText())
            if old==new:return
            if QMessageBox.question(w,'Cambio baud',f'Cambiare UART1 da {old} a {new}? Potrebbe essere necessario riconnettere il ricevitore.')!=QMessageBox.Yes:return
            try:
                gnss.valset(port.currentText(),old,gnss.CFG_UART1_BAUDRATE,struct.pack('<I',new),persistent.isChecked())
                baud.setCurrentText(str(new));out.append(f'Comando cambio baud inviato. Rileggi identità a {new} per confermare.')
            except Exception as e:QMessageBox.warning(w,'GNSS',str(e)+'\nIl baud potrebbe essere già cambiato: prova a riconnetterti al nuovo valore.')
        b=QPushButton('Imposta baud UART1');b.clicked.connect(apply_baud);v.addWidget(b)
        v.addWidget(QLabel('Tramite laptimer: NON ANCORA DISPONIBILE — richiede ponte UART bidirezionale nel firmware RLCD.'))
        l.addWidget(card);l.addStretch();return w

    def _embedded_tool_page(self, mode, title, subtitle):
        w,l=self.page(title,subtitle)
        host=QFrame();host.setObjectName('card')
        host_layout=QVBoxLayout(host)
        host_layout.setContentsMargins(8,8,8,8)
        host_layout.setSpacing(6)

        tool=TrackManager(mode)
        content,toolbar=tool.detach_for_embedding()
        self.embedded_tools[mode]=tool

        if toolbar is not None:
            toolbar.setParent(host)
            host_layout.addWidget(toolbar)
        if content is not None:
            content.setParent(host)
            host_layout.addWidget(content,1)

        l.addWidget(host,1)
        return w

    def tracks_page(self):
        return self._embedded_tool_page(
            'tracks',
            'Circuiti',
            'Crea, modifica, invia e importa i circuiti direttamente nel Manager.'
        )

    def assistnow_page(self):
        return self._embedded_tool_page(
            'assistnow',
            'AssistNow',
            'Gestisci più prototipi AssistNow con descrizione, registrazione ZTP, download dati, invio al M9N e diagnostica.'
        )

    def open_tool_mode(self,mode):
        # Compatibilità con vecchi richiami: porta alla pagina interna corrispondente.
        page_index={'tracks':4,'sessions':5,'assistnow':6}.get(mode,0)
        self.show_page(page_index)

    def open_track_editor(self):
        self.show_page(4)

    def page(self,title,sub):
        w=QWidget();l=QVBoxLayout(w);l.setContentsMargins(28,24,28,24);h=QLabel(title);h.setObjectName('pageTitle');s=QLabel(sub);s.setObjectName('pageSub');s.setWordWrap(True);l.addWidget(h);l.addWidget(s);return w,l
    def make_metric_card(self,label,value):
        f=QFrame();f.setObjectName('metric');l=QVBoxLayout(f);a=QLabel(label);a.setObjectName('muted');b=QLabel(value);b.setObjectName('metricValue');l.addWidget(a);l.addWidget(b);f.value_label=b;return f
    def card(self,title,desc,button,cb):
        f=QFrame();f.setObjectName('card');l=QVBoxLayout(f);t=QLabel(title);t.setObjectName('cardTitle');d=QLabel(desc);d.setWordWrap(True);d.setObjectName('muted');b=QPushButton(button);b.setObjectName('primary');b.clicked.connect(cb);l.addWidget(t);l.addWidget(d);l.addStretch();l.addWidget(b);return f
    def dashboard(self):
        w,l=self.page('Dashboard','Archivio storico, telemetria ad alta risoluzione e analisi delle traiettorie.')
        row=QHBoxLayout();self.m_sessions=self.make_metric_card('Sessioni','0');self.m_points=self.make_metric_card('Punti GPS','0');self.m_hours=self.make_metric_card('Ore registrate','0.0');self.m_best=self.make_metric_card('Best lap archivio','--:--.---')
        for x in (self.m_sessions,self.m_points,self.m_hours,self.m_best):row.addWidget(x)
        l.addLayout(row);r2=QHBoxLayout();r2.addWidget(self.card('Importa sessioni','Importa CSV diretto dalla telemetria, GRT8, GSA3/GSA2 o JSON legacy.','IMPORTA',lambda:self.show_page(3)));r2.addWidget(self.card('Analisi telemetria','Mappa satellitare, heatmap velocità e confronto giri.','ANALIZZA',lambda:self.show_page(2)));l.addLayout(r2);l.addStretch();return w
    def sessions_page(self):
        w,l=self.page('Sessioni','Database SQLite locale. Doppio click per aprire la sessione in Analisi.')
        top=QHBoxLayout();self.search=QLineEdit();self.search.setPlaceholderText('Cerca circuito, data, tipo o note...');self.search.textChanged.connect(self.refresh_sessions);top.addWidget(self.search,1);b=QPushButton('IMPORTA');b.clicked.connect(lambda:self.show_page(3));top.addWidget(b);cmp=QPushButton('CONFRONTA SESSIONI');cmp.setObjectName('primary');cmp.clicked.connect(self.compare_selected_sessions);top.addWidget(cmp);n=QPushButton('NOTE SESSIONE');n.clicked.connect(self.edit_selected_session_notes);top.addWidget(n);d=QPushButton('ELIMINA');d.clicked.connect(self.delete_selected);top.addWidget(d);l.addLayout(top)
        hint=QLabel('Per il confronto seleziona almeno due sessioni con Ctrl+click o Shift+click, poi premi CONFRONTA SESSIONI.');hint.setObjectName('muted');l.addWidget(hint)
        self.table=QTableWidget(0,12);self.table.setHorizontalHeaderLabels(['ID','Data','Ora','Circuito','Tipo','Formato','Punti','Giri','Vmax','Best','Potenziale','Note']);self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents);self.table.horizontalHeader().setSectionResizeMode(3,QHeaderView.Stretch);self.table.horizontalHeader().setSectionResizeMode(11,QHeaderView.Stretch);self.table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter);self.table.setShowGrid(True);self.table.setGridStyle(Qt.SolidLine);self.table.setStyleSheet('QTableWidget{gridline-color:#34404d;} QHeaderView::section{border-right:1px solid #34404d;border-bottom:1px solid #34404d;}');self.table.setSelectionBehavior(QAbstractItemView.SelectRows);self.table.setSelectionMode(QAbstractItemView.ExtendedSelection);self.table.setEditTriggers(QAbstractItemView.NoEditTriggers);self.table.doubleClicked.connect(self.open_selected_analysis)
        for c in range(self.table.columnCount()):
            hi=self.table.horizontalHeaderItem(c)
            if hi is not None:hi.setTextAlignment((Qt.AlignLeft|Qt.AlignVCenter) if c==11 else Qt.AlignCenter)
        l.addWidget(self.table,1);return w
    def compare_sessions_page(self):
        w,l=self.page(
            'Confronta Sessioni',
            'Riepilogo affiancato delle sessioni selezionate. Usa APRI o il doppio click per entrare nell’analisi; INDIETRO AL CONFRONTO riporta qui.'
        )
        top=QHBoxLayout()
        back=QPushButton('← TORNA A SESSIONI');back.clicked.connect(lambda:self.show_page(1));top.addWidget(back)
        self.compare_info=QLabel('Nessuna sessione selezionata.');self.compare_info.setObjectName('muted');top.addWidget(self.compare_info,1)
        open_btn=QPushButton('APRI SESSIONE SELEZIONATA');open_btn.clicked.connect(self._open_selected_comparison_session);top.addWidget(open_btn)
        l.addLayout(top)
        self.compare_table=QTableWidget(0,12)
        self.compare_table.setHorizontalHeaderLabels(['Apri','ID','Data','Ora','Circuito','Tipo','Giri','Best Lap','Giro potenziale','V media','V max','Note'])
        self.compare_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.compare_table.horizontalHeader().setSectionResizeMode(4,QHeaderView.Stretch)
        self.compare_table.horizontalHeader().setSectionResizeMode(11,QHeaderView.Stretch)
        self.compare_table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        self.compare_table.setShowGrid(True)
        self.compare_table.setGridStyle(Qt.SolidLine)
        self.compare_table.setStyleSheet('QTableWidget{gridline-color:#34404d;} QHeaderView::section{border-right:1px solid #34404d;border-bottom:1px solid #34404d;}')
        for c in range(self.compare_table.columnCount()):
            hi=self.compare_table.horizontalHeaderItem(c)
            if hi is not None:hi.setTextAlignment((Qt.AlignLeft|Qt.AlignVCenter) if c==11 else Qt.AlignCenter)
        self.compare_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.compare_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.compare_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.compare_table.cellDoubleClicked.connect(lambda r,c:self._open_comparison_row(r))
        l.addWidget(self.compare_table,1)
        return w

    def selected_ids(self):
        if not hasattr(self,'table'):
            return []
        rows=sorted({idx.row() for idx in self.table.selectionModel().selectedRows()})
        ids=[]
        for r in rows:
            item=self.table.item(r,0)
            if item is not None:
                try: ids.append(int(item.text()))
                except Exception: pass
        return ids

    def compare_selected_sessions(self):
        ids=self.selected_ids()
        if len(ids)<2:
            QMessageBox.information(
                self,'Confronta Sessioni',
                'Seleziona almeno due sessioni nella tabella con Ctrl+click o Shift+click.'
            )
            return
        self._comparison_session_ids=list(ids)
        self._populate_comparison_table(ids)
        self.show_page(self.compare_page_index)

    def _comparison_stats(self,sid):
        sess=self.store.session(sid)
        if sess is None:
            return None
        laps=list(self.store.laps(sid))
        points_all=list(self.store.points(sid,None))

        # Stessa logica dell'Analisi: elimina eventuale giro ancora aperto nei
        # vecchi database e i giri anomali sotto l'80% del Giro 2.
        open_final_lap=None
        if str(sess['source_format'] or '')=='SDCSV':
            point_laps=sorted({int(p['lap'] or 0) for p in points_all if int(p['lap'] or 0)>0})
            if point_laps: open_final_lap=point_laps[-1]
        positive=[
            lap for lap in laps
            if int(lap['lap_time_ms'] or 0)>0
            and (open_final_lap is None or int(lap['lap'])!=open_final_lap)
        ]
        ref=next((lap for lap in positive if int(lap['lap'])==2),None)
        ref_ms=int(ref['lap_time_ms'] or 0) if ref is not None else 0
        valid=[lap for lap in positive if not ref_ms or int(lap['lap_time_ms'] or 0)>=ref_ms*0.80]
        valid_nos={int(lap['lap']) for lap in valid}
        speeds=[float(p['speed_kmh'] or 0.0) for p in points_all if int(p['lap'] or 0) in valid_nos]
        best=min((int(lap['lap_time_ms']) for lap in valid),default=0)
        vmax=max(speeds,default=float(sess['max_speed_kmh'] or 0.0))
        vavg=(sum(speeds)/len(speeds)) if speeds else float(sess['avg_speed_kmh'] or 0.0)
        potential=self._session_potential_lap_details(sid).get('potential_ms',0)
        return {
            'session':sess,'lap_count':len(valid),'best_ms':best,
            'potential_ms':potential,'vavg':vavg,'vmax':vmax,
        }

    def _populate_comparison_table(self,ids=None):
        if not hasattr(self,'compare_table'):
            return
        ids=list(ids if ids is not None else self._comparison_session_ids)
        stats=[]
        for sid in ids:
            st=self._comparison_stats(sid)
            if st is not None: stats.append(st)
        self.compare_table.setRowCount(len(stats))
        best_global=min((st['best_ms'] for st in stats if st['best_ms']>0),default=0)
        potential_global=min((st.get('potential_ms',0) for st in stats if st.get('potential_ms',0)>0),default=0)
        vmax_global=max((st['vmax'] for st in stats),default=0.0)
        for r,st in enumerate(stats):
            s=st['session'];sid=int(s['id'])
            btn=QPushButton('APRI');btn.clicked.connect(lambda checked=False,x=sid:self.open_analysis_from_comparison(x));self.compare_table.setCellWidget(r,0,btn)
            note=(s['notes'] or '').strip().replace('\n',' ')
            if len(note)>90: note=note[:87]+'...'
            vals=[sid,s['date'],s['time'],s['track_name'],s['session_type'],st['lap_count'],fmt_ms(st['best_ms']),fmt_ms(st.get('potential_ms',0)),f"{st['vavg']:.1f} km/h",f"{st['vmax']:.1f} km/h",note]
            for c,val in enumerate(vals,start=1):
                item=QTableWidgetItem(str(val));item.setData(Qt.UserRole,sid);item.setTextAlignment((Qt.AlignLeft|Qt.AlignVCenter) if c==11 else Qt.AlignCenter)
                if c==7 and best_global and st['best_ms']==best_global:
                    item.setBackground(QColor(46,125,50));item.setForeground(QColor(255,255,255));f=item.font();f.setBold(True);item.setFont(f)
                if c==8 and potential_global and st.get('potential_ms',0)==potential_global:
                    item.setBackground(QColor(190,0,190));item.setForeground(QColor(255,255,255));f=item.font();f.setBold(True);item.setFont(f)
                if c==10 and vmax_global and abs(st['vmax']-vmax_global)<1e-9:
                    f=item.font();f.setBold(True);item.setFont(f)
                self.compare_table.setItem(r,c,item)
        if stats:
            tracks=sorted({str(st['session']['track_name'] or '') for st in stats if str(st['session']['track_name'] or '')})
            extra=f" • Circuito: {tracks[0]}" if len(tracks)==1 else (f" • {len(tracks)} circuiti" if tracks else '')
            self.compare_info.setText(f"{len(stats)} sessioni a confronto{extra} • Best verde • Potenziale migliore fucsia")
            self.compare_table.selectRow(0)
        else:
            self.compare_info.setText('Nessuna sessione disponibile per il confronto.')

    def _comparison_sid_at_row(self,row):
        if row<0 or row>=self.compare_table.rowCount(): return None
        item=self.compare_table.item(row,1)
        if item is None:return None
        try:return int(item.data(Qt.UserRole) or item.text())
        except Exception:return None

    def _open_comparison_row(self,row):
        sid=self._comparison_sid_at_row(row)
        if sid:self.open_analysis_from_comparison(sid)

    def _open_selected_comparison_session(self):
        self._open_comparison_row(self.compare_table.currentRow())

    def open_analysis_from_comparison(self,sid):
        self._analysis_return_page=self.compare_page_index
        if hasattr(self,'analysis_back_btn'):
            self.analysis_back_btn.setVisible(True)
        self.show_page(2)
        idx=self.session_combo.findData(int(sid))
        if idx>=0:self.session_combo.setCurrentIndex(idx)

    def _back_from_analysis(self):
        target=self._analysis_return_page
        self._analysis_return_page=None
        if hasattr(self,'analysis_back_btn'):self.analysis_back_btn.setVisible(False)
        if target==self.compare_page_index:
            self._populate_comparison_table(self._comparison_session_ids)
            self.show_page(self.compare_page_index)
        else:
            self.show_page(1)

    def analysis_page(self):
        w,l=self.page(
            'Analisi',
            'Giri e curve velocità sono affiancati: selezionando una riga il Manager porta subito alla curva corrispondente. '
            'La mappa mostra split e tempi settore del giro attivo, oltre all hover continuo della velocità.'
        )

        top=QHBoxLayout()
        self.analysis_back_btn=QPushButton('← INDIETRO AL CONFRONTO')
        self.analysis_back_btn.clicked.connect(self._back_from_analysis)
        self.analysis_back_btn.setVisible(False)
        top.addWidget(self.analysis_back_btn)
        self.session_combo=QComboBox()
        self.session_combo.currentIndexChanged.connect(self.analysis_session_changed)
        top.addWidget(QLabel('Sessione'))
        top.addWidget(self.session_combo,1)

        self.select_all_laps_btn=QPushButton('SELEZIONA TUTTO')
        self.select_all_laps_btn.clicked.connect(self._select_all_laps)
        top.addWidget(self.select_all_laps_btn)

        self.clear_all_laps_btn=QPushButton('DESELEZIONA TUTTO')
        self.clear_all_laps_btn.clicked.connect(self._clear_all_laps)
        top.addWidget(self.clear_all_laps_btn)

        self.fullscreen_map_btn=QPushButton('MAPPA SCHERMO INTERO')
        self.fullscreen_map_btn.clicked.connect(self._analysis_open_fullscreen_map)
        top.addWidget(self.fullscreen_map_btn)

        self.replay_btn=QPushButton('▶ ANIMA GIRI')
        self.replay_btn.setCheckable(True)
        self.replay_btn.toggled.connect(self._analysis_replay_toggled)
        top.addWidget(self.replay_btn)
        self.replay_speed_combo=QComboBox()
        self.replay_speed_combo.addItem('0,5x',0.5)
        self.replay_speed_combo.addItem('1x',1.0)
        self.replay_speed_combo.setCurrentIndex(1)
        self.replay_speed_combo.currentIndexChanged.connect(self._analysis_replay_speed_changed)
        self.replay_speed_combo.setToolTip('Velocità animazione dei giri selezionati')
        top.addWidget(self.replay_speed_combo)
        self.replay_reset_btn=QPushButton('↺')
        self.replay_reset_btn.setToolTip("Riporta i pallini all'inizio dei giri")
        self.replay_reset_btn.clicked.connect(self._analysis_replay_reset)
        top.addWidget(self.replay_reset_btn)

        self.brake_analysis_btn=QPushButton('ANALISI FRENATE + CURVE')
        self.brake_analysis_btn.clicked.connect(self._analysis_open_braking_analysis)
        self.brake_analysis_btn.setToolTip('Confronta frenata, velocità di ingresso, minima e uscita curva dei giri selezionati')
        top.addWidget(self.brake_analysis_btn)

        e=QPushButton('ESPORTA')
        e.clicked.connect(self.export_current)
        top.addWidget(e)
        l.addLayout(top)

        # Riepilogo sessione sempre visibile sopra mappa/giri.
        self.session_summary=QTableWidget(1,5)
        self.session_summary.setHorizontalHeaderLabels(
            ['Giri validi','Best Lap','Giro potenziale','Velocità max','Velocità media']
        )
        self.session_summary.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.session_summary.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        self.session_summary.verticalHeader().setVisible(False)
        self.session_summary.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.session_summary.setSelectionMode(QAbstractItemView.NoSelection)
        self.session_summary.setFocusPolicy(Qt.NoFocus)
        self.session_summary.setMinimumHeight(66)
        self.session_summary.setMaximumHeight(82)
        l.addWidget(self.session_summary)

        # Note descrittive persistenti della sessione. Salvate nel database SQLite
        # locale e incluse anche nell'export JSON della sessione.
        notes_frame=QFrame();notes_frame.setObjectName('card')
        notes_layout=QHBoxLayout(notes_frame);notes_layout.setContentsMargins(12,10,12,10);notes_layout.setSpacing(10)
        notes_label=QLabel('NOTE SESSIONE');notes_label.setObjectName('cardTitle');notes_layout.addWidget(notes_label)
        self.session_notes_edit=QTextEdit();self.session_notes_edit.setPlaceholderText('Aggiungi note descrittive: assetto, gomme, pressione, meteo, pilota, anomalie, osservazioni...');self.session_notes_edit.setMinimumHeight(62);self.session_notes_edit.setMaximumHeight(96);notes_layout.addWidget(self.session_notes_edit,1)
        self.save_session_notes_btn=QPushButton('SALVA NOTE');self.save_session_notes_btn.clicked.connect(self.save_current_session_notes);notes_layout.addWidget(self.save_session_notes_btn)
        l.addWidget(notes_frame)

        # Layout Analisi: mappa sopra; sotto due pannelli affiancati.
        # A sinistra tabella giri/settori, a destra curve velocità.
        main_split=QSplitter(Qt.Vertical)

        self.map=QWebEngineView()
        self._map_ready=False
        self._pending_map_hover=None
        self.map.loadFinished.connect(self._analysis_map_loaded)
        main_split.addWidget(self.map)

        laps_charts_split=QSplitter(Qt.Horizontal)

        lap_panel=QWidget()
        lap_panel_layout=QVBoxLayout(lap_panel)
        lap_panel_layout.setContentsMargins(0,0,0,0)
        lap_panel_layout.setSpacing(6)
        lap_title=QLabel('GIRI E SETTORI')
        lap_title.setObjectName('cardTitle')
        lap_panel_layout.addWidget(lap_title)

        self.lap_table=QTableWidget(0,7)
        self.lap_table.setHorizontalHeaderLabels(
            ['Mostra','Giro','Tempo','V min','V media','V max','Punti']
        )
        self.lap_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.lap_table.horizontalHeader().setStretchLastSection(True)
        self.lap_table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        self.lap_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.lap_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.lap_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.lap_table.setMinimumWidth(520)
        self.lap_table.itemChanged.connect(self._lap_check_changed)
        self.lap_table.itemSelectionChanged.connect(self._lap_row_selected)
        lap_panel_layout.addWidget(self.lap_table,1)
        laps_charts_split.addWidget(lap_panel)

        chart_panel=QWidget()
        chart_panel_layout=QVBoxLayout(chart_panel)
        chart_panel_layout.setContentsMargins(0,0,0,0)
        chart_panel_layout.setSpacing(6)
        chart_title=QLabel('CURVE VELOCITÀ')
        chart_title.setObjectName('cardTitle')
        chart_panel_layout.addWidget(chart_title)

        self.chart_scroll=QScrollArea()
        self.chart_scroll.setWidgetResizable(True)
        self.chart_scroll.setFrameShape(QFrame.NoFrame)
        self.chart_container=QWidget()
        self.chart_layout=QVBoxLayout(self.chart_container)
        self.chart_layout.setContentsMargins(0,0,0,0)
        self.chart_layout.setSpacing(10)
        self.chart_scroll.setWidget(self.chart_container)
        chart_panel_layout.addWidget(self.chart_scroll,1)
        laps_charts_split.addWidget(chart_panel)
        laps_charts_split.setSizes([610,790])

        main_split.addWidget(laps_charts_split)
        main_split.setSizes([430,390])
        l.addWidget(main_split,1)

        self.analysis_info=QLabel()
        self.analysis_info.setObjectName('muted')
        l.addWidget(self.analysis_info)
        return w

    def import_page(self):
        w,l=self.page(
            'Importa Sessioni',
            'Leggi, scarica o elimina sessioni via USB seriale senza Mass Storage; oppure importa file locali.'
        )

        # Reuse the USB/SD control from the existing tool inside this page:
        # no separate "Sessioni USB" page.
        usb_host=QFrame();usb_host.setObjectName('card')
        usb_layout=QVBoxLayout(usb_host)
        usb_layout.setContentsMargins(14,14,14,14)
        usb_layout.setSpacing(8)
        usb_title=QLabel('MicroSD del laptimer')
        usb_title.setObjectName('cardTitle')
        usb_desc=QLabel(
            'Seleziona la porta del laptimer e premi MODALITÀ USB SD. '
            'Il comando usa la stessa procedura USB SD del tool integrato; '
            'quando Windows monta la scheda puoi scegliere i CSV da importare.'
        )
        usb_desc.setWordWrap(True);usb_desc.setObjectName('muted')
        usb_layout.addWidget(usb_title);usb_layout.addWidget(usb_desc)

        tool=TrackManager('sessions')
        self.embedded_tools['import_sessions_usb']=tool
        content,_toolbar=tool.detach_for_embedding()

        # Keep only COM selector + the USB-SD button in Importa Sessioni.
        if hasattr(tool,'download_sessions_button'):
            tool.download_sessions_button.setVisible(False)
        if hasattr(tool,'analysis_button'):
            tool.analysis_button.setVisible(False)
        if hasattr(tool,'clear_sessions_button'):
            tool.clear_sessions_button.setVisible(False)
        if hasattr(tool,'usb_sd_button'):
            tool.usb_sd_button.setText('MODALITÀ USB SD')
            tool.usb_sd_button.setToolTip(
                'Attiva l’accesso USB Mass Storage alla microSD del laptimer'
            )
        if content is not None:
            content.setParent(usb_host)
            usb_layout.addWidget(content)

        # Serial microSD controls first, visible immediately upon opening Importa Sessioni.
        self.serial_sessions_panel=SerialSessionsPanel(self)
        l.addWidget(self.serial_sessions_panel)
        l.addWidget(usb_host)
        l.addWidget(self.card(
            'Importa file',
            'Seleziona uno o più CSV della telemetria, .grt, .gsa/.bin o .json.',
            'SCEGLI FILE',self.import_files
        ))
        l.addWidget(self.card(
            'Importa cartella microSD',
            'Seleziona la cartella GOATS o l’intera scheda. La scansione è ricorsiva.',
            'SCANSIONA CARTELLA',self.import_folder
        ))

        cloud=QFrame();cloud.setObjectName('card')
        cl=QVBoxLayout(cloud);cl.setContentsMargins(14,14,14,14);cl.setSpacing(8)
        ct=QLabel('Cloud Sync Android ↔ PC');ct.setObjectName('cardTitle');cl.addWidget(ct)
        cd=QLabel('Seleziona la cartella locale sincronizzata dal tuo cloud (Google Drive, OneDrive, Dropbox, Synology Drive, ecc.). Deve essere la stessa cartella scelta nell’app Android. La sincronizzazione scambia i file sessione, non il database SQLite.')
        cd.setWordWrap(True);cd.setObjectName('muted');cl.addWidget(cd)
        self.cloud_folder_label=QLabel(self.cloud_folder or 'Nessuna cartella cloud selezionata')
        self.cloud_folder_label.setWordWrap(True);cl.addWidget(self.cloud_folder_label)
        cr=QHBoxLayout()
        cb=QPushButton('SCEGLI CARTELLA CLOUD');cb.clicked.connect(self.choose_cloud_folder);cr.addWidget(cb)
        sb=QPushButton('SINCRONIZZA ORA');sb.setObjectName('primary');sb.clicked.connect(self.cloud_sync_now);cr.addWidget(sb)
        cr.addStretch();cl.addLayout(cr)
        self.cloud_auto_check=QCheckBox('Sincronizzazione automatica ogni 15 secondi')
        self.cloud_auto_check.setChecked(bool(self.cloud_auto));self.cloud_auto_check.toggled.connect(self._set_cloud_auto);cl.addWidget(self.cloud_auto_check)
        self.cloud_status=QLabel('Pronto');self.cloud_status.setObjectName('muted');cl.addWidget(self.cloud_status)
        l.addWidget(cloud)
        l.addStretch()
        from PySide6.QtWidgets import QScrollArea
        scroll=QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(w)
        return scroll
    def settings_page(self):
        w,l=self.page('Impostazioni','Configura dove il Manager salva e legge gli archivi di sessioni e circuiti.')
        box=QFrame();box.setObjectName('card');bl=QVBoxLayout(box)
        title=QLabel('Archivio sessioni');title.setObjectName('cardTitle');bl.addWidget(title)
        desc=QLabel('Puoi usare una cartella locale, OneDrive, Google Drive, Dropbox o una cartella sincronizzata del Synology NAS. Il database GOATS verrà salvato nella cartella selezionata.')
        desc.setWordWrap(True);desc.setObjectName('muted');bl.addWidget(desc)
        row=QHBoxLayout();self.sessions_folder_edit=QLineEdit(str(self.configured_sessions_dir));self.sessions_folder_edit.setReadOnly(True);row.addWidget(self.sessions_folder_edit,1)
        browse=QPushButton('SFOGLIA');browse.clicked.connect(self.browse_sessions_folder);row.addWidget(browse);bl.addLayout(row)
        self.storage_status_label=QLabel();self.storage_status_label.setWordWrap(True);bl.addWidget(self.storage_status_label)
        buttons=QHBoxLayout();local=QPushButton('CARTELLA LOCALE PREDEFINITA');local.clicked.connect(self.use_default_sessions_folder);buttons.addWidget(local)
        apply_btn=QPushButton('APPLICA CARTELLA');apply_btn.setObjectName('primary');apply_btn.clicked.connect(self.apply_sessions_folder);buttons.addWidget(apply_btn);buttons.addStretch();bl.addLayout(buttons)
        warning=QLabel('Nota cloud: evita di aprire contemporaneamente lo stesso archivio SQLite da due PC. La sincronizzazione è pensata per avere sempre disponibile lo stesso archivio tra i dispositivi, non per modifiche simultanee.')
        warning.setWordWrap(True);warning.setObjectName('muted');bl.addWidget(warning)
        l.addWidget(box)

        tbox=QFrame();tbox.setObjectName('card');tbl=QVBoxLayout(tbox)
        ttitle=QLabel('Archivio circuiti');ttitle.setObjectName('cardTitle');tbl.addWidget(ttitle)
        tdesc=QLabel('Puoi salvare i file JSON dei circuiti in una cartella locale, OneDrive, Google Drive, Dropbox o Synology. Editor, analisi e invio al laptimer useranno sempre questa posizione.')
        tdesc.setWordWrap(True);tdesc.setObjectName('muted');tbl.addWidget(tdesc)
        trow=QHBoxLayout();self.tracks_folder_edit=QLineEdit(str(self.configured_tracks_dir));self.tracks_folder_edit.setReadOnly(True);trow.addWidget(self.tracks_folder_edit,1)
        tbrowse=QPushButton('SFOGLIA');tbrowse.clicked.connect(self.browse_tracks_folder);trow.addWidget(tbrowse);tbl.addLayout(trow)
        self.tracks_storage_status_label=QLabel();self.tracks_storage_status_label.setWordWrap(True);tbl.addWidget(self.tracks_storage_status_label)
        tbuttons=QHBoxLayout();tlocal=QPushButton('CARTELLA LOCALE PREDEFINITA');tlocal.clicked.connect(self.use_default_tracks_folder);tbuttons.addWidget(tlocal)
        tapply=QPushButton('APPLICA CARTELLA');tapply.setObjectName('primary');tapply.clicked.connect(self.apply_tracks_folder);tbuttons.addWidget(tapply);tbuttons.addStretch();tbl.addLayout(tbuttons)
        l.addWidget(tbox);l.addStretch();self._update_storage_status();self._update_tracks_storage_status();return w

    def _update_storage_status(self):
        if not hasattr(self,'storage_status_label'):return
        active=str(getattr(self,'active_sessions_dir',DATA_DIR))
        configured=str(getattr(self,'configured_sessions_dir',DATA_DIR))
        if getattr(self,'storage_fallback_reason',''):
            self.storage_status_label.setText(f'ATTIVO: {active}\nConfigurato ma non disponibile: {configured}\nFallback locale automatico attivo.')
        else:
            self.storage_status_label.setText(f'ATTIVO: {active}\nDatabase: {Path(active)/DB_FILENAME}')

    def browse_sessions_folder(self):
        start=self.sessions_folder_edit.text().strip() if hasattr(self,'sessions_folder_edit') else str(self.active_sessions_dir)
        folder=QFileDialog.getExistingDirectory(self,'Seleziona cartella archivio sessioni',start)
        if folder:self.sessions_folder_edit.setText(folder)

    def use_default_sessions_folder(self):
        if hasattr(self,'sessions_folder_edit'):self.sessions_folder_edit.setText(str(DATA_DIR))

    def _save_sessions_dir_config(self,folder):
        cfg=_read_manager_settings();cfg['sessions_dir']=str(Path(folder));_write_manager_settings(cfg)

    def apply_sessions_folder(self):
        if not hasattr(self,'sessions_folder_edit'):return
        raw=self.sessions_folder_edit.text().strip()
        if not raw:return
        target_dir=Path(raw).expanduser()
        try:
            target_dir=_prepare_sessions_dir(target_dir)
        except Exception as exc:
            QMessageBox.critical(self,'Archivio sessioni',f'La cartella non è disponibile o scrivibile:\n{target_dir}\n\n{exc}')
            return
        current_db=Path(self.store.path)
        target_db=target_dir/DB_FILENAME
        try:
            same=current_db.resolve()==target_db.resolve()
        except Exception:
            same=str(current_db)==str(target_db)
        if same:
            self.configured_sessions_dir=target_dir;self.active_sessions_dir=target_dir;self.storage_fallback_reason=''
            self._save_sessions_dir_config(target_dir);self._update_storage_status()
            QMessageBox.information(self,'Archivio sessioni','Cartella sessioni salvata.')
            return

        use_existing=False
        overwrite=False
        if target_db.exists() and target_db.stat().st_size>0:
            msg=QMessageBox(self);msg.setIcon(QMessageBox.Question);msg.setWindowTitle('Archivio già presente')
            msg.setText('Nella cartella selezionata esiste già un archivio GOATS.')
            msg.setInformativeText('SÌ = usa l’archivio già presente.\nNO = sostituiscilo con l’archivio attualmente aperto.\nANNULLA = non cambiare nulla.')
            msg.setStandardButtons(QMessageBox.Yes|QMessageBox.No|QMessageBox.Cancel)
            ans=msg.exec()
            if ans==QMessageBox.Cancel:return
            use_existing=(ans==QMessageBox.Yes);overwrite=(ans==QMessageBox.No)

        old_db=current_db
        try:
            self.db_refresh_timer.stop()
            self.store.close()
            if (not target_db.exists()) or overwrite:
                target_db.parent.mkdir(parents=True,exist_ok=True)
                if old_db.exists():shutil.copy2(old_db,target_db)
            self.store=SessionStore(target_db,cloud_safe=(target_dir.resolve()!=DATA_DIR.resolve()))
        except Exception as exc:
            try:self.store=SessionStore(old_db,cloud_safe=(old_db.parent.resolve()!=DATA_DIR.resolve()))
            except Exception:pass
            self.db_refresh_timer.start()
            QMessageBox.critical(self,'Archivio sessioni',f'Impossibile passare alla nuova cartella.\n\n{exc}')
            return

        self.configured_sessions_dir=target_dir;self.active_sessions_dir=target_dir;self.storage_fallback_reason=''
        self._save_sessions_dir_config(target_dir)
        self.current_session_id=None;self._potential_lap_cache.clear();self._comparison_session_ids=[]
        self.refresh_sessions();self.db_refresh_timer.start();self._update_storage_status()
        if use_existing:
            QMessageBox.information(self,'Archivio sessioni','Archivio cloud esistente aperto correttamente.')
        else:
            QMessageBox.information(self,'Archivio sessioni','Cartella modificata. L’archivio sessioni corrente è stato copiato nella nuova posizione.')

    def _update_tracks_storage_status(self):
        if not hasattr(self,'tracks_storage_status_label'):return
        active=str(getattr(self,'active_tracks_dir',TRACKS_DIR))
        configured=str(getattr(self,'configured_tracks_dir',TRACKS_DIR))
        count=0
        try:count=len(list(Path(active).glob('*.json')))
        except Exception:pass
        if getattr(self,'tracks_storage_fallback_reason',''):
            self.tracks_storage_status_label.setText(f'ATTIVO: {active}\nConfigurato ma non disponibile: {configured}\nFallback locale automatico attivo. Circuiti disponibili: {count}')
        else:
            self.tracks_storage_status_label.setText(f'ATTIVO: {active}\nCircuiti JSON disponibili: {count}')

    def browse_tracks_folder(self):
        start=self.tracks_folder_edit.text().strip() if hasattr(self,'tracks_folder_edit') else str(self.active_tracks_dir)
        folder=QFileDialog.getExistingDirectory(self,'Seleziona cartella archivio circuiti',start)
        if folder:self.tracks_folder_edit.setText(folder)

    def use_default_tracks_folder(self):
        if hasattr(self,'tracks_folder_edit'):self.tracks_folder_edit.setText(str(APP_DIR/'tracks'))

    def _save_tracks_dir_config(self,folder):
        cfg=_read_manager_settings();cfg['tracks_dir']=str(Path(folder));_write_manager_settings(cfg)

    def apply_tracks_folder(self):
        if not hasattr(self,'tracks_folder_edit'):return
        raw=self.tracks_folder_edit.text().strip()
        if not raw:return
        target_dir=Path(raw).expanduser()
        try:target_dir=_prepare_tracks_dir(target_dir)
        except Exception as exc:
            QMessageBox.critical(self,'Archivio circuiti',f'La cartella non è disponibile o scrivibile:\n{target_dir}\n\n{exc}')
            return
        current_dir=Path(getattr(self,'active_tracks_dir',APP_DIR/'tracks'))
        try:same=current_dir.resolve()==target_dir.resolve()
        except Exception:same=str(current_dir)==str(target_dir)
        if same:
            self.configured_tracks_dir=target_dir;self.active_tracks_dir=target_dir;self.tracks_storage_fallback_reason=''
            self._save_tracks_dir_config(target_dir);set_tracks_dir(target_dir);self._update_tracks_storage_status()
            QMessageBox.information(self,'Archivio circuiti','Cartella circuiti salvata.')
            return

        existing=list(target_dir.glob('*.json'))
        copy_current=True
        overwrite=False
        if existing:
            msg=QMessageBox(self);msg.setIcon(QMessageBox.Question);msg.setWindowTitle('Circuiti già presenti')
            msg.setText('Nella cartella selezionata sono già presenti circuiti GOATS.')
            msg.setInformativeText('SÌ = usa i circuiti già presenti senza modificarli.\nNO = copia anche i circuiti dell’archivio corrente, sovrascrivendo gli omonimi.\nANNULLA = non cambiare nulla.')
            msg.setStandardButtons(QMessageBox.Yes|QMessageBox.No|QMessageBox.Cancel)
            ans=msg.exec()
            if ans==QMessageBox.Cancel:return
            copy_current=(ans==QMessageBox.No);overwrite=copy_current
        try:
            if copy_current:
                for src in current_dir.glob('*.json'):
                    dst=target_dir/src.name
                    if (not dst.exists()) or overwrite:shutil.copy2(src,dst)
            self.configured_tracks_dir=target_dir;self.active_tracks_dir=target_dir;self.tracks_storage_fallback_reason=''
            self._save_tracks_dir_config(target_dir);set_tracks_dir(target_dir)
            self._track_data_cache.clear();self._potential_lap_cache.clear()
            tool=self.embedded_tools.get('tracks')
            if tool is not None and hasattr(tool,'refresh_tracks'):tool.refresh_tracks()
            self._update_tracks_storage_status()
        except Exception as exc:
            set_tracks_dir(current_dir)
            QMessageBox.critical(self,'Archivio circuiti',f'Impossibile passare alla nuova cartella.\n\n{exc}')
            return
        if existing and not copy_current:
            QMessageBox.information(self,'Archivio circuiti','Archivio circuiti cloud esistente aperto correttamente.')
        else:
            QMessageBox.information(self,'Archivio circuiti','Cartella modificata. I circuiti correnti sono stati copiati nella nuova posizione.')

    def info_page(self):
        w,l=self.page('Informazioni','GOATS RT Manager V5.4.15.5');t=QLabel('''Implementato:\n• GRT8 / GSA3 / GSA2 / JSON legacy\n• Database SQLite\n• Archivio storico ricercabile\n• Cartella archivio sessioni configurabile (locale/cloud/NAS)\n• Cartella archivio circuiti configurabile (locale/cloud/NAS)\n• Import microSD\n• Cloud Sync bidirezionale Android ↔ PC tramite cartella cloud condivisa\n• Mappa satellitare con hover continuo/interpolato + schermo intero\n• Giri e curve velocità affiancati con salto automatico alla curva selezionata\n• Tempi settore in tabella + split e tempi evidenziati sulla mappa\n• Giro Potenziale = somma dei migliori settori validi della sessione\n• Riepiloghi sessioni centrati (Note a sinistra) con linee di divisione e Giro Potenziale\n• Note descrittive persistenti per ogni sessione\n• Confronto multi-sessione con riepilogo e navigazione avanti/indietro\n• Replay simultaneo dei giri selezionati a 0,5x / 1x\n• Controlli replay fullscreen con promemoria tastiera: SPAZIO / S / R / ESC\n• Analisi frenata + curva con modalità FRENATA / VELOCITÀ CURVA / ENTRAMBI, sincronizzata anche con le tabelle F1/F2/... sulla mappa\n• Fullscreen: scelta indipendente di analisi frenata, velocità curva e grafico velocità\n• Mappa senza riquadro descrittivo sovrapposto\n• Tabelle frenata fullscreen con scala dinamica proporzionale allo zoom mappa\n• Tempi giro SDCSV: crossing interpolato iTOW + finish line\n• Grafico velocità/tempo\n• Export JSON / CSV / GPX\n• Editor piste + USB Protocol V2\n• AssistNow Predictive Orbits (ZTP / Thingstream)\n• Profili AssistNow multi-dispositivo con nome, descrizione, credenziali e cache indipendenti\n• Manuale integrato con procedura Thingstream/ZTP\n• Lettura automatica identità M9N via USB (GGID_GET)\n\nProssimi moduli: delta spaziale, corda/uscita, video Brave Pro 4 e Coach AI.''');t.setWordWrap(True);l.addWidget(t);l.addStretch();return w
    def show_page(self,i):
        # L'editor Circuiti può modificare split/settori: invalida i calcoli
        # del giro potenziale prima di aprirlo, così al rientro vengono ricalcolati.
        if i==4:
            self._track_data_cache.clear();self._potential_lap_cache.clear()
        self.stack.setCurrentIndex(i)
        [b.setChecked(k==i) for k,b in enumerate(self.nav)]
        # Se si esce dall'Analisi verso una normale pagina della sidebar,
        # l'eventuale contesto "ritorna al confronto" non deve restare appeso.
        if i!=2 and i!=getattr(self,'compare_page_index',None):
            self._analysis_return_page=None
            if hasattr(self,'analysis_back_btn'):self.analysis_back_btn.setVisible(False)
        # The session combo is refreshed with signals blocked. Ensure that
        # entering Analysis always loads the selected session immediately.
        if i == 2 and hasattr(self, 'session_combo') and self.session_combo.count():
            self.analysis_session_changed()
    def refresh_sessions(self,*_):
        rows=self.store.sessions(self.search.text() if hasattr(self,'search') else '')
        if hasattr(self,'table'):
            self.table.setRowCount(len(rows))
            for r,s in enumerate(rows):
                note=(s['notes'] or '').strip().replace('\n',' ')
                note_preview=(note[:77]+'...') if len(note)>80 else note
                potential_ms=self._session_potential_lap_details(int(s['id'])).get('potential_ms',0)
                vals=[s['id'],s['date'],s['time'],s['track_name'],s['session_type'],s['source_format'],s['point_count'],s['lap_count'],f"{s['max_speed_kmh']:.1f}",fmt_ms(s['best_lap_ms']),fmt_ms(potential_ms),note_preview]
                for c,v in enumerate(vals):
                    item=QTableWidgetItem(str(v))
                    item.setTextAlignment((Qt.AlignLeft|Qt.AlignVCenter) if c==11 else Qt.AlignCenter)
                    self.table.setItem(r,c,item)
        if hasattr(self,'session_combo'):
            old=self.session_combo.currentData();self.session_combo.blockSignals(True);self.session_combo.clear()
            for s in rows:self.session_combo.addItem(f"#{s['id']} • {s['date']} {s['time']} • {s['track_name']} ({s['source_format']})",s['id'])
            if old:
                idx=self.session_combo.findData(old)
                if idx>=0:self.session_combo.setCurrentIndex(idx)
            self.session_combo.blockSignals(False)
            if self.current_session_id is None and self.session_combo.count():
                self.current_session_id = self.session_combo.currentData()
        allrows=self.store.sessions('')
        if (hasattr(self,'compare_table') and self.compare_page_index is not None
                and self.stack.currentIndex()==self.compare_page_index and self._comparison_session_ids):
            self._populate_comparison_table(self._comparison_session_ids)
        if hasattr(self,'m_sessions'):
            pts=sum(int(s['point_count']) for s in allrows);dur=sum(int(s['duration_ms']) for s in allrows);best=min((int(s['best_lap_ms']) for s in allrows if int(s['best_lap_ms'])>0),default=0);self.m_sessions.value_label.setText(str(len(allrows)));self.m_points.value_label.setText(f'{pts:,}'.replace(',','.'));self.m_hours.value_label.setText(f'{dur/3600000:.1f}');self.m_best.value_label.setText(fmt_ms(best))
    def selected_id(self):
        return int(self.table.item(self.table.currentRow(),0).text()) if self.table.currentRow()>=0 else None
    def edit_selected_session_notes(self):
        sid=self.selected_id()
        if not sid:
            QMessageBox.information(self,'Note sessione','Seleziona prima una sessione.')
            return
        sess=self.store.session(sid)
        dlg=QDialog(self);dlg.setWindowTitle(f'Note sessione #{sid} - {sess["track_name"] or "Circuito"}');dlg.resize(640,380)
        lay=QVBoxLayout(dlg)
        info=QLabel(f'{sess["date"]} {sess["time"]} • {sess["track_name"]}');info.setObjectName('muted');lay.addWidget(info)
        edit=QTextEdit();edit.setPlaceholderText('Inserisci note descrittive della sessione...');edit.setPlainText(sess['notes'] or '');lay.addWidget(edit,1)
        buttons=QHBoxLayout();buttons.addStretch();cancel=QPushButton('ANNULLA');save=QPushButton('SALVA NOTE');buttons.addWidget(cancel);buttons.addWidget(save);lay.addLayout(buttons)
        cancel.clicked.connect(dlg.reject)
        def _save():
            self.store.update_notes(sid,edit.toPlainText().strip());self.refresh_sessions();
            if self.current_session_id==sid and hasattr(self,'session_notes_edit'):self.session_notes_edit.setPlainText(edit.toPlainText().strip())
            dlg.accept()
        save.clicked.connect(_save)
        dlg.exec()
    def save_current_session_notes(self):
        sid=self.current_session_id
        if not sid:
            QMessageBox.information(self,'Note sessione','Seleziona prima una sessione.')
            return
        text=self.session_notes_edit.toPlainText().strip() if hasattr(self,'session_notes_edit') else ''
        self.store.update_notes(sid,text);self.refresh_sessions()
        QMessageBox.information(self,'Note sessione','Note salvate nel database locale.')
    def open_selected_analysis(self,*_):
        sid=self.selected_id()
        self._analysis_return_page=None
        if hasattr(self,'analysis_back_btn'):self.analysis_back_btn.setVisible(False)
        self.show_page(2);idx=self.session_combo.findData(sid);self.session_combo.setCurrentIndex(idx if idx>=0 else 0)
    def delete_selected(self):
        sid=self.selected_id()
        if sid and QMessageBox.question(self,'Elimina','Eliminare la sessione dal database locale?')==QMessageBox.Yes:self.store.delete(sid);self._potential_lap_cache.pop(int(sid),None);self.refresh_sessions()
    def _load_cloud_config(self):
        try:
            cfg=_read_manager_settings()
            self.cloud_folder=str(cfg.get('cloud_sync_folder','') or '')
            self.cloud_auto=bool(cfg.get('cloud_sync_auto',False))
        except Exception:
            self.cloud_folder='';self.cloud_auto=False

    def _save_cloud_config(self):
        try:
            cfg=_read_manager_settings()
            cfg['cloud_sync_folder']=self.cloud_folder
            cfg['cloud_sync_auto']=bool(self.cloud_auto)
            _write_manager_settings(cfg)
        except Exception:
            pass

    def _set_cloud_auto(self,checked):
        self.cloud_auto=bool(checked);self._save_cloud_config()
        if hasattr(self,'cloud_status'):
            self.cloud_status.setText('Sincronizzazione automatica attiva.' if self.cloud_auto else 'Sincronizzazione automatica disattivata.')
        if self.cloud_auto:QTimer.singleShot(200,self._cloud_auto_tick)

    def choose_cloud_folder(self):
        start=self.cloud_folder if self.cloud_folder and Path(self.cloud_folder).exists() else str(Path.home())
        folder=QFileDialog.getExistingDirectory(self,'Cartella Cloud Sync GOATS RT',start)
        if not folder:return
        self.cloud_folder=str(Path(folder).resolve());self._cloud_seen={};self._save_cloud_config()
        if hasattr(self,'cloud_folder_label'):self.cloud_folder_label.setText(self.cloud_folder)
        if hasattr(self,'cloud_status'):self.cloud_status.setText('Cartella cloud selezionata. Premi SINCRONIZZA ORA.')

    @staticmethod
    def _cloud_supported(path):
        p=Path(path);return p.is_file() and p.suffix.lower() in ('.csv','.grt','.gsa','.bin','.json')

    def _cloud_publish_file(self,path):
        if not self.cloud_folder:return False
        src=Path(path)
        if not self._cloud_supported(src):return False
        root=Path(self.cloud_folder)
        try:_prepare_sessions_dir(root)
        except Exception:return False
        try:
            if src.resolve().parent==root.resolve():
                sig=(src.stat().st_size,src.stat().st_mtime_ns);self._cloud_seen[str(src.resolve())]=sig
                return False
        except Exception:pass
        dest=root/src.name
        try:
            if dest.exists() and dest.stat().st_size==src.stat().st_size:
                sig=(dest.stat().st_size,dest.stat().st_mtime_ns);self._cloud_seen[str(dest.resolve())]=sig
                return False
            if dest.exists():
                stem,suffix=dest.stem,dest.suffix;i=2
                while dest.exists():dest=root/f'{stem}_{i}{suffix}';i+=1
            shutil.copy2(src,dest)
            sig=(dest.stat().st_size,dest.stat().st_mtime_ns);self._cloud_seen[str(dest.resolve())]=sig
            return True
        except Exception:return False

    def _cloud_files(self):
        if not self.cloud_folder:return []
        root=Path(self.cloud_folder)
        if not root.exists():return []
        return sorted([p for p in root.iterdir() if self._cloud_supported(p)],key=lambda p:p.name.lower())

    def _cloud_session_exists(self,sess):
        try:
            crc=int(getattr(sess,'crc32',0) or 0);n=len(getattr(sess,'points',[]) or [])
            args=[str(getattr(sess,'date','') or ''),str(getattr(sess,'time','') or ''),str(getattr(sess,'track_name','') or ''),n]
            sql='SELECT id FROM sessions WHERE date=? AND time=? AND track_name=? AND point_count=?'
            if crc:
                sql+=' AND crc32=?';args.append(crc)
            return self.store.conn.execute(sql,tuple(args)).fetchone() is not None
        except Exception:
            return False

    def _cloud_import_changed(self,show_progress=False):
        files=self._cloud_files();changed=[]
        for p in files:
            try:sig=(p.stat().st_size,p.stat().st_mtime_ns)
            except Exception:continue
            key=str(p.resolve())
            if self._cloud_seen.get(key)!=sig:changed.append((p,key,sig))
        if not changed:return (0,0,0)
        ok=0;skipped=0;errors=0
        pg=QProgressDialog('Sincronizzazione cloud...','Annulla',0,len(changed),self) if show_progress else None
        if pg:pg.setWindowModality(Qt.WindowModal)
        for i,(p,key,sig) in enumerate(changed):
            if pg and pg.wasCanceled():break
            if pg:pg.setLabelText(p.name);QApplication.processEvents()
            try:
                for sess in parse_any(str(p)):
                    if self._cloud_session_exists(sess):skipped+=1
                    else:self.store.import_session(sess);ok+=1
                self._cloud_seen[key]=sig
            except Exception:
                errors+=1
            if pg:pg.setValue(i+1)
        if pg:pg.close()
        if ok:self._potential_lap_cache.clear();self.refresh_sessions()
        return ok,skipped,errors

    def _cloud_publish_existing_sources(self):
        count=0
        if not self.cloud_folder:return count
        for row in self.store.sessions():
            try:
                src=row['source_path']
                if src and Path(src).exists() and self._cloud_publish_file(src):count+=1
            except Exception:pass
        return count

    def cloud_sync_now(self,*_):
        if not self.cloud_folder:
            QMessageBox.information(self,'Cloud Sync','Seleziona prima una cartella cloud.');return
        if hasattr(self,'cloud_status'):self.cloud_status.setText('Sincronizzazione in corso...')
        QApplication.processEvents()
        imported,skipped,errors=self._cloud_import_changed(show_progress=True)
        uploaded=self._cloud_publish_existing_sources()
        if hasattr(self,'cloud_status'):
            self.cloud_status.setText(f'Completata: {imported} importate • {skipped} già presenti • {uploaded} caricate • {errors} errori')
        QMessageBox.information(self,'Cloud Sync',f'Sincronizzazione completata.\n\nSessioni importate: {imported}\nGià presenti: {skipped}\nFile caricati: {uploaded}\nErrori: {errors}')

    def _cloud_auto_tick(self):
        if not self.cloud_auto or not self.cloud_folder:return
        try:
            imported,skipped,errors=self._cloud_import_changed(show_progress=False)
            uploaded=self._cloud_publish_existing_sources()
            if hasattr(self,'cloud_status') and (imported or uploaded or errors):
                self.cloud_status.setText(f'Auto Sync: {imported} importate • {skipped} già presenti • {uploaded} caricate • {errors} errori')
        except Exception as e:
            if hasattr(self,'cloud_status'):self.cloud_status.setText(f'Cloud Sync: {e}')

    def import_files(self):
        files,_=QFileDialog.getOpenFileNames(self,'Importa sessioni','','Sessioni GOATS (*.csv *.grt *.gsa *.bin *.json);;CSV telemetria (*.csv);;Tutti i file (*.*)');self.do_import(files)
    def import_folder(self):
        folder=QFileDialog.getExistingDirectory(self,'Cartella microSD / sessioni')
        if not folder:return
        root=Path(folder);files=[]
        for pat in ('*.csv','*.grt','*.gsa','*.bin','*.json'):files.extend(str(p) for p in root.rglob(pat) if p.suffix.lower()!='.json' or 'session' in p.name.lower() or 'archive' in p.name.lower())
        self.do_import(sorted(set(files)))
    def do_import(self,files):
        if not files:return
        pg=QProgressDialog('Importazione sessioni...','Annulla',0,len(files),self);pg.setWindowModality(Qt.WindowModal);ok=0;errors=[]
        for i,path in enumerate(files):
            if pg.wasCanceled():break
            pg.setLabelText(Path(path).name);QApplication.processEvents()
            try:
                for s in parse_any(path):self.store.import_session(s);ok+=1
                if self.cloud_auto:self._cloud_publish_file(path)
            except Exception as e:errors.append(f'{Path(path).name}: {e}')
            pg.setValue(i+1)
        pg.close();self._potential_lap_cache.clear();self.refresh_sessions();self.show_page(1);msg=f'Importate {ok} sessioni.'+(('\n\nErrori:\n'+'\n'.join(errors[:10])) if errors else '');QMessageBox.information(self,'Importazione',msg)
    def analysis_session_changed(self,*_):
        sid=self.session_combo.currentData()
        self.current_session_id=sid
        if hasattr(self,'session_notes_edit'):
            sess_note=self.store.session(sid) if sid else None
            self.session_notes_edit.blockSignals(True)
            self.session_notes_edit.setPlainText((sess_note['notes'] or '') if sess_note else '')
            self.session_notes_edit.blockSignals(False)

        self._lap_table_updating=True
        self.lap_table.blockSignals(True)
        self.lap_table.clearContents()
        self.lap_table.setRowCount(0)
        self._set_session_summary(0,0,0,0.0,0.0)
        self._analysis_focus_lap=None
        self._analysis_lap_stats_by_no={}
        self._analysis_best_lap_no=None
        self._analysis_show_brakes=False
        self._analysis_brake_events=[]
        self._analysis_brake_groups=[]
        self._analysis_replay_running=False

        if sid:
            sess=self.store.session(sid)
            laps=list(self.store.laps(sid))

            # Filtro giri completi + filtro giri anomali/corti.
            # Per i CSV SD il numero giro più alto rappresenta il giro ancora
            # APERTO al momento di Fine Sessione: lo ignoriamo sempre, anche se
            # dura più dell'80% di un giro normale. Questo rende il filtro
            # indipendente dalla durata dello spezzone finale.
            all_session_points=(
                list(self.store.points(sid,None))
                if str(sess['source_format'] or '') == 'SDCSV' else []
            )
            point_lap_nos=sorted({
                int(p['lap'] or 0) for p in all_session_points
                if int(p['lap'] or 0) > 0
            })
            open_final_lap=(
                point_lap_nos[-1]
                if str(sess['source_format'] or '') == 'SDCSV' and point_lap_nos
                else None
            )
            ignored_incomplete_laps=1 if open_final_lap is not None else 0

            positive_laps=[
                lap for lap in laps
                if int(lap['lap_time_ms'] or 0) > 0
                and (open_final_lap is None or int(lap['lap']) != open_final_lap)
            ]

            reference_lap=None
            for lap in positive_laps:
                if int(lap['lap']) == 2:
                    reference_lap=lap
                    break

            reference_lap_ms=(
                int(reference_lap['lap_time_ms'])
                if reference_lap is not None else 0
            )
            min_valid_lap_ms=reference_lap_ms * 0.80

            if reference_lap_ms > 0:
                valid=[
                    lap for lap in positive_laps
                    if int(lap['lap_time_ms']) >= min_valid_lap_ms
                ]
            else:
                valid=positive_laps

            best_lap_no=None
            best_lap_ms=0
            if valid:
                best=min(valid,key=lambda x:int(x['lap_time_ms']))
                best_lap_no=int(best['lap'])
                best_lap_ms=int(best['lap_time_ms'])

            laps=valid
            track_data=self._analysis_track_data()
            sector_lines=list((track_data or {}).get('sectors',[]) or [])
            timing_sector_count=(len(sector_lines)+1) if sector_lines else 0

            headers=['Mostra','Giro','Tempo']
            if timing_sector_count:
                headers.extend([f'S{i}' for i in range(1,timing_sector_count+1)])
            headers.extend(['V min','V media','V max','Punti'])
            self.lap_table.setColumnCount(len(headers))
            self.lap_table.setHorizontalHeaderLabels(headers)
            self.lap_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
            self.lap_table.horizontalHeader().setStretchLastSection(True)

            all_points=(
                all_session_points
                if all_session_points
                else (list(self.store.points(sid,None)) if timing_sector_count else [])
            )
            lap_stats=[]
            for lap in laps:
                lap_no=int(lap['lap'])
                pts=list(self.store.points(sid,lap_no))
                speeds=[float(p['speed_kmh']) for p in pts]
                vmin=min(speeds) if speeds else 0.0
                vmax=max(speeds) if speeds else 0.0
                vavg=(sum(speeds)/len(speeds)) if speeds else 0.0
                sector_times=(
                    self._analysis_sector_times_for_lap(
                        all_points,lap_no,track_data
                    ) if timing_sector_count else []
                )
                lap_stats.append({
                    'lap':lap,'lap_no':lap_no,'pts':pts,
                    'vmin':vmin,'vmax':vmax,'vavg':vavg,
                    'sector_times':sector_times,
                })

            self._analysis_lap_stats_by_no={
                int(st['lap_no']):st for st in lap_stats
            }
            self._analysis_best_lap_no=best_lap_no
            self._analysis_focus_lap=best_lap_no

            best_sector_times=[]
            for i in range(timing_sector_count):
                vals=[
                    st['sector_times'][i]
                    for st in lap_stats
                    if i < len(st['sector_times'])
                    and st['sector_times'][i] is not None
                    and st['sector_times'][i] > 0
                ]
                best_sector_times.append(min(vals) if vals else None)

            potential_lap_ms=(
                int(sum(int(x) for x in best_sector_times))
                if timing_sector_count and len(best_sector_times)==timing_sector_count
                and all(x is not None and int(x)>0 for x in best_sector_times)
                else 0
            )
            self._potential_lap_cache[int(sid)]={
                'potential_ms':potential_lap_ms,
                'best_sector_times':list(best_sector_times),
                'sector_count':timing_sector_count,
            }

            for st in lap_stats:
                lap=st['lap']; lap_no=st['lap_no']; pts=st['pts']
                r=self.lap_table.rowCount()
                self.lap_table.insertRow(r)

                check=QTableWidgetItem()
                check.setFlags(
                    Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable
                )
                check.setCheckState(
                    Qt.Checked if lap_no==best_lap_no else Qt.Unchecked
                )
                check.setData(Qt.UserRole,lap_no)
                check.setTextAlignment(Qt.AlignCenter)
                # Piccolo richiamo colore: coincide con curva e traiettoria del giro.
                check.setBackground(QColor(self._analysis_color_for_lap(lap_no)))
                self.lap_table.setItem(r,0,check)

                values=[
                    ('BEST' if lap_no==best_lap_no else str(lap_no)),
                    fmt_ms(int(lap['lap_time_ms'] or 0)),
                ]
                values.extend([
                    fmt_ms(int(x)) if x is not None else '--:--.---'
                    for x in st['sector_times']
                ])
                values.extend([
                    f"{st['vmin']:.1f}",
                    f"{st['vavg']:.1f}",
                    f"{st['vmax']:.1f}",
                    str(len(pts)),
                ])

                for c,val in enumerate(values,start=1):
                    item=QTableWidgetItem(val)
                    item.setData(Qt.UserRole,lap_no)
                    item.setTextAlignment(Qt.AlignCenter)

                    if lap_no==best_lap_no:
                        item.setBackground(QColor(46,125,50))
                        item.setForeground(QColor(255,255,255))
                        font=item.font();font.setBold(True);item.setFont(font)

                    # I migliori settori della sessione sono evidenziati in fucsia.
                    sector_idx=c-3
                    if 0 <= sector_idx < timing_sector_count:
                        cur=st['sector_times'][sector_idx]
                        best_sector=best_sector_times[sector_idx]
                        if cur is not None and best_sector is not None and cur==best_sector:
                            item.setBackground(QColor(190,0,190))
                            item.setForeground(QColor(255,255,255))
                            font=item.font();font.setBold(True);item.setFont(font)

                    self.lap_table.setItem(r,c,item)

            ignored_short_laps=max(0,len(positive_laps)-len(valid))

            # Il riepilogo Analisi usa soltanto i giri completi/validi. In
            # questo modo anche Vmax e Vmedia non vengono alterate dal tratto
            # percorso dopo l'ultimo traguardo prima di Fine Sessione.
            valid_speeds=[
                float(p['speed_kmh'] or 0.0)
                for st in lap_stats for p in st['pts']
            ]
            summary_vmax=(
                max(valid_speeds) if valid_speeds
                else float(sess['max_speed_kmh'] or 0.0)
            )
            summary_vavg=(
                sum(valid_speeds)/len(valid_speeds) if valid_speeds
                else float(sess['avg_speed_kmh'] or 0.0)
            )
            self._set_session_summary(
                len(valid),best_lap_ms,potential_lap_ms,summary_vmax,summary_vavg
            )
            sector_note=(
                f" • {timing_sector_count} settori calcolati dalla geometria pista"
                if timing_sector_count else ""
            )
            self.analysis_info.setText(
                f"{sess['source_format']} • {sess['point_count']} punti • "
                f"{sess['sample_rate_hz']:.1f} Hz • durata {fmt_dur(sess['duration_ms'])} • "
                f"Vmax giri validi {summary_vmax:.1f} km/h"
                + (f" • Best Lap: Giro {best_lap_no}" if best_lap_no else "")
                + (f" • Giro potenziale {fmt_ms(potential_lap_ms)}" if potential_lap_ms else "")
                + sector_note
                + (
                    f" • {ignored_incomplete_laps} spezzone finale ignorato (giro non chiuso)"
                    if ignored_incomplete_laps else ""
                )
                + (
                    f" • {ignored_short_laps} giro/i ignorato/i (<80% del Giro 2)"
                    if ignored_short_laps else ""
                )
            )

        self.lap_table.blockSignals(False)
        self._lap_table_updating=False
        self.render_analysis()

    def _set_session_summary(self,lap_count,best_ms,potential_ms,vmax,vavg):
        values=[
            str(int(lap_count or 0)),
            fmt_ms(int(best_ms or 0)),
            fmt_ms(int(potential_ms or 0)),
            f"{float(vmax or 0.0):.1f} km/h",
            f"{float(vavg or 0.0):.1f} km/h",
        ]
        for c,val in enumerate(values):
            item=QTableWidgetItem(val)
            item.setTextAlignment(Qt.AlignCenter)
            if c==1 and best_ms:
                item.setBackground(QColor(46,125,50))
                item.setForeground(QColor(255,255,255))
                font=item.font();font.setBold(True);item.setFont(font)
            elif c==2 and potential_ms:
                item.setBackground(QColor(190,0,190))
                item.setForeground(QColor(255,255,255))
                font=item.font();font.setBold(True);item.setFont(font)
            self.session_summary.setItem(0,c,item)

    def _selected_laps(self):
        laps=[]
        if not hasattr(self,'lap_table'):
            return laps
        for r in range(self.lap_table.rowCount()):
            item=self.lap_table.item(r,0)
            if item is not None and item.checkState()==Qt.Checked:
                lap_no=item.data(Qt.UserRole)
                if lap_no is not None:
                    laps.append(int(lap_no))
        return laps

    def _lap_check_changed(self,item):
        if self._lap_table_updating or item.column()!=0:
            return
        lap_no=item.data(Qt.UserRole)
        if lap_no is not None:
            lap_no=int(lap_no)
            if item.checkState()==Qt.Checked:
                self._analysis_focus_lap=lap_no
            elif self._analysis_focus_lap==lap_no:
                remaining=self._selected_laps()
                self._analysis_focus_lap=remaining[0] if remaining else None
        self.render_analysis()
        if lap_no is not None and item.checkState()==Qt.Checked:
            QTimer.singleShot(80,lambda n=lap_no:self._scroll_to_lap_chart(n))

    def _lap_row_selected(self):
        if self._lap_table_updating or not hasattr(self,'lap_table'):
            return
        row=self.lap_table.currentRow()
        if row < 0:
            return
        item=self.lap_table.item(row,0) or self.lap_table.item(row,1)
        if item is None:
            return
        lap_no=item.data(Qt.UserRole)
        if lap_no is None:
            return
        lap_no=int(lap_no)
        self._analysis_focus_lap=lap_no

        # Una riga selezionata deve avere anche la relativa curva disponibile.
        # Non deselezioniamo gli altri giri: il confronto multiplo resta attivo.
        check=self.lap_table.item(row,0)
        if check is not None and check.checkState()!=Qt.Checked:
            self._lap_table_updating=True
            self.lap_table.blockSignals(True)
            check.setCheckState(Qt.Checked)
            self.lap_table.blockSignals(False)
            self._lap_table_updating=False

        self.render_analysis()
        QTimer.singleShot(80,lambda n=lap_no:self._scroll_to_lap_chart(n))

    def _scroll_to_lap_chart(self,lap_no):
        view=self._analysis_chart_views_by_lap.get(int(lap_no))
        if view is not None and hasattr(self,'chart_scroll'):
            self.chart_scroll.ensureWidgetVisible(view,0,35)
            try:
                view.setFocus(Qt.OtherFocusReason)
            except Exception:
                pass

    def _select_all_laps(self):
        self._lap_table_updating=True
        self.lap_table.blockSignals(True)
        for r in range(self.lap_table.rowCount()):
            item=self.lap_table.item(r,0)
            if item is not None:
                item.setCheckState(Qt.Checked)
        self.lap_table.blockSignals(False)
        self._lap_table_updating=False
        self.render_analysis()

    def _clear_all_laps(self):
        self._lap_table_updating=True
        self.lap_table.blockSignals(True)
        for r in range(self.lap_table.rowCount()):
            item=self.lap_table.item(r,0)
            if item is not None:
                item.setCheckState(Qt.Unchecked)
        self.lap_table.blockSignals(False)
        self._lap_table_updating=False
        self.render_analysis()

    @staticmethod
    def _analysis_geo_distance_m(a,b):
        """Distanza geodetica tra due punti DB/dict in metri."""
        try:
            lat1=math.radians(float(a['latitude'])); lon1=math.radians(float(a['longitude']))
            lat2=math.radians(float(b['latitude'])); lon2=math.radians(float(b['longitude']))
        except Exception:
            return 0.0
        dlat=lat2-lat1; dlon=lon2-lon1
        h=math.sin(dlat/2.0)**2+math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2.0)**2
        return 6371000.0*2.0*math.asin(min(1.0,math.sqrt(max(0.0,h))))

    def _analysis_distance_time_profile(self, rows, lap_meta=None):
        """
        Profilo distanza/tempo del giro per confronti nello stesso punto pista.

        Per i CSV diagnostici usa anche gli start/end del giro ricostruiti dal
        crossing iTOW. Aggiunge due estremi sintetici START/FINISH stimando i
        pochi metri tra il crossing e il primo/ultimo fix dalla velocità GNSS.
        Questo rende il delta cumulativo al punto di frenata molto meno
        sensibile al fatto che il primo campione cada 40-100 ms dopo il traguardo.
        """
        pts=[dict(r) for r in rows if r['latitude'] is not None and r['longitude'] is not None]
        pts.sort(key=lambda r:int(r['elapsed_ms'] or 0))
        point_times=[float(r.get('elapsed_ms',0) or 0) for r in pts]
        if not pts:
            return {'rows':[],'dist':[],'times':[],'length':0.0,'lap_start_ms':0.0,'lap_end_ms':0.0}

        try: lap_start=float(lap_meta['start_ms']) if lap_meta is not None else point_times[0]
        except Exception: lap_start=point_times[0]
        try: lap_end=float(lap_meta['end_ms']) if lap_meta is not None else point_times[-1]
        except Exception: lap_end=point_times[-1]
        if lap_start>point_times[0]: lap_start=point_times[0]
        if lap_end<point_times[-1]: lap_end=point_times[-1]

        if len(pts)<2:
            return {'rows':pts,'dist':[0.0],'times':[point_times[0]],'length':0.0,'lap_start_ms':lap_start,'lap_end_ms':lap_end}

        poly=[0.0]*len(pts)
        for i in range(1,len(pts)):
            step=self._analysis_geo_distance_m(pts[i-1],pts[i])
            poly[i]=poly[i-1]+(step if 0.0<=step<35.0 else 0.0)

        # Stima molto corta dei tratti non campionati a cavallo del crossing.
        # Il clamp evita che un file legacy con start/end non coerenti generi
        # offset spaziali irrealistici.
        start_dt=max(0.0,min(0.50,(point_times[0]-lap_start)/1000.0))
        end_dt=max(0.0,min(0.50,(lap_end-point_times[-1])/1000.0))
        v0=max(0.0,float(pts[0].get('speed_kmh',0.0) or 0.0))/3.6
        v1=max(0.0,float(pts[-1].get('speed_kmh',0.0) or 0.0))/3.6
        start_gap=v0*start_dt
        end_gap=v1*end_dt
        point_dist=[start_gap+d for d in poly]
        total=max(0.0,point_dist[-1]+end_gap)

        dist=[0.0]+point_dist+[total]
        times=[lap_start]+point_times+[lap_end]
        point_speeds=[max(0.0,float(p.get('speed_kmh',0.0) or 0.0)) for p in pts]
        speeds=[point_speeds[0]]+point_speeds+[point_speeds[-1]]
        return {
            'rows':pts,'dist':dist,'times':times,'speeds':speeds,'length':total,
            'lap_start_ms':lap_start,'lap_end_ms':lap_end,
        }

    @staticmethod
    def _analysis_profile_speed_at_fraction(profile, fraction):
        """Interpola la velocità nello stesso punto normalizzato della pista."""
        if not profile or profile.get('length',0.0)<=0 or len(profile.get('dist',[]))<2:
            return None
        dist=profile.get('dist',[]); speeds=profile.get('speeds',[])
        if len(speeds)!=len(dist):
            return None
        f=max(0.0,min(1.0,float(fraction)))
        target=f*float(profile['length'])
        if target<=dist[0]: return float(speeds[0])
        if target>=dist[-1]: return float(speeds[-1])
        lo=0;hi=len(dist)-1
        while hi-lo>1:
            mid=(lo+hi)//2
            if dist[mid]<=target: lo=mid
            else: hi=mid
        span=dist[hi]-dist[lo]
        k=(target-dist[lo])/span if span>1e-9 else 0.0
        return float(speeds[lo])+(float(speeds[hi])-float(speeds[lo]))*k

    @staticmethod
    def _analysis_profile_time_at_fraction(profile, fraction):
        """Interpola il tempo del giro a una posizione normalizzata 0..1."""
        if not profile or profile.get('length',0.0)<=0 or len(profile.get('dist',[]))<2:
            return None
        f=max(0.0,min(1.0,float(fraction)))
        target=f*float(profile['length'])
        dist=profile['dist']; times=profile['times']
        if target<=dist[0]: return float(times[0])
        if target>=dist[-1]: return float(times[-1])
        lo=0;hi=len(dist)-1
        while hi-lo>1:
            mid=(lo+hi)//2
            if dist[mid]<=target: lo=mid
            else: hi=mid
        span=dist[hi]-dist[lo]
        k=(target-dist[lo])/span if span>1e-9 else 0.0
        return float(times[lo])+(float(times[hi])-float(times[lo]))*k

    def _analysis_profile_lap_elapsed_at_fraction(self, profile, fraction):
        """Tempo cumulativo dal crossing di inizio giro allo stesso punto pista."""
        t=self._analysis_profile_time_at_fraction(profile,fraction)
        if t is None or not profile:return None
        try:start=float(profile.get('lap_start_ms',0.0))
        except Exception:start=0.0
        return float(t)-start

    def _analysis_detect_braking_events(self,lap_no,rows):
        """
        Stima le frenate usando soltanto velocità GPS e tempo.
        Il punto restituito è l'inizio della decelerazione significativa, non il
        punto di minima velocità. Il filtro è volutamente conservativo per non
        trasformare piccoli rilasci gas in frenate.
        """
        rows=[dict(r) for r in rows if r['latitude'] is not None and r['longitude'] is not None]
        rows.sort(key=lambda r:int(r['elapsed_ms'] or 0))
        if len(rows)<8:
            return [],0.0

        n=len(rows)
        times=[float(r['elapsed_ms'] or 0) for r in rows]
        raw=[float(r['speed_kmh'] or 0.0) for r in rows]
        # Media mobile corta: a 25 Hz circa 0,20 s, a 10 Hz circa 0,5 s.
        radius=2
        smooth=[]
        for i in range(n):
            lo=max(0,i-radius); hi=min(n,i+radius+1)
            smooth.append(sum(raw[lo:hi])/max(1,hi-lo))

        dist=[0.0]*n
        for i in range(1,n):
            step=self._analysis_geo_distance_m(rows[i-1],rows[i])
            # Protezione contro salti GNSS palesemente impossibili.
            if step<35.0:
                dist[i]=dist[i-1]+step
            else:
                dist[i]=dist[i-1]
        lap_len=max(dist[-1],1.0)

        acc=[0.0]*n
        for i in range(1,n):
            dt=(times[i]-times[i-1])/1000.0
            if dt>0.005:
                acc[i]=((smooth[i]-smooth[i-1])/3.6)/dt

        candidates=[]
        i=1
        while i<n-2:
            if acc[i] <= -1.55 and smooth[i] >= 18.0:
                start=i
                # Recupera l'onset prima della soglia forte.
                while start>1 and acc[start-1] < -0.35 and (times[i]-times[start-1])<=900:
                    start-=1
                end=i
                quiet=0
                j=i+1
                while j<n:
                    if acc[j] > -0.20:
                        quiet+=1
                    else:
                        quiet=0
                    end=j
                    if quiet>=3 or (times[j]-times[start])>4500:
                        end=max(start+1,j-quiet+1)
                        break
                    j+=1
                seg=smooth[start:min(n,end+1)]
                v_start=smooth[start]
                v_min=min(seg) if seg else v_start
                duration=max(0.0,(times[end]-times[start])/1000.0)
                drop=v_start-v_min
                if duration>=0.22 and drop>=4.0 and v_start>=20.0:
                    min_idx=start+seg.index(v_min) if seg else start
                    candidates.append({
                        'lap':int(lap_no),'start_idx':start,'end_idx':end,'min_idx':min_idx,
                        'start_ms':times[start],'end_ms':times[end],
                        'duration_s':duration,'start_speed':v_start,'min_speed':v_min,
                        'drop_kmh':drop,'distance_m':dist[start],
                        'fraction':dist[start]/lap_len,
                        'end_distance_m':dist[end],
                        'end_fraction':dist[end]/lap_len,
                        'min_distance_m':dist[min_idx],
                        'min_fraction':dist[min_idx]/lap_len,
                        'latitude':float(rows[start]['latitude']),
                        'longitude':float(rows[start]['longitude']),
                    })
                i=max(i+1,end)
            else:
                i+=1

        # Un'unica frenata può spezzarsi in due per un breve plateau di velocità.
        merged=[]
        for ev in candidates:
            if merged and ev['start_ms']-merged[-1]['end_ms']<=700 and ev['distance_m']-merged[-1]['distance_m']<=35:
                prev=merged[-1]
                prev['end_ms']=max(prev['end_ms'],ev['end_ms'])
                prev['end_idx']=max(prev.get('end_idx',0),ev.get('end_idx',0))
                if ev.get('end_distance_m',0.0)>=prev.get('end_distance_m',0.0):
                    prev['end_distance_m']=ev.get('end_distance_m',prev.get('end_distance_m',0.0))
                    prev['end_fraction']=ev.get('end_fraction',prev.get('end_fraction',prev.get('fraction',0.0)))
                if ev['min_speed']<prev['min_speed']:
                    prev['min_speed']=ev['min_speed'];prev['min_idx']=ev.get('min_idx',prev.get('min_idx'))
                    prev['min_distance_m']=ev.get('min_distance_m',prev.get('min_distance_m',prev.get('distance_m',0.0)))
                    prev['min_fraction']=ev.get('min_fraction',prev.get('min_fraction',prev.get('fraction',0.0)))
                prev['duration_s']=(prev['end_ms']-prev['start_ms'])/1000.0
                prev['drop_kmh']=prev['start_speed']-prev['min_speed']
            else:
                merged.append(ev)
        return merged,lap_len

    def _analysis_build_brake_analysis(self,selected=None):
        selected=list(selected if selected is not None else self._selected_laps())
        selected=[int(x) for x in selected if int(x) in self._analysis_lap_stats_by_no]
        if not selected:
            self._analysis_brake_events=[];self._analysis_brake_groups=[]
            return [],[]

        events=[]; lengths=[]; profiles={}
        for lap_no in selected:
            rows=(self._analysis_lap_stats_by_no.get(lap_no) or {}).get('pts',[]) or []
            profiles[int(lap_no)]=self._analysis_distance_time_profile(rows,(self._analysis_lap_stats_by_no.get(lap_no) or {}).get('lap'))
            evs,length=self._analysis_detect_braking_events(lap_no,rows)
            if length>10:lengths.append(length)
            events.extend(evs)
        if not events:
            self._analysis_brake_events=[];self._analysis_brake_groups=[]
            return [],[]

        median_len=sorted(lengths)[len(lengths)//2] if lengths else 1000.0
        for ev in events:
            ev['norm_m']=ev['fraction']*median_len
            ev['end_norm_m']=ev.get('end_fraction',ev['fraction'])*median_len
            ev['min_norm_m']=ev.get('min_fraction',ev['fraction'])*median_len

        # Raggruppa frenate che appartengono alla stessa zona della pista.
        threshold=max(35.0,min(70.0,median_len*0.055))
        groups=[]
        for ev in sorted(events,key=lambda x:x['norm_m']):
            best=None;best_d=None
            for g in groups:
                d=abs(ev['norm_m']-g['center_m'])
                if d<=threshold and (best_d is None or d<best_d):
                    best=g;best_d=d
            if best is None:
                best={'zone':len(groups)+1,'center_m':ev['norm_m'],'events':[]}
                groups.append(best)
            best['events'].append(ev)
            best['center_m']=sum(x['norm_m'] for x in best['events'])/len(best['events'])

        # Una zona deve contenere al massimo un evento per giro. Se un breve
        # rilascio crea due candidati vicini, conserviamo quello più vicino al
        # centro della zona per non falsare il confronto prima/dopo.
        for g in groups:
            chosen={}
            for ev in g['events']:
                lap=int(ev['lap'])
                old=chosen.get(lap)
                if old is None or abs(ev['norm_m']-g['center_m'])<abs(old['norm_m']-g['center_m']):
                    chosen[lap]=ev
            g['events']=list(chosen.values())
            if g['events']:
                g['center_m']=sum(x['norm_m'] for x in g['events'])/len(g['events'])

        # Nel confronto multiplo scartiamo eventi isolati presenti in un solo
        # giro: in genere sono rilasci gas, traffico o rumore e non una zona di
        # frenata ricorrente utile al confronto.
        if len(selected)>1:
            groups=[g for g in groups if len({int(e['lap']) for e in g['events']})>=2]
        groups.sort(key=lambda g:g['center_m'])
        for zi,g in enumerate(groups,1):g['zone']=zi

        # Il riferimento dell'analisi frenate è SEMPRE il giro più veloce
        # fra quelli effettivamente selezionati, indipendentemente dal giro
        # attivo/focus nella tabella Analisi.
        timed_selected=[]
        for lap_no in selected:
            st=self._analysis_lap_stats_by_no.get(int(lap_no)) or {}
            lap=st.get('lap')
            try:lap_ms=int(lap['lap_time_ms'] or 0) if lap is not None else 0
            except Exception:lap_ms=0
            if lap_ms>0:timed_selected.append((lap_ms,int(lap_no)))
        reference=min(timed_selected,key=lambda x:(x[0],x[1]))[1] if timed_selected else int(selected[0])

        flattened=[]
        for g in groups:
            ref_ev=next((e for e in g['events'] if int(e['lap'])==int(reference)),None)
            ref_m=ref_ev['norm_m'] if ref_ev else sorted(e['norm_m'] for e in g['events'])[len(g['events'])//2]

            # Finestra spaziale comune per stimare il tempo perso/guadagnato
            # nella zona di frenata. Comprende l'onset più anticipato e circa
            # 20 m dopo la fine della decelerazione, così include anche la
            # prima parte dell'uscita/riaccelerazione.
            zone_start_m=max(0.0,min(e['norm_m'] for e in g['events'])-8.0)
            zone_end_m=min(median_len,max(e.get('end_norm_m',e['norm_m']) for e in g['events'])+20.0)
            if zone_end_m-zone_start_m<20.0:
                zone_end_m=min(median_len,zone_start_m+20.0)
            f0=zone_start_m/max(median_len,1.0);f1=zone_end_m/max(median_len,1.0)

            def lap_elapsed_for_lap(lap,fraction):
                return self._analysis_profile_lap_elapsed_at_fraction(profiles.get(int(lap)),fraction)

            def lap_delta_at(lap,fraction):
                cur=lap_elapsed_for_lap(lap,fraction);ref=lap_elapsed_for_lap(reference,fraction)
                if cur is None or ref is None:return None
                return (cur-ref)/1000.0

            def zone_time_for_lap(lap):
                t0=lap_elapsed_for_lap(lap,f0);t1=lap_elapsed_for_lap(lap,f1)
                if t0 is None or t1 is None or t1<t0:return None
                return (t1-t0)/1000.0

            ref_zone_time=zone_time_for_lap(reference)
            if ref_zone_time is None:
                vals=[zone_time_for_lap(e['lap']) for e in g['events']]
                vals=[v for v in vals if v is not None]
                ref_zone_time=(sorted(vals)[len(vals)//2] if vals else 0.0)

            # Analisi curva collegata alla frenata. Il punto di minima velocità
            # del giro di riferimento rappresenta il centro/apice dinamico della
            # zona. Ingresso e uscita vengono misurati in due punti fisici comuni
            # a tutti i giri: 15 m prima e 25 m dopo la minima di riferimento.
            # Così i ΔV non confrontano campioni GNSS presi in posizioni diverse.
            if ref_ev is not None:
                corner_center_m=float(ref_ev.get('min_norm_m',ref_ev.get('norm_m',ref_m)))
                ref_min_speed=float(ref_ev.get('min_speed',0.0))
            else:
                mins=sorted(float(e.get('min_norm_m',e.get('norm_m',ref_m))) for e in g['events'])
                corner_center_m=mins[len(mins)//2] if mins else float(ref_m)
                min_speeds=sorted(float(e.get('min_speed',0.0)) for e in g['events'])
                ref_min_speed=min_speeds[len(min_speeds)//2] if min_speeds else 0.0
            corner_entry_m=max(0.0,corner_center_m-15.0)
            corner_exit_m=min(median_len,corner_center_m+25.0)
            corner_entry_f=corner_entry_m/max(median_len,1.0)
            corner_exit_f=corner_exit_m/max(median_len,1.0)
            ref_entry_speed=self._analysis_profile_speed_at_fraction(profiles.get(int(reference)),corner_entry_f)
            ref_exit_speed=self._analysis_profile_speed_at_fraction(profiles.get(int(reference)),corner_exit_f)

            g['zone_start_m']=zone_start_m;g['zone_end_m']=zone_end_m;g['reference_zone_time_s']=ref_zone_time
            g['corner_center_m']=corner_center_m;g['corner_entry_m']=corner_entry_m;g['corner_exit_m']=corner_exit_m
            for ev in sorted(g['events'],key=lambda e:int(e['lap'])):
                e=dict(ev);e['zone']=g['zone'];e['reference_lap']=reference;e['delta_m']=e['norm_m']-ref_m
                # Delta cumulativo del giro calcolato NELLO STESSO PUNTO FISICO
                # in cui questo giro inizia a frenare. Negativo = giro avanti.
                event_fraction=max(0.0,min(1.0,float(e['norm_m'])/max(median_len,1.0)))
                lap_delta=lap_delta_at(e['lap'],event_fraction)
                entry_delta=lap_delta_at(e['lap'],f0)
                exit_delta=lap_delta_at(e['lap'],f1)
                zt=zone_time_for_lap(e['lap'])
                e['zone_time_s']=float(zt if zt is not None else 0.0)
                e['lap_delta_at_brake_s']=float(lap_delta if lap_delta is not None else 0.0)
                # I valori mostrati nella tabella sono a 3 decimali. Per garantire
                # coerenza matematica visibile, memorizziamo PRIMA e DOPO già
                # arrotondati e calcoliamo GUAD./PERSO esclusivamente da questi.
                entry_disp=round(float(entry_delta if entry_delta is not None else 0.0),3)
                exit_disp=round(float(exit_delta if exit_delta is not None else 0.0),3)
                e['lap_delta_entry_s']=entry_disp
                e['lap_delta_exit_s']=exit_disp
                # Effetto zona = Δ DOPO visualizzato - Δ PRIMA visualizzato.
                # + = tempo perso, - = tempo guadagnato.
                if entry_delta is not None and exit_delta is not None:
                    effect=round(exit_disp-entry_disp,3)
                else:
                    effect=round(e['zone_time_s']-float(ref_zone_time or 0.0),3)
                e['brake_effect_s']=effect
                e['delta_time_s']=effect  # compatibilità con versioni precedenti
                e['zone_start_m']=zone_start_m;e['zone_end_m']=zone_end_m

                # Velocità curva: ingresso e uscita nello stesso punto fisico
                # del giro di riferimento; minima rilevata nella decelerazione.
                v_entry=self._analysis_profile_speed_at_fraction(profiles.get(int(e['lap'])),corner_entry_f)
                v_exit=self._analysis_profile_speed_at_fraction(profiles.get(int(e['lap'])),corner_exit_f)
                v_min=float(e.get('min_speed',0.0))
                e['corner_center_m']=corner_center_m
                e['corner_entry_m']=corner_entry_m;e['corner_exit_m']=corner_exit_m
                e['corner_entry_speed']=float(v_entry if v_entry is not None else 0.0)
                e['corner_min_speed']=v_min
                e['corner_exit_speed']=float(v_exit if v_exit is not None else 0.0)
                e['corner_dv_entry']=e['corner_entry_speed']-float(ref_entry_speed if ref_entry_speed is not None else e['corner_entry_speed'])
                e['corner_dv_min']=v_min-float(ref_min_speed)
                e['corner_dv_exit']=e['corner_exit_speed']-float(ref_exit_speed if ref_exit_speed is not None else e['corner_exit_speed'])
                flattened.append(e)
        self._analysis_brake_events=flattened
        self._analysis_brake_groups=groups
        return flattened,groups

    def _analysis_open_braking_analysis(self):
        selected=self._selected_laps()
        if not selected:
            QMessageBox.information(self,'Analisi frenate','Seleziona almeno un giro nella tabella.')
            return
        events,groups=self._analysis_build_brake_analysis(selected)
        if not events:
            QMessageBox.information(self,'Analisi frenate','Non ho rilevato frenate significative nei giri selezionati.')
            return
        self._analysis_show_brakes=True
        self.render_analysis()

        dlg=QDialog(self);dlg.setWindowTitle('GOATS RT - Analisi frenata e velocità curva · modalità selezionabile');dlg.resize(1520,700)
        lay=QVBoxLayout(dlg)
        ref=events[0].get('reference_lap') if events else None
        info=QLabel(
            f'Confronto dei giri selezionati. Riferimento automatico: Giro {ref}, il più veloce tra quelli selezionati. '
            'Δ PUNTO FRENO indica DOVE inizi a frenare. Δ PRIMA/DOPO e GUAD./PERSO ZONA mostrano l’effetto sul tempo. '
            'Per la curva vengono confrontate V INGRESSO, V MINIMA e V USCITA. Ingresso e uscita sono misurati '
            'nello stesso punto fisico per tutti i giri (circa 15 m prima e 25 m dopo la minima del giro di riferimento); '
            'i relativi ΔV sono positivi quando quel giro è più veloce del riferimento. La rilevazione è stimata dalla velocità GNSS.'
        )
        info.setWordWrap(True);info.setObjectName('muted');lay.addWidget(info)

        # Tempi dei giri selezionati: sempre visibili sopra alla tabella, con il
        # giro di riferimento evidenziato esplicitamente.
        lap_time_parts=[]
        selected_lap_ms={}
        for lap_no in selected:
            st=self._analysis_lap_stats_by_no.get(int(lap_no))
            lap_ms=int(st['lap']['lap_time_ms'] or 0) if st is not None else 0
            selected_lap_ms[int(lap_no)]=lap_ms
            suffix='  (RIF.)' if ref is not None and int(lap_no)==int(ref) else ''
            lap_time_parts.append(f'Giro {int(lap_no)}: {fmt_ms(lap_ms)}{suffix}')
        potential_ms=self._session_potential_lap_details(self.current_session_id).get('potential_ms',0)
        potential_txt=(f'   •   GIRO POTENZIALE SESSIONE: {fmt_ms(potential_ms)}' if potential_ms else '')
        laps_header=QLabel('TEMPI GIRI SELEZIONATI   •   ' + '   |   '.join(lap_time_parts) + potential_txt)
        laps_header.setWordWrap(True)
        fh=laps_header.font();fh.setBold(True);laps_header.setFont(fh)
        laps_header.setStyleSheet('padding: 6px 4px;')
        lay.addWidget(laps_header)

        # Filtro di visualizzazione condiviso con le tabelle F1/F2/... sulla mappa.
        mode_row=QHBoxLayout()
        mode_lbl=QLabel('VISUALIZZA:')
        fm=mode_lbl.font();fm.setBold(True);mode_lbl.setFont(fm)
        mode_row.addWidget(mode_lbl)
        btn_brake=QPushButton('SOLO PUNTO FRENATA')
        btn_speed=QPushButton('SOLO VELOCITÀ CURVA')
        btn_both=QPushButton('ENTRAMBI')
        mode_buttons={'brake':btn_brake,'speed':btn_speed,'both':btn_both}
        for b in mode_buttons.values():
            b.setCheckable(True);b.setMinimumHeight(34);mode_row.addWidget(b)
        mode_row.addStretch()
        lay.addLayout(mode_row)

        table=QTableWidget(0,17)
        table.setHorizontalHeaderLabels(['Curva/Zona','Giro','Punto freno [m]','Δ PUNTO FRENO','Δ PRIMA','Δ DOPO','GUAD./PERSO ZONA','V prima freno','V INGRESSO','ΔV IN','V MINIMA','ΔV MIN','V USCITA','ΔV OUT','Calo frenata','Durata frenata','Tempo zona'])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setSelectionBehavior(QAbstractItemView.SelectRows);table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        for ev in sorted(events,key=lambda e:(int(e['zone']),int(e['lap']))):
            r=table.rowCount();table.insertRow(r)
            dm=float(ev['delta_m'])
            delta='RIF.' if int(ev['lap'])==int(ev['reference_lap']) else (f'+{dm:.1f} m (DOPO)' if dm>=0 else f'{dm:.1f} m (PRIMA)')
            lap_dt=float(ev.get('lap_delta_entry_s',0.0));exit_dt=float(ev.get('lap_delta_exit_s',0.0));effect=float(ev.get('brake_effect_s',round(exit_dt-lap_dt,3)))
            if int(ev['lap'])==int(ev['reference_lap']):
                lap_dt_txt=exit_dt_txt=effect_txt='RIF.'
            else:
                lap_dt_txt=(f'+{lap_dt:.3f} s RIT.' if lap_dt>=0 else f'{lap_dt:.3f} s AVANTI')
                exit_dt_txt=(f'+{exit_dt:.3f} s RIT.' if exit_dt>=0 else f'{exit_dt:.3f} s AVANTI')
                effect_txt=(f'+{effect:.3f} s PERSI' if effect>=0 else f'{effect:.3f} s GUAD.')
            is_ref=int(ev['lap'])==int(ev['reference_lap'])
            def dvtxt(v):
                if is_ref:return 'RIF.'
                return f"{float(v):+.1f} km/h"
            vals=[f"C{ev['zone']} / F{ev['zone']}",str(ev['lap']),f"{ev['norm_m']:.1f}",delta,lap_dt_txt,exit_dt_txt,effect_txt,
                  f"{ev['start_speed']:.1f} km/h",f"{ev.get('corner_entry_speed',0.0):.1f} km/h",dvtxt(ev.get('corner_dv_entry',0.0)),
                  f"{ev.get('corner_min_speed',ev['min_speed']):.1f} km/h",dvtxt(ev.get('corner_dv_min',0.0)),
                  f"{ev.get('corner_exit_speed',0.0):.1f} km/h",dvtxt(ev.get('corner_dv_exit',0.0)),
                  f"-{ev['drop_kmh']:.1f} km/h",f"{ev['duration_s']:.2f} s",f"{ev.get('zone_time_s',0.0):.3f} s"]
            for c,val in enumerate(vals):
                it=QTableWidgetItem(val);it.setTextAlignment(Qt.AlignCenter)
                if c==1:it.setBackground(QColor(self._analysis_color_for_lap(ev['lap'])))
                table.setItem(r,c,it)
        # Gruppi di colonne. Zona/Giro restano sempre visibili per identificare
        # immediatamente F1/F2/... anche in modalità filtrata.
        brake_cols={2,3,4,5,6,7,14,15,16}
        speed_cols={8,9,10,11,12,13}
        def apply_analysis_mode(mode):
            if mode not in ('brake','speed','both'):
                mode='both'
            self._analysis_brake_table_mode=mode
            for c in range(table.columnCount()):
                visible=(c in (0,1) or mode=='both' or (mode=='brake' and c in brake_cols) or (mode=='speed' and c in speed_cols))
                table.setColumnHidden(c,not visible)
            for key,b in mode_buttons.items():
                b.blockSignals(True);b.setChecked(key==mode);b.blockSignals(False)
                b.setStyleSheet('font-weight:700;' if key==mode else '')
            # Aggiorna senza ricreare la mappa, così il filtro è immediato anche
            # con la mappa fullscreen e mantiene zoom/posizione correnti.
            if self._map_ready:
                self.map.page().runJavaScript(
                    "window.goatsSetBrakeAnalysisMode && window.goatsSetBrakeAnalysisMode('%s');" % mode
                )

        btn_brake.clicked.connect(lambda _=False: apply_analysis_mode('brake'))
        btn_speed.clicked.connect(lambda _=False: apply_analysis_mode('speed'))
        btn_both.clicked.connect(lambda _=False: apply_analysis_mode('both'))
        apply_analysis_mode(getattr(self,'_analysis_brake_table_mode','both'))

        lay.addWidget(table,1)

        # Gap finale tra i tempi giro selezionati, calcolato direttamente sul
        # tempo completo del giro e riferito allo stesso giro usato nel confronto.
        gap_parts=[]
        ref_ms=selected_lap_ms.get(int(ref),0) if ref is not None else 0
        if ref is not None and ref_ms>0:
            for lap_no in selected:
                lap_no=int(lap_no)
                if lap_no==int(ref):
                    continue
                lap_ms=selected_lap_ms.get(lap_no,0)
                if lap_ms<=0:
                    continue
                gap_s=(lap_ms-ref_ms)/1000.0
                if abs(gap_s)<0.0005:
                    gap_parts.append(f'Giro {lap_no} vs Giro {int(ref)}: 0.000 s (PARI)')
                elif gap_s<0:
                    gap_parts.append(f'Giro {lap_no} vs Giro {int(ref)}: {gap_s:.3f} s (PIÙ VELOCE)')
                else:
                    gap_parts.append(f'Giro {lap_no} vs Giro {int(ref)}: +{gap_s:.3f} s (PIÙ LENTO)')
        gap_label=QLabel('GAP FINALE   •   ' + ('   |   '.join(gap_parts) if gap_parts else '—'))
        gap_label.setWordWrap(True)
        fg=gap_label.font();fg.setBold(True);gap_label.setFont(fg)
        gap_label.setStyleSheet('padding: 7px 4px;')
        lay.addWidget(gap_label)

        row=QHBoxLayout()
        hide=QPushButton('NASCONDI PUNTI FRENATA DALLA MAPPA')
        hide.clicked.connect(lambda: (setattr(self,'_analysis_show_brakes',False),self.render_analysis(),dlg.accept()))
        row.addWidget(hide);row.addStretch()
        close=QPushButton('CHIUDI');close.clicked.connect(dlg.accept);row.addWidget(close);lay.addLayout(row)
        dlg.exec()

    def _analysis_replay_rate(self):
        if not hasattr(self,'replay_speed_combo'):return 1.0
        try:return float(self.replay_speed_combo.currentData() or 1.0)
        except Exception:return 1.0

    def _analysis_replay_toggled(self,checked):
        self._analysis_replay_running=bool(checked)
        if hasattr(self,'replay_btn'):
            self.replay_btn.setText('⏸ PAUSA' if checked else '▶ ANIMA GIRI')
        if not self._map_ready:return
        if checked:
            self.map.page().runJavaScript(f"window.goatsReplayStart && window.goatsReplayStart({self._analysis_replay_rate():.3f});")
        else:
            self.map.page().runJavaScript("window.goatsReplayPause && window.goatsReplayPause();")

    def _analysis_replay_speed_changed(self,*_):
        if self._map_ready:
            self.map.page().runJavaScript(f"window.goatsReplaySetRate && window.goatsReplaySetRate({self._analysis_replay_rate():.3f});")

    def _analysis_replay_reset(self):
        self._analysis_replay_running=False
        if hasattr(self,'replay_btn'):
            self.replay_btn.blockSignals(True);self.replay_btn.setChecked(False);self.replay_btn.setText('▶ ANIMA GIRI');self.replay_btn.blockSignals(False)
        if self._map_ready:
            self.map.page().runJavaScript("window.goatsReplayReset && window.goatsReplayReset();")

    def render_analysis(self,*_):
        if not self.current_session_id:
            return

        # Un cambio di selezione ricrea la mappa: fermiamo il replay per
        # evitare che il pulsante resti in uno stato non sincronizzato.
        self._analysis_replay_running=False
        if hasattr(self,'replay_btn') and self.replay_btn.isChecked():
            self.replay_btn.blockSignals(True);self.replay_btn.setChecked(False);self.replay_btn.setText('▶ ANIMA GIRI');self.replay_btn.blockSignals(False)

        selected=self._selected_laps()
        if selected:
            if self._analysis_focus_lap not in selected:
                self._analysis_focus_lap=selected[0]
        else:
            self._analysis_focus_lap=None

        # Per il confronto multigiro ogni curva parte da t=0 del proprio giro.
        # In questo modo le velocità sono realmente sovrapposte e confrontabili.
        series={}
        if selected:
            for lap_no in selected:
                raw=list(self.store.points(self.current_session_id,lap_no))
                if raw:
                    base=int(raw[0]['elapsed_ms'] or 0)
                    rows=[]
                    for r in raw:
                        d=dict(r)
                        d['elapsed_ms']=max(0,int(r['elapsed_ms'] or 0)-base)
                        rows.append(d)
                    series[f"Giro {lap_no}"]=rows
        else:
            laps=list(self.store.laps(self.current_session_id))
            if not laps:
                raw=list(self.store.points(self.current_session_id,None))
                if raw:
                    base=int(raw[0]['elapsed_ms'] or 0)
                    rows=[]
                    for r in raw:
                        d=dict(r)
                        d['elapsed_ms']=max(0,int(r['elapsed_ms'] or 0)-base)
                        rows.append(d)
                    series['Traccia completa']=rows

        self.render_map(series)
        self.render_chart(series)

    def _analysis_track_data_for_session(self,sid):
        """Trova il JSON del circuito di una sessione, anche in versioni Manager sorelle."""
        if not sid:
            return None
        sess=self.store.session(int(sid))
        if not sess:
            return None
        target=str(sess['track_name'] or '').strip()
        if not target:
            return None

        def norm(v):
            return ''.join(ch.lower() for ch in str(v) if ch.isalnum())

        cache_key=norm(target)
        if cache_key in self._track_data_cache:
            return self._track_data_cache[cache_key]

        roots=[getattr(self,'active_tracks_dir',TRACKS_DIR)]
        try:
            for sibling in APP_DIR.parent.iterdir():
                candidate=sibling/'tracks'
                if sibling != APP_DIR and candidate.is_dir():
                    roots.append(candidate)
        except Exception:
            pass

        seen=set(); candidates=[]
        for root in roots:
            try:
                paths=root.rglob('*.json')
            except Exception:
                continue
            for path in paths:
                key=str(path.resolve())
                if key in seen:
                    continue
                seen.add(key)
                try:
                    data=json.loads(path.read_text(encoding='utf-8'))
                except Exception:
                    continue
                name=str(data.get('name','')).strip()
                track_id=str(data.get('id','')).strip()
                if name.casefold()==target.casefold() or track_id.casefold()==target.casefold():
                    self._track_data_cache[cache_key]=data
                    return data
                candidates.append((name,track_id,data))

        nt=norm(target)
        for name,track_id,data in candidates:
            if norm(name)==nt or norm(track_id)==nt:
                self._track_data_cache[cache_key]=data
                return data
        self._track_data_cache[cache_key]=None
        return None

    def _analysis_track_data(self):
        return self._analysis_track_data_for_session(self.current_session_id)

    @staticmethod
    def _analysis_segment_cross_fraction(p0,p1,line):
        """Frazione t (0..1) del segmento GPS p0->p1 che interseca la linea."""
        try:
            lat0=float(p0['latitude']); lon0=float(p0['longitude'])
            lat1=float(p1['latitude']); lon1=float(p1['longitude'])
            alat=float(line['lat1']); alon=float(line['lon1'])
            blat=float(line['lat2']); blon=float(line['lon2'])
        except Exception:
            return None

        # Proiezione locale equirettangolare: sufficiente su un circuito e
        # conserva il parametro di intersezione lungo il segmento.
        ref_lat=math.radians((lat0+lat1+alat+blat)/4.0)
        k=math.cos(ref_lat)
        ax=lon0*k; ay=lat0
        bx=lon1*k; by=lat1
        cx=alon*k; cy=alat
        dx=blon*k; dy=blat
        rx=bx-ax; ry=by-ay
        sx=dx-cx; sy=dy-cy
        den=rx*sy-ry*sx
        if abs(den)<1e-15:
            return None
        qpx=cx-ax; qpy=cy-ay
        t=(qpx*sy-qpy*sx)/den
        u=(qpx*ry-qpy*rx)/den
        eps=1e-9
        if -eps <= t <= 1.0+eps and -eps <= u <= 1.0+eps:
            return max(0.0,min(1.0,float(t)))
        return None

    @staticmethod
    def _analysis_interp_elapsed(p0,p1,t):
        a=float(p0['elapsed_ms']); b=float(p1['elapsed_ms'])
        return a+(b-a)*float(t)

    def _analysis_sector_times_for_lap(self,all_points,lap_no,track_data):
        """
        Ricostruisce S1..Sn dalla geometria del circuito e dalla traccia GPS.
        Le linee JSON sono split intermedi; l'ultimo settore termina al finish.
        """
        if not track_data:
            return []
        sectors=list(track_data.get('sectors',[]) or [])
        finish=track_data.get('start_line') or {}
        if not sectors or not finish or len(all_points)<2:
            return []

        idx=[
            i for i,p in enumerate(all_points)
            if int(p['lap'] or 0)==int(lap_no)
        ]
        if len(idx)<2:
            return [None]*(len(sectors)+1)
        first_i,last_i=idx[0],idx[-1]

        start_ms=float(all_points[first_i]['elapsed_ms'])
        if first_i>0:
            t=self._analysis_segment_cross_fraction(
                all_points[first_i-1],all_points[first_i],finish
            )
            if t is not None:
                start_ms=self._analysis_interp_elapsed(
                    all_points[first_i-1],all_points[first_i],t
                )

        end_ms=float(all_points[last_i]['elapsed_ms'])
        if last_i+1 < len(all_points):
            t=self._analysis_segment_cross_fraction(
                all_points[last_i],all_points[last_i+1],finish
            )
            if t is not None:
                end_ms=self._analysis_interp_elapsed(
                    all_points[last_i],all_points[last_i+1],t
                )

        cross_times=[]
        search_i=max(0,first_i-1)
        max_seg=min(last_i,len(all_points)-2)
        for sector in sectors:
            found=None
            found_i=None
            for i in range(search_i,max_seg+1):
                t=self._analysis_segment_cross_fraction(
                    all_points[i],all_points[i+1],sector
                )
                if t is None:
                    continue
                cross=self._analysis_interp_elapsed(all_points[i],all_points[i+1],t)
                if cross+1e-6 < start_ms:
                    continue
                if cross-1e-6 > end_ms:
                    continue
                found=cross;found_i=i
                break
            cross_times.append(found)
            if found_i is not None:
                search_i=found_i

        boundaries=[start_ms]+cross_times+[end_ms]
        out=[]
        for i in range(len(boundaries)-1):
            a=boundaries[i];b=boundaries[i+1]
            if a is None or b is None or b<a:
                out.append(None)
            else:
                out.append(int(round(b-a)))
        return out

    def _session_potential_lap_details(self,sid):
        """
        Giro potenziale = somma del miglior tempo rilevato in ciascun settore
        della sessione, usando esclusivamente i giri completi/validi.
        Richiede la geometria dei settori del circuito.
        """
        try:
            sid=int(sid)
        except Exception:
            return {'potential_ms':0,'best_sector_times':[],'sector_count':0}
        cached=self._potential_lap_cache.get(sid)
        if cached is not None:
            return cached
        sess=self.store.session(sid)
        track_data=self._analysis_track_data_for_session(sid)
        sectors=list((track_data or {}).get('sectors',[]) or [])
        if sess is None or not sectors:
            out={'potential_ms':0,'best_sector_times':[],'sector_count':0}
            self._potential_lap_cache[sid]=out
            return out

        all_points=list(self.store.points(sid,None))
        laps=list(self.store.laps(sid))
        point_laps=sorted({int(p['lap'] or 0) for p in all_points if int(p['lap'] or 0)>0})
        open_final_lap=(point_laps[-1] if str(sess['source_format'] or '')=='SDCSV' and point_laps else None)
        positive=[
            lap for lap in laps
            if int(lap['lap_time_ms'] or 0)>0
            and (open_final_lap is None or int(lap['lap'])!=open_final_lap)
        ]
        ref=next((lap for lap in positive if int(lap['lap'])==2),None)
        ref_ms=int(ref['lap_time_ms'] or 0) if ref is not None else 0
        valid=[lap for lap in positive if not ref_ms or int(lap['lap_time_ms'] or 0)>=ref_ms*0.80]

        count=len(sectors)+1
        best=[None]*count
        for lap in valid:
            lap_no=int(lap['lap'])
            times=self._analysis_sector_times_for_lap(all_points,lap_no,track_data)
            for i in range(min(count,len(times))):
                value=times[i]
                if value is None or int(value)<=0:
                    continue
                value=int(value)
                if best[i] is None or value<best[i]:
                    best[i]=value
        potential=(
            int(sum(int(x) for x in best))
            if count>0 and all(x is not None and int(x)>0 for x in best)
            else 0
        )
        out={'potential_ms':potential,'best_sector_times':best,'sector_count':count}
        self._potential_lap_cache[sid]=out
        return out

    @staticmethod
    def _analysis_color_for_lap(lap_no):
        palette=[
            '#00d084','#ffd600','#ff5c5c','#4da3ff',
            '#c17cff','#ff9f43','#7bed9f','#70a1ff',
            '#00e5ff','#f78fb3','#a3cb38','#e58e26'
        ]
        try:
            idx=max(0,int(lap_no)-1)
        except Exception:
            idx=0
        return palette[idx % len(palette)]

    def _analysis_color_for_series(self,name,index=0):
        m=re.search(r'(\d+)',str(name))
        return self._analysis_color_for_lap(int(m.group(1))) if m else self._analysis_color_for_lap(index+1)

    def render_map(self,series):
        track_data=self._analysis_track_data() or {}
        sectors=list(track_data.get('sectors',[]) or [])
        start_line=track_data.get('start_line') or None

        active_lap=self._analysis_focus_lap
        active_stats=(
            self._analysis_lap_stats_by_no.get(int(active_lap))
            if active_lap is not None else None
        )
        active_sector_times=list((active_stats or {}).get('sector_times',[]) or [])

        def sector_text(ms):
            if ms is None or int(ms)<=0:
                return '--.---'
            ms=int(ms)
            if ms < 60000:
                return f'{ms/1000.0:.3f}'
            return fmt_ms(ms)

        sector_time_labels=[sector_text(x) for x in active_sector_times]

        js_series={}
        names=list(series.keys())
        for idx,name in enumerate(names):
            rows=series[name]
            js_series[name]={
                'color':self._analysis_color_for_series(name,idx),
                'points':[
                    [float(r['latitude']),float(r['longitude']),
                     float(r['speed_kmh']),float(r['elapsed_ms'])]
                    for r in rows
                    if r['latitude'] and r['longitude']
                ]
            }

        all_points=[p for entry in js_series.values() for p in entry['points']]
        center=all_points[0][:2] if all_points else [45.0,9.0]

        brake_payload=[]
        selected_laps=[]
        for name in names:
            m=re.search(r'(\d+)',str(name))
            if m:selected_laps.append(int(m.group(1)))
        events,_groups=self._analysis_build_brake_analysis(selected_laps) if selected_laps else ([],[])
        for ev in events:
            brake_payload.append({
                'lap':int(ev['lap']),'zone':int(ev['zone']),'series':f"Giro {int(ev['lap'])}",
                'lat':float(ev['latitude']),'lon':float(ev['longitude']),
                'start_ms':float(ev['start_ms']),'end_ms':float(ev['end_ms']),
                'v0':float(ev['start_speed']),'vmin':float(ev['min_speed']),
                'drop':float(ev.get('drop_kmh',0.0)),'duration':float(ev.get('duration_s',0.0)),
                'point_m':float(ev.get('norm_m',0.0)),'delta_m':float(ev['delta_m']),
                'zone_time':float(ev.get('zone_time_s',0.0)),'delta_time':float(ev.get('delta_time_s',0.0)),
                'lap_delta':float(ev.get('lap_delta_entry_s',0.0)),
                'lap_delta_entry':float(ev.get('lap_delta_entry_s',0.0)),
                'lap_delta_exit':float(ev.get('lap_delta_exit_s',0.0)),
                'brake_effect':float(ev.get('brake_effect_s',round(float(ev.get('lap_delta_exit_s',0.0))-float(ev.get('lap_delta_entry_s',0.0)),3))),
                'v_entry':float(ev.get('corner_entry_speed',0.0)),
                'dv_entry':float(ev.get('corner_dv_entry',0.0)),
                'v_corner_min':float(ev.get('corner_min_speed',ev.get('min_speed',0.0))),
                'dv_min':float(ev.get('corner_dv_min',0.0)),
                'v_exit':float(ev.get('corner_exit_speed',0.0)),
                'dv_exit':float(ev.get('corner_dv_exit',0.0)),
                'reference_lap':int(ev.get('reference_lap',ev['lap'])),
                'color':self._analysis_color_for_lap(ev['lap']),
            })

        html=f"""<!doctype html><html><head><meta charset="utf-8">
<style>
html,body,#map{{height:100%;margin:0;background:#10151c;color:#dfe7ef}}
.hoverInfo{{background:rgba(12,17,23,.94);color:#fff;padding:8px 11px;border:1px solid #56606b;border-radius:7px;font:12px Segoe UI;box-shadow:0 1px 5px #0008;min-width:135px}}
.sector-label{{background:transparent;border:0}}
.sector-label div{{color:#111;font:bold 12px Segoe UI;padding:3px 6px;border-radius:5px;border:2px solid #111;text-align:center;white-space:nowrap;line-height:1.15}}
.finish-label{{background:transparent;border:0}}
.finish-label div{{color:white;background:#d71920;font:bold 12px Segoe UI;padding:4px 7px;border-radius:5px;border:2px solid white;text-align:center;white-space:nowrap}}
.brake-label{{background:transparent;border:0}}
.brake-label div{{color:white;background:rgba(15,20,27,.94);font:bold 11px Segoe UI;padding:3px 6px;border-radius:5px;border:2px solid white;white-space:nowrap}}
#fsBrakePanel{{display:none;position:absolute;z-index:1350;left:62px;top:12px;max-width:min(760px,calc(100% - 330px));background:rgba(8,12,17,.94);color:#eef3f8;border:1px solid rgba(255,255,255,.35);border-radius:8px;padding:9px 12px;font:12px Segoe UI;box-shadow:0 3px 14px rgba(0,0,0,.45);pointer-events:none}}
#fsBrakePanel .title{{font-weight:800;margin-bottom:5px;letter-spacing:.2px}}
#fsBrakePanel .idle{{color:#b9c4cf}}
#fsBrakePanel .brRow{{padding:4px 0;border-top:1px solid rgba(255,255,255,.13);line-height:1.35}}
#fsBrakePanel .brRow:first-of-type{{border-top:0}}
#fsBrakePanel .dot{{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;border:1px solid #fff;vertical-align:-1px}}
#fsBrakePanel .deltaPoint,#fsBrakePanel .deltaTime{{font-weight:800}}
.brake-zone-table{{background:transparent!important;border:0!important;overflow:visible!important}}
.brake-zone-table .bzWrap{{width:var(--bz-width,292px);background:rgba(8,12,17,.94);color:#f3f6f9;border:1px solid rgba(255,255,255,.72);border-radius:7px;box-shadow:0 2px 8px rgba(0,0,0,.48);font:10px Segoe UI;line-height:1.15;overflow:hidden;pointer-events:none;transform:scale(var(--bz-scale,1));transform-origin:center center;transition:transform .10s ease-out,width .10s ease-out}}
#brakeModeControl{{position:absolute;z-index:1400;right:12px;top:12px;display:none;gap:5px;padding:6px;background:rgba(8,12,17,.92);border:1px solid rgba(255,255,255,.40);border-radius:8px;box-shadow:0 2px 10px rgba(0,0,0,.40);font:11px Segoe UI}}
#brakeModeControl button{{cursor:pointer;color:#eaf0f6;background:#202a35;border:1px solid #66717d;border-radius:5px;padding:6px 9px;font-weight:700}}
#brakeModeControl button.active{{background:#e7edf4;color:#10151c;border-color:#fff}}
.brake-zone-table .bzHead{{display:flex;align-items:center;justify-content:space-between;padding:4px 6px;background:rgba(255,255,255,.09);font-weight:800;border-bottom:1px solid rgba(255,255,255,.22)}}
.brake-zone-table .bzRef{{font-size:9px;color:#cbd5df;font-weight:600}}
.brake-zone-table table{{width:100%;border-collapse:collapse;table-layout:fixed}}
.brake-zone-table th{{font-size:9px;color:#bfcbd6;font-weight:700;padding:3px 4px;border-bottom:1px solid rgba(255,255,255,.16);text-align:left}}
.brake-zone-table td{{padding:3px 4px;border-bottom:1px solid rgba(255,255,255,.09);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.brake-zone-table tr:last-child td{{border-bottom:0}}
.brake-zone-table .bzLap{{font-weight:800;width:39px}}
.brake-zone-table .bzDot{{display:inline-block;width:8px;height:8px;border-radius:50%;border:1px solid #fff;margin-right:4px;vertical-align:-1px}}
.brake-zone-table .bzDP{{width:76px;font-weight:700}}
.brake-zone-table .bzLapDelta{{width:78px;font-weight:700}}
.brake-zone-table .bzEffect{{font-weight:700}}
.brake-zone-table .bzRow.active td{{background:rgba(255,255,255,.18);color:#fff}}
.brake-zone-table .bzRow.active .bzLap{{text-decoration:underline}}
.brake-zone-table .gain{{color:#74f29a}}
.brake-zone-table .loss{{color:#ff9a9a}}
.brake-zone-table .ref{{color:#d7dee6}}

#fsSpeedPanel{{display:none;position:absolute;z-index:1200;left:0;right:0;bottom:0;height:220px;background:rgba(8,12,17,.91);border-top:2px solid rgba(255,255,255,.28);box-shadow:0 -4px 18px rgba(0,0,0,.45);font-family:Segoe UI;color:#eef3f8;backdrop-filter:blur(3px)}}
#fsSpeedHeader{{height:34px;display:flex;align-items:center;justify-content:space-between;padding:0 14px;border-bottom:1px solid rgba(255,255,255,.14);font-size:13px;box-sizing:border-box}}
#fsSpeedTitle{{font-weight:700}}
#fsSpeedValue{{font-size:14px;font-weight:800;white-space:nowrap}}
#fsSpeedSvg{{display:block;width:100%;height:184px;cursor:crosshair}}
.fsGrid{{stroke:rgba(255,255,255,.14);stroke-width:1}}
.fsAxisText{{fill:#c9d3de;font:11px Segoe UI}}
.fsSpeedPath{{fill:none;stroke-width:3;stroke-linejoin:round;stroke-linecap:round}}
#fsCursorLine{{stroke:#fff;stroke-width:2;opacity:0}}
#fsCursorDot{{fill:#0b0f14;stroke:#fff;stroke-width:3;opacity:0}}
</style>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"></head>
<body><div id="map"></div>
<div id="brakeModeControl"><button data-mode="brake">FRENATA</button><button data-mode="speed">VELOCITÀ CURVA</button><button data-mode="both">ENTRAMBI</button></div>
<div id="fsBrakePanel"><div class="title">DATI FRENATA DURANTE IL REPLAY</div><div class="idle">Le tabelle mostrano Δ PRIMA e GUAD./PERSO ZONA; la riga attiva si evidenzia durante il replay.</div></div>
<div id="fsSpeedPanel">
  <div id="fsSpeedHeader"><span id="fsSpeedTitle">Velocità giro selezionato</span><span id="fsSpeedValue">Muovi il mouse sulla curva</span></div>
  <svg id="fsSpeedSvg" viewBox="0 0 1200 184" preserveAspectRatio="none" aria-label="Grafico velocità giro selezionato"></svg>
</div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const SERIES={json.dumps(js_series)};
const SECTORS={json.dumps(sectors)};
const STARTLINE={json.dumps(start_line)};
const ACTIVE_LAP={json.dumps(active_lap)};
const SECTOR_TIMES={json.dumps(sector_time_labels)};
const BRAKES={json.dumps(brake_payload)};
const SHOW_BRAKES={json.dumps(bool(self._analysis_show_brakes))};
let BRAKE_ANALYSIS_MODE={json.dumps(getattr(self,'_analysis_brake_table_mode','both'))};
const map=L.map('map',{{minZoom:2,maxZoom:23,zoomSnap:0.25,zoomDelta:0.5}}).setView({json.dumps(center)},18);
map.createPane('brakeConnectorPane');map.getPane('brakeConnectorPane').style.zIndex='425';map.getPane('brakeConnectorPane').style.pointerEvents='none';
map.createPane('brakeTablePane');map.getPane('brakeTablePane').style.zIndex='440';map.getPane('brakeTablePane').style.pointerEvents='none';
map.createPane('replayPane');map.getPane('replayPane').style.zIndex='680';map.getPane('replayPane').style.pointerEvents='none';
const sat=L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}',{{maxNativeZoom:19,maxZoom:23,attribution:'Tiles &copy; Esri'}}).addTo(map);
const osm=L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',{{maxNativeZoom:19,maxZoom:23,attribution:'&copy; OpenStreetMap contributors'}});
const blank=L.tileLayer('',{{maxZoom:23,attribution:''}});
L.control.layers({{'Satellite (overzoom)':sat,'Stradale OSM (overzoom)':osm,'Solo traccia':blank}},null,{{collapsed:true}}).addTo(map);

const hoverMarker=L.circleMarker({json.dumps(center)},{{radius:13,color:'#ffffff',weight:4,fillColor:'#00d084',fillOpacity:1,opacity:0}}).addTo(map);
hoverMarker.bringToFront();
const hoverInfo=L.control({{position:'topright'}});
hoverInfo.onAdd=function(){{const div=L.DomUtil.create('div','hoverInfo');div.id='hoverInfo';div.innerHTML='Mouse sulla traiettoria o sul grafico';return div;}};
hoverInfo.addTo(map);

function nearestByTime(P,ms){{
  if(!P || !P.length)return null;
  let best=P[0],bestD=Math.abs(P[0][3]-ms);
  for(let i=1;i<P.length;i++){{const d=Math.abs(P[i][3]-ms);if(d<bestD){{best=P[i];bestD=d;}}}}
  return best;
}}
function pointByTime(P,ms){{
  if(!P || !P.length)return null;
  if(ms<=P[0][3])return P[0].slice();
  const last=P[P.length-1];if(ms>=last[3])return last.slice();
  let lo=0,hi=P.length-1;
  while(hi-lo>1){{const mid=(lo+hi)>>1;if(P[mid][3]<=ms)lo=mid;else hi=mid;}}
  const a=P[lo],b=P[hi],dt=b[3]-a[3];
  const t=dt>0?Math.max(0,Math.min(1,(ms-a[3])/dt)):0;
  return [a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,a[2]+(b[2]-a[2])*t,a[3]+(b[3]-a[3])*t];
}}

function activeSpeedSeriesName(){{
  const preferred=(ACTIVE_LAP!==null)?('Giro '+ACTIVE_LAP):null;
  if(preferred && SERIES[preferred] && SERIES[preferred].points.length)return preferred;
  const keys=Object.keys(SERIES);return keys.length?keys[0]:null;
}}
function drawFullscreenSpeedGraph(){{
  const panel=document.getElementById('fsSpeedPanel'),svg=document.getElementById('fsSpeedSvg');
  if(!panel || !svg || panel.style.display==='none')return;
  const name=activeSpeedSeriesName(),entry=name?SERIES[name]:null,P=entry?entry.points:[];
  const title=document.getElementById('fsSpeedTitle'),value=document.getElementById('fsSpeedValue');
  if(title)title.textContent=(name||'Giro')+' — Velocità';
  if(!P || P.length<2){{svg.innerHTML='';if(value)value.textContent='Dati velocità non disponibili';return;}}
  const W=1200,H=184,L=58,R=18,T=12,B=30,pw=W-L-R,ph=H-T-B;
  const t0=P[0][3],t1=P[P.length-1][3],dur=Math.max(1,t1-t0);
  let vmin=Infinity,vmax=-Infinity;for(const p of P){{vmin=Math.min(vmin,p[2]);vmax=Math.max(vmax,p[2]);}}
  const pad=Math.max(3,(vmax-vmin)*.08);vmin=Math.max(0,vmin-pad);vmax=vmax+pad;if(vmax<=vmin)vmax=vmin+10;
  const x=ms=>L+((ms-t0)/dur)*pw;const y=v=>T+(1-(v-vmin)/(vmax-vmin))*ph;
  let parts=[];
  for(let i=0;i<=4;i++){{const yy=T+i*ph/4;const vv=vmax-i*(vmax-vmin)/4;parts.push('<line class="fsGrid" x1="'+L+'" y1="'+yy+'" x2="'+(W-R)+'" y2="'+yy+'"/><text class="fsAxisText" x="6" y="'+(yy+4)+'">'+vv.toFixed(0)+'</text>');}}
  for(let i=0;i<=5;i++){{const xx=L+i*pw/5;const ss=((t0+i*dur/5-t0)/1000);parts.push('<line class="fsGrid" x1="'+xx+'" y1="'+T+'" x2="'+xx+'" y2="'+(H-B)+'"/><text class="fsAxisText" text-anchor="middle" x="'+xx+'" y="'+(H-8)+'">'+ss.toFixed(1)+' s</text>');}}
  const step=Math.max(1,Math.floor(P.length/3000));let pts=[];for(let i=0;i<P.length;i+=step)pts.push(x(P[i][3]).toFixed(2)+','+y(P[i][2]).toFixed(2));if((P.length-1)%step)pts.push(x(P[P.length-1][3]).toFixed(2)+','+y(P[P.length-1][2]).toFixed(2));
  parts.push('<polyline class="fsSpeedPath" stroke="'+entry.color+'" points="'+pts.join(' ')+'"/>');
  parts.push('<line id="fsCursorLine" x1="0" y1="'+T+'" x2="0" y2="'+(H-B)+'"/><circle id="fsCursorDot" cx="0" cy="0" r="6"/>');
  svg.innerHTML=parts.join('');
  svg.onmousemove=function(ev){{
    const rect=svg.getBoundingClientRect();if(!rect.width)return;
    const sx=(ev.clientX-rect.left)*(W/rect.width);const clamped=Math.max(L,Math.min(W-R,sx));
    const ms=t0+((clamped-L)/pw)*dur;const pt=pointByTime(P,ms);if(!pt)return;
    const xx=x(pt[3]),yy=y(pt[2]);const line=document.getElementById('fsCursorLine'),dot=document.getElementById('fsCursorDot');
    if(line){{line.setAttribute('x1',xx);line.setAttribute('x2',xx);line.style.opacity='1';}}
    if(dot){{dot.setAttribute('cx',xx);dot.setAttribute('cy',yy);dot.style.opacity='1';}}
    if(value)value.innerHTML='<b>'+pt[2].toFixed(1)+' km/h</b> · '+((pt[3]-t0)/1000).toFixed(3)+' s';
    showPoint(name,pt);
  }};
  svg.onmouseleave=function(){{const line=document.getElementById('fsCursorLine'),dot=document.getElementById('fsCursorDot');if(line)line.style.opacity='0';if(dot)dot.style.opacity='0';if(value)value.textContent='Muovi il mouse sulla curva';hidePoint();}};
}}
let fullscreenMode=false;
let fullscreenBraking=BRAKE_ANALYSIS_MODE!=='speed';
let fullscreenCornerSpeed=BRAKE_ANALYSIS_MODE!=='brake';
let fullscreenSpeedGraph=true;
const brakeMarkers=[];
function fullscreenAnalysesVisible(){{return fullscreenBraking||fullscreenCornerSpeed;}}
function applyFullscreenOverlays(){{
  const graphVisible=fullscreenMode&&fullscreenSpeedGraph;
  const analysesVisible=fullscreenMode&&fullscreenAnalysesVisible();
  const panel=document.getElementById('fsSpeedPanel'),brakePanel=document.getElementById('fsBrakePanel');
  if(panel)panel.style.display=graphVisible?'block':'none';
  if(brakePanel)brakePanel.style.display='none';
  // In fullscreen i controlli Qt permettono anche di nascondere entrambe le analisi.
  const modeControl=document.getElementById('brakeModeControl');
  if(modeControl)modeControl.style.display=(!fullscreenMode&&SHOW_BRAKES)?'flex':'none';
  setBrakeZoneTablesVisible(analysesVisible);
  brakeMarkers.forEach(marker=>{{
    if(fullscreenMode?analysesVisible:SHOW_BRAKES){{if(!map.hasLayer(marker))marker.addTo(map);}}
    else{{marker.closeTooltip();if(map.hasLayer(marker))map.removeLayer(marker);}}
  }});
  if(!analysesVisible){{
    setBrakeTableActive([]);
    if(fullscreenMode)Object.values(replayMarkers).forEach(marker=>marker.setRadius(9));
  }}
  if(graphVisible)setTimeout(drawFullscreenSpeedGraph,80);
  if(analysesVisible)setTimeout(layoutBrakeZoneTables,140);
  setTimeout(()=>map.invalidateSize(),120);
}}
window.goatsSetFullscreenMode=function(on){{
  fullscreenMode=!!on;
  applyFullscreenOverlays();
}};
window.goatsSetFullscreenOverlays=function(braking,cornerSpeed,speedGraph){{
  fullscreenBraking=!!braking;fullscreenCornerSpeed=!!cornerSpeed;fullscreenSpeedGraph=!!speedGraph;
  if(fullscreenAnalysesVisible()){{
    const mode=fullscreenBraking?(fullscreenCornerSpeed?'both':'brake'):'speed';
    window.goatsSetBrakeAnalysisMode(mode);
  }}
  applyFullscreenOverlays();
}};
window.addEventListener('resize',()=>{{const p=document.getElementById('fsSpeedPanel');if(p&&p.style.display!=='none')drawFullscreenSpeedGraph();}});
function closestInterpolated(P,latlng){{
  // Proietta il mouse su ogni segmento della traiettoria. Non sceglie più
  // il solo fix GPS più vicino: velocità, tempo e posizione vengono
  // interpolati continuamente tra i due fix che delimitano il segmento.
  if(!P || P.length<2)return P&&P.length?P[0]:null;
  const m=map.latLngToLayerPoint(latlng);
  let best=null,bestD=Infinity;
  for(let i=0;i<P.length-1;i++){{
    const a=map.latLngToLayerPoint([P[i][0],P[i][1]]);
    const b=map.latLngToLayerPoint([P[i+1][0],P[i+1][1]]);
    const vx=b.x-a.x,vy=b.y-a.y;
    const len2=vx*vx+vy*vy;
    let t=0;
    if(len2>0)t=((m.x-a.x)*vx+(m.y-a.y)*vy)/len2;
    t=Math.max(0,Math.min(1,t));
    const x=a.x+t*vx,y=a.y+t*vy;
    const dx=x-m.x,dy=y-m.y,d=dx*dx+dy*dy;
    if(d<bestD){{
      bestD=d;
      const p0=P[i],p1=P[i+1];
      best=[
        p0[0]+(p1[0]-p0[0])*t,
        p0[1]+(p1[1]-p0[1])*t,
        p0[2]+(p1[2]-p0[2])*t,
        p0[3]+(p1[3]-p0[3])*t
      ];
    }}
  }}
  return best;
}}
function showPoint(seriesName,pt){{
  const entry=SERIES[seriesName];if(!entry || !pt)return;
  hoverMarker.setLatLng([pt[0],pt[1]]);
  hoverMarker.setStyle({{opacity:1,fillOpacity:1,fillColor:entry.color}});
  hoverMarker.bringToFront();
  const info=document.getElementById('hoverInfo');
  if(info)info.innerHTML='<b>'+seriesName+'</b><br><b>'+pt[2].toFixed(1)+' km/h</b><br>'+ (pt[3]/1000.0).toFixed(3)+' s';
}}
function hidePoint(){{hoverMarker.setStyle({{opacity:0,fillOpacity:0}});const info=document.getElementById('hoverInfo');if(info)info.innerHTML='Mouse sulla traiettoria o sul grafico';}}

Object.entries(SERIES).forEach(([name,entry])=>{{
  const P=entry.points;if(P.length<2)return;
  // Linea visibile non interattiva + hit-area trasparente molto più larga.
  // Questo rende l'hover fluido lungo tutta la traiettoria anche se il mouse
  // non è esattamente sopra i pixel della linea colorata.
  L.polyline(P.map(x=>[x[0],x[1]]),{{color:entry.color,weight:6,opacity:.90,interactive:false}}).addTo(map);
  const hit=L.polyline(P.map(x=>[x[0],x[1]]),{{color:'#ffffff',weight:28,opacity:.01,interactive:true}}).addTo(map);
  hit.bindTooltip(name,{{sticky:true}});
  hit.on('mousemove',e=>{{const pt=closestInterpolated(P,e.latlng);showPoint(name,pt);}});
  hit.on('mouseout',()=>hidePoint());
}});

// Replay simultaneo: ogni giro selezionato parte da t=0 e usa un pallino
// dello stesso colore della relativa traiettoria. Durante la frenata il
// tooltip del pallino mostra automaticamente gli stessi dati dell'analisi.
const BRAKES_BY_SERIES={{}};
BRAKES.forEach(b=>{{if(!BRAKES_BY_SERIES[b.series])BRAKES_BY_SERIES[b.series]=[];BRAKES_BY_SERIES[b.series].push(b);}});
Object.values(BRAKES_BY_SERIES).forEach(a=>a.sort((x,y)=>x.start_ms-y.start_ms));
const replayMarkers={{}};
let replayRAF=null,replayRunning=false,replayRate=1.0,replayElapsed=0,replayBase=0,replayStartPerf=0;
let replayMaxDuration=0;
Object.entries(SERIES).forEach(([name,entry])=>{{
  const P=entry.points;if(!P.length)return;
  const marker=L.circleMarker([P[0][0],P[0][1]],{{radius:9,color:'#ffffff',weight:3,fillColor:entry.color,fillOpacity:1,opacity:0,pane:'replayPane'}}).addTo(map);
  marker.bindTooltip(name,{{direction:'top',offset:[0,-8]}});
  marker.bringToFront();replayMarkers[name]=marker;
  replayMaxDuration=Math.max(replayMaxDuration,Math.max(0,P[P.length-1][3]-P[0][3]));
}});
function setBrakeTableActive(activeRows){{
  document.querySelectorAll('.brake-zone-table .bzRow.active').forEach(el=>el.classList.remove('active'));
  const rows=Array.isArray(activeRows)?activeRows:[];
  rows.forEach(x=>{{
    const b=x&&x.brake;if(!b)return;
    const el=document.querySelector('.brake-zone-table .bzRow[data-key="'+b.zone+'-'+b.lap+'"]');
    if(el)el.classList.add('active');
  }});
}}
function updateFullscreenBrakePanel(activeRows){{
  if(fullscreenMode)setBrakeTableActive(activeRows);
}}
function replayApply(ms,visible=true){{
  const activeBrakeRows=[];
  Object.entries(SERIES).forEach(([name,entry])=>{{
    const P=entry.points,m=replayMarkers[name];if(!m||!P.length)return;
    const local=Math.min(Math.max(0,ms),Math.max(0,P[P.length-1][3]-P[0][3]));
    const pt=pointByTime(P,P[0][3]+local);if(!pt)return;
    m.setLatLng([pt[0],pt[1]]);m.setStyle({{opacity:visible?1:0,fillOpacity:visible?1:0,fillColor:entry.color}});
    const absMs=P[0][3]+local;
    const brakes=BRAKES_BY_SERIES[name]||[];
    const active=brakes.find(b=>absMs>=Number(b.start_ms)-700 && absMs<=Number(b.end_ms)+1600);
    if(active&&(!fullscreenMode||fullscreenAnalysesVisible())){{
      activeBrakeRows.push({{series:name,color:entry.color,brake:active}});
      m.setRadius(12);m.setTooltipContent(brakeHtml(active));
      if(visible && !fullscreenMode)m.openTooltip();else m.closeTooltip();
    }}
    else{{m.setRadius(9);m.setTooltipContent(name+' · '+pt[2].toFixed(1)+' km/h · '+(local/1000).toFixed(3)+' s');m.closeTooltip();}}
    m.bringToFront();
  }});
  updateFullscreenBrakePanel(activeBrakeRows);
}}
function replayFrame(now){{
  if(!replayRunning)return;
  replayElapsed=replayBase+(now-replayStartPerf)*replayRate;
  if(replayElapsed>=replayMaxDuration){{replayElapsed=replayMaxDuration;replayApply(replayElapsed,true);replayRunning=false;replayRAF=null;return;}}
  replayApply(replayElapsed,true);replayRAF=requestAnimationFrame(replayFrame);
}}
window.goatsReplayStart=function(rate){{
  const r=Number(rate);if(Number.isFinite(r)&&r>0)replayRate=r;
  if(replayElapsed>=replayMaxDuration-1)replayElapsed=0;
  replayBase=replayElapsed;replayStartPerf=performance.now();replayRunning=true;
  if(replayRAF)cancelAnimationFrame(replayRAF);replayApply(replayElapsed,true);replayRAF=requestAnimationFrame(replayFrame);
}};
window.goatsReplayPause=function(){{if(replayRunning){{replayElapsed=replayBase+(performance.now()-replayStartPerf)*replayRate;}}replayRunning=false;if(replayRAF)cancelAnimationFrame(replayRAF);replayRAF=null;}};
window.goatsReplayReset=function(){{window.goatsReplayPause();replayElapsed=0;replayBase=0;replayApply(0,true);}};
window.goatsReplaySetRate=function(rate){{const r=Number(rate);if(!Number.isFinite(r)||r<=0)return;if(replayRunning){{replayElapsed=replayBase+(performance.now()-replayStartPerf)*replayRate;replayBase=replayElapsed;replayStartPerf=performance.now();}}replayRate=r;}};

// Dati stimati di frenata, calcolati dalla velocità GNSS.
function brakePointText(b){{return Math.abs(b.delta_m)<0.05?'RIF.':(b.delta_m>0?('+'+b.delta_m.toFixed(1)+' m DOPO'):(b.delta_m.toFixed(1)+' m PRIMA'));}}
function lapDeltaText(v){{const d=Number(v||0);if(Math.abs(d)<0.0005)return 'RIF.';return d>0?('+'+d.toFixed(3)+' s RIT.'):(d.toFixed(3)+' s AVANTI');}}
function brakeEffectText(v){{const d=Number(v||0);if(Math.abs(d)<0.0005)return 'RIF.';return d>0?('+'+d.toFixed(3)+' s PERSI'):(d.toFixed(3)+' s GUAD.');}}
function dvSpeedText(v){{const d=Number(v||0);if(Math.abs(d)<0.05)return 'RIF.';return (d>0?'+':'')+d.toFixed(1);}}
function brakeHtml(b){{
  const head='<b>F'+b.zone+' · CURVA / FRENATA · Giro '+b.lap+'</b><br>';
  const br='<b>Frenata:</b> '+brakePointText(b)+' · punto '+Number(b.point_m||0).toFixed(1)+' m<br><b>Δ PRIMA:</b> '+lapDeltaText(b.lap_delta)+'<br><b>Δ DOPO:</b> '+lapDeltaText(b.lap_delta_exit)+' · <b>effetto:</b> '+brakeEffectText(b.brake_effect)+'<br>V prima freno '+Number(b.v0||0).toFixed(1)+' km/h · calo -'+Number(b.drop||0).toFixed(1)+'<br>Frenata '+Number(b.duration||0).toFixed(2)+' s';
  const sp='<b>Velocità curva:</b><br>IN '+Number(b.v_entry||0).toFixed(1)+' ('+dvSpeedText(b.dv_entry)+') · MIN '+Number(b.v_corner_min||0).toFixed(1)+' ('+dvSpeedText(b.dv_min)+') · OUT '+Number(b.v_exit||0).toFixed(1)+' ('+dvSpeedText(b.dv_exit)+') km/h';
  if(BRAKE_ANALYSIS_MODE==='brake')return head+br;
  if(BRAKE_ANALYSIS_MODE==='speed')return head+sp;
  return head+br+'<br>'+sp;
}}
const BRAKES_BY_ZONE={{}};
BRAKES.forEach(b=>{{if(!BRAKES_BY_ZONE[b.zone])BRAKES_BY_ZONE[b.zone]=[];BRAKES_BY_ZONE[b.zone].push(b);}});
Object.values(BRAKES_BY_ZONE).forEach(rows=>rows.sort((a,b)=>a.lap-b.lap));
const BRAKE_ZONE_TABLES=[];
// Le tabelle dell'analisi frenata crescono insieme allo zoom della mappa.
// Zoom 18 = 100%; ogni livello aggiunge circa il 15%, con limiti per
// mantenere le tabelle leggibili senza occupare l'intero schermo.
const BRAKE_TABLE_BASE_ZOOM=18;
function brakeTableScale(){{
  const z=Number(map.getZoom());
  if(!Number.isFinite(z))return 1.0;
  return Math.max(0.85,Math.min(1.75,1.0+(z-BRAKE_TABLE_BASE_ZOOM)*0.15));
}}
function applyBrakeTableScale(){{
  const scale=brakeTableScale();
  BRAKE_ZONE_TABLES.forEach(t=>{{
    t.scale=scale;
    const el=t.marker.getElement();
    if(el)el.style.setProperty('--bz-scale',scale.toFixed(3));
  }});
  return scale;
}}
function brakeDeltaClass(v){{const n=Number(v||0);return Math.abs(n)<0.0005?'ref':(n>0?'loss':'gain');}}
function speedDeltaClass(v){{const n=Number(v||0);return Math.abs(n)<0.05?'ref':(n>0?'gain':'loss');}}
function brakeTableWidth(mode){{return mode==='both'?520:(mode==='speed'?332:292);}}
function brakeZoneTableHtml(zone,rows){{
  const ref=(rows.find(r=>Number(r.lap)===Number(r.reference_lap))||rows[0]);
  const title=BRAKE_ANALYSIS_MODE==='brake'?'FRENATA':(BRAKE_ANALYSIS_MODE==='speed'?'VELOCITÀ CURVA':'FRENATA + VELOCITÀ CURVA');
  let h='<div class="bzWrap" style="--bz-width:'+brakeTableWidth(BRAKE_ANALYSIS_MODE)+'px"><div class="bzHead"><span>CURVA/ZONA '+zone+' · F'+zone+' · '+title+'</span><span class="bzRef">rif. G'+Number(ref.reference_lap||ref.lap)+'</span></div><table><thead><tr><th style="width:39px">Giro</th>';
  if(BRAKE_ANALYSIS_MODE!=='speed')h+='<th style="width:82px">Δ PUNTO</th><th style="width:78px">Δ PRIMA</th><th style="width:92px">GUAD./PERSO</th>';
  if(BRAKE_ANALYSIS_MODE!=='brake')h+='<th>V IN</th><th>V MIN</th><th>V OUT</th>';
  h+='</tr></thead><tbody>';
  rows.forEach(b=>{{
    const dp=brakePointText(b);const ld=lapDeltaText(b.lap_delta);const ef=brakeEffectText(b.brake_effect);
    h+='<tr class="bzRow" data-key="'+b.zone+'-'+b.lap+'"><td class="bzLap"><span class="bzDot" style="background:'+b.color+'"></span>G'+b.lap+'</td>';
    if(BRAKE_ANALYSIS_MODE!=='speed')h+='<td class="bzDP ref">'+dp+'</td><td class="bzLapDelta '+brakeDeltaClass(b.lap_delta)+'">'+ld+'</td><td class="bzEffect '+brakeDeltaClass(b.brake_effect)+'">'+ef+'</td>';
    if(BRAKE_ANALYSIS_MODE!=='brake'){{
      h+='<td>'+Number(b.v_entry||0).toFixed(1)+' <span class="'+speedDeltaClass(b.dv_entry)+'">('+dvSpeedText(b.dv_entry)+')</span></td>'
       +'<td>'+Number(b.v_corner_min||0).toFixed(1)+' <span class="'+speedDeltaClass(b.dv_min)+'">('+dvSpeedText(b.dv_min)+')</span></td>'
       +'<td>'+Number(b.v_exit||0).toFixed(1)+' <span class="'+speedDeltaClass(b.dv_exit)+'">('+dvSpeedText(b.dv_exit)+')</span></td>';
    }}
    h+='</tr>';
  }});
  return h+'</tbody></table></div>';
}}
function tableRect(cx,cy,w,h,pad=0){{return {{left:cx-w/2-pad,right:cx+w/2+pad,top:cy-h/2-pad,bottom:cy+h/2+pad}};}}
function rectOverlapArea(a,b){{const w=Math.max(0,Math.min(a.right,b.right)-Math.max(a.left,b.left));const h=Math.max(0,Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top));return w*h;}}
function pointInsideRect(p,r,pad=0){{return p.x>=r.left-pad&&p.x<=r.right+pad&&p.y>=r.top-pad&&p.y<=r.bottom+pad;}}
function rebuildBrakeZoneTable(t){{
  const width=brakeTableWidth(BRAKE_ANALYSIS_MODE),height=48+t.rows.length*18;
  t.width=width;t.height=height;
  const icon=L.divIcon({{className:'brake-zone-table',html:brakeZoneTableHtml(t.zone,t.rows),iconSize:[width,height],iconAnchor:[width/2,height/2]}});
  t.marker.setIcon(icon);
}}
Object.entries(BRAKES_BY_ZONE).forEach(([zoneS,rows])=>{{
  if(!rows.length)return;const zone=Number(zoneS);
  const anchor=[rows.reduce((s,b)=>s+Number(b.lat),0)/rows.length,rows.reduce((s,b)=>s+Number(b.lon),0)/rows.length];
  const width=brakeTableWidth(BRAKE_ANALYSIS_MODE),height=48+rows.length*18;
  const icon=L.divIcon({{className:'brake-zone-table',html:brakeZoneTableHtml(zone,rows),iconSize:[width,height],iconAnchor:[width/2,height/2]}});
  const marker=L.marker(anchor,{{icon:icon,interactive:false,pane:'brakeTablePane'}});
  const connector=L.polyline([anchor,anchor],{{color:'#ffffff',weight:1.4,opacity:.55,dashArray:'4 4',interactive:false,pane:'brakeConnectorPane'}});
  BRAKE_ZONE_TABLES.push({{zone:zone,rows:rows,anchor:L.latLng(anchor[0],anchor[1]),marker:marker,connector:connector,width:width,height:height}});
}});
window.goatsSetBrakeAnalysisMode=function(mode){{
  if(!['brake','speed','both'].includes(mode))mode='both';
  BRAKE_ANALYSIS_MODE=mode;
  document.querySelectorAll('#brakeModeControl button').forEach(b=>b.classList.toggle('active',b.dataset.mode===mode));
  BRAKE_ZONE_TABLES.forEach(rebuildBrakeZoneTable);
  applyBrakeTableScale();
  if(fullscreenMode)setTimeout(layoutBrakeZoneTables,20);
}};
const brakeModeControl=document.getElementById('brakeModeControl');
if(brakeModeControl){{
  brakeModeControl.style.display=SHOW_BRAKES?'flex':'none';
  brakeModeControl.querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>window.goatsSetBrakeAnalysisMode(b.dataset.mode)));
  brakeModeControl.querySelectorAll('button').forEach(b=>b.classList.toggle('active',b.dataset.mode===BRAKE_ANALYSIS_MODE));
}}
function setBrakeZoneTablesVisible(on){{
  BRAKE_ZONE_TABLES.forEach(t=>{{
    if(on){{if(!map.hasLayer(t.connector))t.connector.addTo(map);if(!map.hasLayer(t.marker))t.marker.addTo(map);}}
    else{{if(map.hasLayer(t.connector))map.removeLayer(t.connector);if(map.hasLayer(t.marker))map.removeLayer(t.marker);}}
  }});
  if(on){{
    applyBrakeTableScale();
    setTimeout(()=>{{applyBrakeTableScale();layoutBrakeZoneTables();}},30);
  }}
}}
function layoutBrakeZoneTables(){{
  if(!fullscreenMode||!fullscreenAnalysesVisible()||!BRAKE_ZONE_TABLES.length)return;
  const tableScale=applyBrakeTableScale();
  const sz=map.getSize(),usableBottom=Math.max(100,sz.y-(fullscreenSpeedGraph?226:8)),center=map.latLngToContainerPoint(map.getCenter());
  const trackPts=[];
  Object.values(SERIES).forEach(entry=>{{const P=entry.points||[];const step=Math.max(1,Math.floor(P.length/320));for(let i=0;i<P.length;i+=step)trackPts.push(map.latLngToContainerPoint([P[i][0],P[i][1]]));}});
  const obstacles=[{{left:Math.max(0,sz.x-255),top:0,right:sz.x,bottom:105}}];
  const placed=[];
  const ordered=BRAKE_ZONE_TABLES.slice().sort((a,b)=>a.zone-b.zone);
  ordered.forEach(t=>{{
    const ap=map.latLngToContainerPoint(t.anchor);let base=Math.atan2(ap.y-center.y,ap.x-center.x);if(!Number.isFinite(base))base=0;
    const angles=[base,base+Math.PI/4,base-Math.PI/4,base+Math.PI/2,base-Math.PI/2,base+3*Math.PI/4,base-3*Math.PI/4,base+Math.PI];
    const tw=t.width*tableScale,th=t.height*tableScale;
    const distances=[118,158,198,238].map(d=>d*Math.max(1,tableScale));let best=null,bestScore=Infinity;
    for(const d of distances){{for(const ang of angles){{
      const cx=ap.x+Math.cos(ang)*d,cy=ap.y+Math.sin(ang)*d;const r=tableRect(cx,cy,tw,th,4*tableScale);let score=d*0.15;
      if(r.left<8)score+=(8-r.left)*800;if(r.right>sz.x-8)score+=(r.right-(sz.x-8))*800;
      if(r.top<8)score+=(8-r.top)*800;if(r.bottom>usableBottom-6)score+=(r.bottom-(usableBottom-6))*800;
      placed.forEach(q=>{{score+=rectOverlapArea(r,q)*55;}});obstacles.forEach(q=>{{score+=rectOverlapArea(r,q)*25;}});
      let hits=0;for(const p of trackPts){{if(pointInsideRect(p,r,11)){{hits++;if(hits>8)break;}}}}score+=hits*9000;
      if(pointInsideRect(ap,r,18))score+=50000;
      if(score<bestScore){{bestScore=score;best={{cx,cy,r}};}}
    }}}}
    if(!best){{const fallbackD=120*Math.max(1,tableScale);best={{cx:ap.x+fallbackD,cy:ap.y,r:tableRect(ap.x+fallbackD,ap.y,tw,th,4*tableScale)}};}}
    placed.push(best.r);const pos=map.containerPointToLatLng([best.cx,best.cy]);t.marker.setLatLng(pos);t.connector.setLatLngs([t.anchor,pos]);
  }});
}}
let brakeZoomRAF=null;
map.on('zoom',()=>{{
  if(!fullscreenMode)return;
  if(brakeZoomRAF)cancelAnimationFrame(brakeZoomRAF);
  brakeZoomRAF=requestAnimationFrame(()=>{{brakeZoomRAF=null;applyBrakeTableScale();}});
}});
map.on('zoomend moveend resize',()=>{{if(fullscreenMode)setTimeout(layoutBrakeZoneTables,20);}});

// Punti di inizio frenata: restano piccoli e senza testi sovrapposti.
BRAKES.forEach(b=>{{
  if(!Number.isFinite(b.lat)||!Number.isFinite(b.lon))return;
  const m=L.circleMarker([b.lat,b.lon],{{radius:7,color:'#ffffff',weight:2,fillColor:b.color,fillOpacity:.95}});
  m.bindTooltip(()=>brakeHtml(b),{{sticky:true}});brakeMarkers.push(m);
  if(SHOW_BRAKES)m.addTo(map);
}});

const sectorColors=['#00e5ff','#ff4fd8','#ff9f43','#b8ff3d','#7c4dff','#ffee58','#40c4ff','#ff5252','#69f0ae','#e040fb','#ffab40','#64ffda'];
if(STARTLINE){{
  const a=[Number(STARTLINE.lat1),Number(STARTLINE.lon1)],b=[Number(STARTLINE.lat2),Number(STARTLINE.lon2)];
  if(Number.isFinite(a[0])&&Number.isFinite(a[1])&&Number.isFinite(b[0])&&Number.isFinite(b[1])){{
    let finishText='START / FINISH';
    if(ACTIVE_LAP!==null && SECTOR_TIMES.length>SECTORS.length){{
      finishText+=' — S'+SECTOR_TIMES.length+' '+SECTOR_TIMES[SECTORS.length];
    }}
    L.polyline([a,b],{{color:'#ff3030',weight:6,opacity:1}}).addTo(map).bindTooltip(finishText);
    if(ACTIVE_LAP!==null && SECTOR_TIMES.length>SECTORS.length){{
      const mid=[(a[0]+b[0])/2,(a[1]+b[1])/2];
      L.marker(mid,{{interactive:false,icon:L.divIcon({{className:'finish-label',html:'<div>FINISH · S'+SECTOR_TIMES.length+'<br>'+SECTOR_TIMES[SECTORS.length]+'</div>',iconSize:[110,42],iconAnchor:[55,21]}})}}).addTo(map);
    }}
  }}
}}
SECTORS.forEach((sector,index)=>{{
  const a=[Number(sector.lat1),Number(sector.lon1)],b=[Number(sector.lat2),Number(sector.lon2)];
  if(!Number.isFinite(a[0])||!Number.isFinite(a[1])||!Number.isFinite(b[0])||!Number.isFinite(b[1]))return;
  const color=sectorColors[index%sectorColors.length];
  const timing=(ACTIVE_LAP!==null && index<SECTOR_TIMES.length)?SECTOR_TIMES[index]:'';
  const tip='S'+(index+1)+' — fine settore'+(timing?' · '+timing:'');
  L.polyline([a,b],{{color:color,weight:6,opacity:1,dashArray:'9 4'}}).addTo(map).bindTooltip(tip);
  const mid=[(a[0]+b[0])/2,(a[1]+b[1])/2];
  const html='<div style="background:'+color+'"><b>S'+(index+1)+'</b>'+(timing?'<br>'+timing:'')+'</div>';
  L.marker(mid,{{interactive:false,icon:L.divIcon({{className:'sector-label',html:html,iconSize:[86,40],iconAnchor:[43,20]}})}}).addTo(map);
}});

window.goatsShowHover=function(seriesName,seconds){{const entry=SERIES[seriesName];if(!entry)return;const pt=pointByTime(entry.points,seconds*1000.0);showPoint(seriesName,pt);}};
window.goatsHideHover=function(){{hidePoint();}};

let all=[];Object.values(SERIES).forEach(e=>all=all.concat(e.points));
if(all.length)map.fitBounds(all.map(x=>[x[0],x[1]]),{{padding:[25,25]}});
setTimeout(()=>{{map.invalidateSize();if(fullscreenMode)layoutBrakeZoneTables();}},120);
</script></body></html>"""

        self._last_map_html=html
        self._map_ready=False
        self.map.setHtml(html,QUrl('https://localhost/'))

    def _analysis_open_fullscreen_map(self):
        if not self._last_map_html:
            QMessageBox.information(self,'Mappa','Seleziona prima una sessione/giro da visualizzare.')
            return
        dlg=QDialog(self)
        dlg.setWindowTitle('GOATS RT - Mappa a schermo intero')
        lay=QVBoxLayout(dlg)
        lay.setContentsMargins(0,0,0,0)
        lay.setSpacing(0)

        # Controlli sempre accessibili mentre la mappa e' a schermo intero.
        # In questo modo il replay si pilota senza tornare alla pagina Analisi.
        control_bar=QWidget(dlg)
        controls=QHBoxLayout(control_bar);controls.setContentsMargins(10,7,10,7);controls.setSpacing(8)
        play=QPushButton('▶ PLAY');play.setCheckable(True);play.setMinimumHeight(40);play.setMinimumWidth(120)
        speed=QComboBox();speed.addItem('0,5x',0.5);speed.addItem('1x',1.0);speed.setMinimumHeight(40);speed.setMinimumWidth(90)
        # Riprende la velocita' selezionata nella pagina Analisi.
        try:
            current_rate=float(self.replay_speed_combo.currentData() or 1.0)
            idx=speed.findData(current_rate)
            speed.setCurrentIndex(idx if idx>=0 else 1)
        except Exception:
            speed.setCurrentIndex(1)
        reset=QPushButton('↺ RESET');reset.setMinimumHeight(40)
        hint=QLabel('PROMEMORIA:  SPAZIO = Play/Pausa   S = 0,5x/1x   R = Reset   ESC = Esci')
        hint.setAlignment(Qt.AlignVCenter|Qt.AlignRight)
        hint.setWordWrap(True)
        hint.setStyleSheet('font-weight:600; padding:0 8px;')
        close_btn=QPushButton('CHIUDI (ESC)');close_btn.setMinimumHeight(40)
        controls.addWidget(play);controls.addWidget(QLabel('Velocità'));controls.addWidget(speed);controls.addWidget(reset);controls.addWidget(hint,1);controls.addWidget(close_btn)
        lay.addWidget(control_bar,0)

        visibility_bar=QWidget(dlg)
        visibility_controls=QHBoxLayout(visibility_bar)
        visibility_controls.setContentsMargins(10,4,10,7);visibility_controls.setSpacing(18)
        visibility_controls.addWidget(QLabel('MOSTRA:'))
        braking_check=QCheckBox('Analisi frenata');braking_check.setObjectName('fullscreenBrakingCheck')
        corner_speed_check=QCheckBox('Velocità in curva');corner_speed_check.setObjectName('fullscreenCornerSpeedCheck')
        graph_check=QCheckBox('Grafico velocità');graph_check.setObjectName('fullscreenSpeedGraphCheck')
        visibility=getattr(self,'_fullscreen_overlay_visibility',None)
        if visibility is None:
            mode=getattr(self,'_analysis_brake_table_mode','both')
            visibility=(mode!='speed',mode!='brake',True)
        for check,checked in zip((braking_check,corner_speed_check,graph_check),visibility):
            check.setChecked(checked);visibility_controls.addWidget(check)
        visibility_controls.addStretch()
        lay.addWidget(visibility_bar,0)

        view=QWebEngineView(dlg)
        def apply_fullscreen_mode():
            rate=float(speed.currentData() or 1.0)
            visibility=(braking_check.isChecked(),corner_speed_check.isChecked(),graph_check.isChecked())
            self._fullscreen_overlay_visibility=visibility
            flags=','.join(json.dumps(flag) for flag in visibility)
            js=("window.goatsSetFullscreenMode && window.goatsSetFullscreenMode(true);"
                f"window.goatsSetFullscreenOverlays && window.goatsSetFullscreenOverlays({flags});"
                f"window.goatsReplaySetRate && window.goatsReplaySetRate({rate:.3f});")
            view.page().runJavaScript(js)
        for check in (braking_check,corner_speed_check,graph_check):
            check.toggled.connect(lambda _checked: apply_fullscreen_mode())
        def fullscreen_loaded(ok):
            # setHtml può segnalare False se una risorsa web esterna tarda/fallisce,
            # anche se il JS locale è già utilizzabile. Applichiamo comunque la modalità.
            apply_fullscreen_mode()
            QTimer.singleShot(250,apply_fullscreen_mode)
            QTimer.singleShot(800,apply_fullscreen_mode)
        view.loadFinished.connect(fullscreen_loaded)
        view.setHtml(self._last_map_html,QUrl('https://localhost/'))
        # Fallback indipendente da loadFinished: evita fullscreen senza HUD/etichette.
        QTimer.singleShot(1200,apply_fullscreen_mode)
        lay.addWidget(view,1)

        def toggle(on):
            play.setText('⏸ PAUSA' if on else '▶ PLAY')
            rate=float(speed.currentData() or 1.0)
            view.page().runJavaScript(
                f"window.goatsReplayStart && window.goatsReplayStart({rate:.3f});" if on
                else "window.goatsReplayPause && window.goatsReplayPause();"
            )
        play.toggled.connect(toggle)
        speed.currentIndexChanged.connect(lambda *_: view.page().runJavaScript(
            f"window.goatsReplaySetRate && window.goatsReplaySetRate({float(speed.currentData() or 1.0):.3f});"
        ))
        def do_reset():
            play.blockSignals(True);play.setChecked(False);play.setText('▶ PLAY');play.blockSignals(False)
            view.page().runJavaScript("window.goatsReplayReset && window.goatsReplayReset();")
        def close_fullscreen():
            view.page().runJavaScript("window.goatsReplayPause && window.goatsReplayPause();")
            dlg.accept()
        reset.clicked.connect(do_reset);close_btn.clicked.connect(close_fullscreen)

        # Comandi tastiera espliciti: ESC chiude sempre, anche con focus sulla mappa;
        # SPAZIO permette di pilotare rapidamente Play/Pausa.
        esc_shortcut=QShortcut(QKeySequence(Qt.Key_Escape),dlg)
        esc_shortcut.activated.connect(close_fullscreen)
        space_shortcut=QShortcut(QKeySequence(Qt.Key_Space),dlg)
        space_shortcut.activated.connect(lambda: play.setChecked(not play.isChecked()))
        reset_shortcut=QShortcut(QKeySequence('R'),dlg)
        reset_shortcut.activated.connect(do_reset)
        speed_shortcut=QShortcut(QKeySequence('S'),dlg)
        def toggle_speed_shortcut():
            speed.setCurrentIndex(0 if speed.currentIndex()==1 else 1)
        speed_shortcut.activated.connect(toggle_speed_shortcut)
        # Conserviamo i riferimenti per tutta la vita della finestra.
        dlg._goats_shortcuts=(esc_shortcut,space_shortcut,reset_shortcut,speed_shortcut)

        # Ricorda le scelte anche se la finestra viene chiusa prima del caricamento web.
        self._fullscreen_overlay_visibility=tuple(check.isChecked() for check in (braking_check,corner_speed_check,graph_check))
        dlg.showFullScreen()
        dlg.exec()

    def _analysis_map_loaded(self,ok):
        self._map_ready=bool(ok)
        if self._map_ready and self._pending_map_hover is not None:
            name,sec=self._pending_map_hover
            self._pending_map_hover=None
            self.map.page().runJavaScript(
                "window.goatsShowHover && "
                f"window.goatsShowHover({json.dumps(name)},{float(sec):.6f});"
            )

    @staticmethod
    def _nearest_row_by_time(rows, sec):
        if not rows:
            return None
        target=float(sec)*1000.0
        return min(rows,key=lambda r:abs(float(r['elapsed_ms'])-target))

    def _remove_analysis_cursor_items(self):
        try:
            view=self._analysis_cursor_chart_view
            chart=view.chart() if view is not None else None
            scene=chart.scene() if chart else None
            if scene is not None:
                if self._analysis_cursor_line is not None:
                    scene.removeItem(self._analysis_cursor_line)
                if self._analysis_cursor_dot is not None:
                    scene.removeItem(self._analysis_cursor_dot)
        except Exception:
            pass
        self._analysis_cursor_line=None
        self._analysis_cursor_dot=None
        self._analysis_cursor_chart_view=None

    def _analysis_cursor_moved_single(self,view,name,rows,series,sec,mouse_y):
        try:
            chart=view.chart()
            if chart is None or not rows or series is None:
                return
            row=self._nearest_row_by_time(rows,sec)
            if row is None:
                return
            point=QPointF(float(row['elapsed_ms'])/1000.0,float(row['speed_kmh']))
            pos=chart.mapToPosition(point,series)
            if abs(float(pos.y())-float(mouse_y))>85.0:
                self._analysis_cursor_left()
                return

            actual_sec=float(row['elapsed_ms'])/1000.0
            if self._map_ready:
                self.map.page().runJavaScript(
                    "window.goatsShowHover && "
                    f"window.goatsShowHover({json.dumps(name)},{actual_sec:.6f});"
                )
            else:
                self._pending_map_hover=(name,actual_sec)

            self._remove_analysis_cursor_items()
            plot=chart.plotArea(); scene=chart.scene()
            line=QGraphicsLineItem(float(pos.x()),float(plot.top()),float(pos.x()),float(plot.bottom()))
            pen=line.pen(); pen.setWidth(4); pen.setColor(Qt.white); line.setPen(pen)
            line.setZValue(2000); scene.addItem(line)
            self._analysis_cursor_line=line

            radius=7.0
            dot=QGraphicsEllipseItem(float(pos.x()-radius),float(pos.y()-radius),radius*2.0,radius*2.0)
            dpen=dot.pen(); dpen.setWidth(3); dpen.setColor(Qt.white); dot.setPen(dpen)
            dot.setBrush(Qt.black); dot.setZValue(2001); scene.addItem(dot)
            self._analysis_cursor_dot=dot
            self._analysis_cursor_chart_view=view
        except Exception:
            pass

    def _analysis_cursor_left(self):
        self._pending_map_hover=None
        self._remove_analysis_cursor_items()
        try:
            self.map.page().runJavaScript(
                "window.goatsHideHover && window.goatsHideHover();"
            )
        except Exception:
            pass

    def _clear_analysis_charts(self):
        self._remove_analysis_cursor_items()
        self._analysis_chart_views=[]
        self._analysis_chart_views_by_lap={}
        if not hasattr(self,'chart_layout'):
            return
        while self.chart_layout.count():
            item=self.chart_layout.takeAt(0)
            widget=item.widget()
            if widget is not None:
                widget.deleteLater()

    def render_chart(self,series):
        self._clear_analysis_charts()
        self._analysis_hover_series=[]
        self._analysis_hover_rows={}
        self._analysis_hover_series_by_name={}

        populated=[(name,rows) for name,rows in series.items() if rows]
        if not populated:
            label=QLabel('Seleziona uno o più giri per visualizzare i grafici velocità.')
            label.setAlignment(Qt.AlignCenter)
            label.setObjectName('muted')
            label.setMinimumHeight(120)
            self.chart_layout.addWidget(label)
            self.chart_layout.addStretch()
            return

        # Stessa scala Y per tutti i giri: i grafici sono separati ma restano
        # immediatamente confrontabili visivamente.
        all_rows=[r for _,rows in populated for r in rows]
        speeds=[float(r['speed_kmh']) for r in all_rows]
        global_ymin=min(speeds); global_ymax=max(speeds)
        global_pad=max(3.0,(global_ymax-global_ymin)*0.08)
        y0=max(0.0,global_ymin-global_pad); y1=global_ymax+global_pad

        for idx,(name,rows) in enumerate(populated):
            chart=QChart()
            chart.setTitle(f'{name} — velocità')
            chart.legend().setVisible(False)

            s=QLineSeries(); s.setName(name)
            pen=s.pen(); pen.setWidth(3); pen.setColor(QColor(self._analysis_color_for_series(name,idx))); s.setPen(pen)
            step=max(1,len(rows)//4500)
            for r in rows[::step]:
                s.append(float(r['elapsed_ms'])/1000.0,float(r['speed_kmh']))
            chart.addSeries(s)

            ax=QValueAxis(); ax.setTitleText('Tempo giro [s]')
            ay=QValueAxis(); ay.setTitleText('Velocità [km/h]')
            chart.addAxis(ax,Qt.AlignBottom); chart.addAxis(ay,Qt.AlignLeft)
            s.attachAxis(ax); s.attachAxis(ay)
            xmax=max(float(r['elapsed_ms']) for r in rows)/1000.0
            ax.setRange(0.0,max(1.0,xmax)); ay.setRange(y0,y1)

            view=AnalysisChartView()
            view.setRenderHint(QPainter.Antialiasing)
            view.setChart(chart)
            view.setMinimumHeight(235)
            view.setMaximumHeight(300)
            view.cursorMoved.connect(
                lambda sec,mouse_y,v=view,n=name,rr=list(rows),ss=s:
                    self._analysis_cursor_moved_single(v,n,rr,ss,sec,mouse_y)
            )
            view.cursorLeft.connect(self._analysis_cursor_left)
            self._analysis_chart_views.append(view)
            m=re.search(r'(\d+)',str(name))
            if m:
                self._analysis_chart_views_by_lap[int(m.group(1))]=view
            self._analysis_hover_series.append(s)
            self._analysis_hover_rows[name]=list(rows)
            self._analysis_hover_series_by_name[name]=s
            self.chart_layout.addWidget(view)

        self.chart_layout.addStretch()

    def export_current(self):
        sid=self.current_session_id
        if not sid:return
        folder=QFileDialog.getExistingDirectory(self,'Cartella esportazione')
        if not folder:return
        s=self.store.session(sid);pts=self.store.points(sid);stem=f"GOATS_{sid}_{s['date'].replace('/','-')}_{s['track_name'].replace(' ','_')}".replace('\\','_').replace('/','_');d=Path(folder);export_json(s,pts,d/(stem+'.json'));export_csv(s,pts,d/(stem+'.csv'));export_gpx(s,pts,d/(stem+'.gpx'));QMessageBox.information(self,'Esportazione','Creati JSON, CSV e GPX.')
    def _style(self):
        self.setStyleSheet('''QMainWindow,QWidget{background:#0b0f14;color:#eef3f8;font-family:"Segoe UI";font-size:10pt}#sidebar{background:#111820;border-right:1px solid #26313d}#appName{font-size:22pt;font-weight:800}#appVersion{color:#00d084;font-weight:700;letter-spacing:2px}#sideStatus{color:#8d9aaa;background:#0d131a;border:1px solid #25313d;border-radius:8px;padding:9px}NavButton{border:0;text-align:left;padding-left:15px;border-radius:8px;background:transparent;color:#aeb9c6;font-weight:600}NavButton:hover{background:#1b2530;color:white}NavButton:checked{background:#00a96b;color:white}#pageTitle{font-size:25pt;font-weight:800}#pageSub,#muted{color:#9aa8b7}#card,#metric{background:#151c24;border:1px solid #26323e;border-radius:12px;padding:10px}#cardTitle{font-size:15pt;font-weight:700}#metricValue{font-size:20pt;font-weight:800;color:#00d084}QPushButton{background:#202a35;border:1px solid #34404d;border-radius:7px;padding:8px 12px;color:white}QPushButton:hover,#primary{background:#00a96b}QLineEdit,QComboBox,QTableWidget{background:#111820;border:1px solid #2b3744;border-radius:6px;padding:5px}QHeaderView::section{background:#18212b;color:#dfe7ef;padding:7px;border:0}''')

def main():
    app=QApplication(sys.argv);app.setApplicationName('GOATS RT Manager V5')
    if LOGO.exists():app.setWindowIcon(QIcon(str(LOGO)))
    w=Main();w.show();return app.exec()
if __name__=='__main__':sys.exit(main())
