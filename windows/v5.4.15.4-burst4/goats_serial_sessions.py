"""TEST23 GSD serial microSD transport, embedded PySide6 panel."""
from pathlib import Path
from pathlib import PurePosixPath
from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,
 QComboBox,QTableWidget,QTableWidgetItem,QHeaderView,QFileDialog,QProgressBar,QMessageBox,QAbstractItemView,QSizePolicy)

def local_relative_path(remote_name):
    """Map the SD's ROOT: display prefix to a safe local relative path.

    Keep remote_name unchanged for GSD_GET/GSD_DELETE: it is the identifier
    returned by GSD_LIST and may be required verbatim by the firmware.
    """
    name = remote_name.replace('\\', '/')
    if name.upper().startswith('ROOT:'):
        name = name[5:]
    # Some firmware variants use a leading slash for SD root.
    if name.startswith('/'):
        name = name[1:]
    relative = PurePosixPath(name)
    if (not name or name.endswith('/') or ':' in name or
            any(part in ('', '.', '..') for part in name.split('/')) or
            relative.is_absolute() or '\x00' in name):
        raise RuntimeError('Percorso remoto non valido: ' + remote_name)
    return Path(*relative.parts)


class TransferWorker(QObject):
    status=Signal(str)
    listing=Signal(object)
    progress=Signal(int)
    finished=Signal(str)
    failed=Signal(str)
    def __init__(self,port,mode,selection,directory):
        super().__init__();self.port=port;self.mode=mode;self.selection=selection;self.directory=directory
    def run(self):
        try:
            from goats_test23_protocol import connect_port,fetch_list,fetch_file,delete_file
            with connect_port(self.port,lambda msg:self.status.emit(msg)) as p:
                files=fetch_list(p)
                if self.mode=='list':
                    self.listing.emit(files)
                    self.finished.emit(f'{len(files)} file trovati sulla microSD')
                    return
                wanted=[(name,size) for name,size in files if name in self.selection]
                if not wanted:raise RuntimeError('Nessun file selezionato trovato sulla microSD')
                if self.mode=='delete':
                    for index,(name,size) in enumerate(wanted):
                        self.status.emit('Eliminazione: '+name)
                        delete_file(p,name)
                        self.progress.emit(int(100*(index+1)/len(wanted)))
                    self.listing.emit(fetch_list(p))
                    self.finished.emit(f'Eliminate {len(wanted)} sessioni dalla microSD')
                    return
                base=Path(self.directory).expanduser();base.mkdir(parents=True,exist_ok=True)
                total=sum(size for _,size in wanted);completed=0
                for name,size in wanted:
                    # Do not permit traversal outside chosen directory.
                    relative=local_relative_path(name)
                    target=base/relative;target.parent.mkdir(parents=True,exist_ok=True)
                    self.status.emit('Scaricamento: '+name)
                    fetch_file(p,name,target,lambda n,received,sz:self.progress.emit(int(100*(completed+received)/max(total,1))))
                    completed+=size
                    self.progress.emit(int(100*completed/max(total,1)))
                self.finished.emit(f'Scaricati {len(wanted)} file in {base}. Usa SCANSIONA CARTELLA per importarli nel database.')
        except Exception as exc:self.failed.emit(str(exc))

class SerialSessionsPanel(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.files=[];self.thread=None;self.worker=None
        self.setStyleSheet('''
            SerialSessionsPanel QLabel { color: #f1f5f9; background: transparent; }
            SerialSessionsPanel QPushButton { color: #ffffff; background-color: #263746;
                border: 1px solid #60758a; border-radius: 5px; padding: 7px 11px;
                min-height: 23px; font-weight: 600; }
            SerialSessionsPanel QPushButton:hover { background-color: #36536a; }
            SerialSessionsPanel QPushButton:disabled { color: #aebbc8; background-color: #25303b; }
            SerialSessionsPanel QComboBox { color: #ffffff; background-color: #253746;
                border: 1px solid #60758a; padding: 5px; min-height: 23px; }
            SerialSessionsPanel QComboBox QAbstractItemView { color: #ffffff; background-color: #253746; }
            SerialSessionsPanel QTableWidget { color: #f8fafc; background-color: #14212d;
                gridline-color: #445567; selection-background-color: #156c86; }
            SerialSessionsPanel QHeaderView::section { color: #ffffff; background-color: #263746;
                padding: 6px; border: 1px solid #445567; }
            SerialSessionsPanel QProgressBar { color: #ffffff; background-color: #253746;
                border: 1px solid #60758a; text-align: center; }
            SerialSessionsPanel QProgressBar::chunk { background-color: #00a878; }
        ''')
        self.setMinimumHeight(415)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        lay=QVBoxLayout(self)
        lay.setContentsMargins(12,12,12,12)
        lay.setSpacing(10)
        lay.addWidget(QLabel('MICROSD VIA USB SERIALE — TEST23 (nessun USB Mass Storage)'))
        row=QHBoxLayout();self.port=QComboBox();row.addWidget(QLabel('Porta COM'));row.addWidget(self.port,1)
        refresh=QPushButton('AGGIORNA PORTE');refresh.clicked.connect(self.refresh_ports);row.addWidget(refresh)
        read=QPushButton('LEGGI MICROSD');read.clicked.connect(lambda:self.start('list'));row.addWidget(read);lay.addLayout(row)
        self.table=QTableWidget(0,2);self.table.setHorizontalHeaderLabels(['File microSD','Dimensione (byte)']);self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch)
        self.table.setMinimumHeight(170);self.table.setSelectionBehavior(QTableWidget.SelectRows);self.table.setSelectionMode(QAbstractItemView.ExtendedSelection);lay.addWidget(self.table,1)
        row=QHBoxLayout();self.directory=QLabel(str(Path.home()/'Documents'/'GOATS_RT'/'Sessioni'));row.addWidget(self.directory,1)
        choose=QPushButton('CARTELLA DESTINAZIONE');choose.clicked.connect(self.choose_dir);row.addWidget(choose);lay.addLayout(row)
        row=QHBoxLayout();selected=QPushButton('SCARICA SELEZIONATI');selected.clicked.connect(lambda:self.start('selected'));row.addWidget(selected)
        allfiles=QPushButton('SCARICA TUTTI');allfiles.clicked.connect(lambda:self.start('all'));row.addWidget(allfiles);lay.addLayout(row)
        row=QHBoxLayout()
        selectall=QPushButton('SELEZIONA TUTTE');selectall.clicked.connect(self.table.selectAll);row.addWidget(selectall)
        clear=QPushButton('DESELEZIONA');clear.clicked.connect(self.table.clearSelection);row.addWidget(clear)
        delete=QPushButton('ELIMINA SELEZIONATE');delete.clicked.connect(lambda:self.start('delete'));row.addWidget(delete)
        lay.addLayout(row)
        self.progress=QProgressBar();self.progress.setMinimumHeight(22);lay.addWidget(self.progress)
        self.status=QLabel('Collega RLCD TEST23 via USB, termina la sessione e seleziona la porta.');self.status.setWordWrap(True);lay.addWidget(self.status)
        self.controls=[refresh,read,choose,selected,allfiles,selectall,clear,delete];self.refresh_ports()
    def refresh_ports(self):
        self.port.clear()
        try:
            from serial.tools import list_ports
            for p in list_ports.comports():self.port.addItem(f'{p.device} — {p.description}',p.device)
        except ImportError:self.status.setText('Dipendenza mancante: pip install pyserial')
    def choose_dir(self):
        folder=QFileDialog.getExistingDirectory(self,'Destinazione sessioni',self.directory.text())
        if folder:self.directory.setText(folder)
    def start(self,mode):
        if self.thread is not None:return
        port=self.port.currentData()
        if not port:QMessageBox.warning(self,'GOATS','Seleziona una porta COM');return
        selection=set()
        if mode=='all':selection={name for name,_ in self.files}
        elif mode in ('selected','delete'):selection={self.files[i][0] for i in {idx.row() for idx in self.table.selectedIndexes()}}
        if mode!='list' and not selection:QMessageBox.warning(self,'GOATS','Leggi la microSD e seleziona almeno un file');return
        if mode=='delete':
            if QMessageBox.question(self,'Conferma eliminazione',
                f'Eliminare definitivamente {len(selection)} sessioni dalla microSD del laptimer?\n'
                'Questa operazione non è reversibile. Non saranno eliminati i file sul PC.',
                QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
        self.progress.setValue(0)
        for b in self.controls:b.setEnabled(False)
        self.thread=QThread(self);self.worker=TransferWorker(port,mode,selection,self.directory.text());self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.listing.connect(self.set_files)
        self.worker.status.connect(self.status.setText)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.finished.connect(self.complete)
        self.worker.failed.connect(self.error)
        self.worker.finished.connect(self.thread.quit);self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.cleanup)
        self.thread.start()
    def set_files(self,files):
        self.files=files;self.table.setRowCount(len(files))
        for row,(name,size) in enumerate(files):
            self.table.setItem(row,0,QTableWidgetItem(name));self.table.setItem(row,1,QTableWidgetItem(str(size)))
    def complete(self,message):self.status.setText(message)
    def error(self,message):
        self.status.setText('Errore: '+message);QMessageBox.warning(self,'Trasferimento microSD',message)
    def cleanup(self):
        self.worker.deleteLater();self.thread.deleteLater();self.worker=None;self.thread=None
        for b in self.controls:b.setEnabled(True)
