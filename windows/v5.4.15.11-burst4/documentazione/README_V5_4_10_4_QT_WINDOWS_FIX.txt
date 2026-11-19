GOATS RT Manager V5.4.10.4 - QT WINDOWS FIX

Problema corretto:
  qt.qpa.plugin: Could not load the Qt platform plugin "windows"
  even though it was found.

La schermata mostrava Python 3.14 + PySide6 6.11.2 correttamente installati,
quindi non era un ModuleNotFoundError: qwindows.dll veniva trovato ma il
loader Windows non risolveva correttamente il runtime Qt.

Fix:
- elimina QT_PLUGIN_PATH / QML2_IMPORT_PATH ereditati da altre applicazioni;
- imposta QT_QPA_PLATFORM_PLUGIN_PATH sul plugin della .goats_venv;
- mette la cartella PySide6 per prima nel PATH dei DLL;
- usa os.add_dll_directory() prima degli import Qt;
- esegue un test reale QApplication prima di avviare il Manager;
- se il test fallisce, reinstalla automaticamente PySide6 senza cache e
  ripete il test;
- aggiunto DIAGNOSTICA_QT_WINDOWS.bat con QT_DEBUG_PLUGINS=1.

Versione applicazione invariata: V5.4.10.4.
Le modifiche Sessioni USB / GSDT_WAIT REMOUNT restano presenti.
