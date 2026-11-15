# Migrazione GOATS Mobile / Windows — verifica del 15 novembre 2026

## Stato della consegna

Importazione pubblicata sul ramo `codex/mobile-windows-handoff`, base
`76c40855a9c3030c0ce53aaa4436c90bd4941a8f` di `ady1972/TELEMETRY`.
Modifiche esaminate dall'utente, che ha autorizzato commit e push sul ramo
di handoff e successivamente ha richiesto esplicitamente l'integrazione in
`main`. L'integrazione conserva gli aggiornamenti firmware già presenti su
`main`; le app mantengono intatti sorgenti e protocolli ricevuti. Non sono
state riscritte le applicazioni.

L'utente ha confermato che la versione allegata è già stata testata ed è
funzionante. Questa conferma è registrata come collaudo effettuato dall'utente;
la versione ricevuta costituisce la base per le successive modifiche.

Questo rapporto documenta anche l'analisi dei sorgenti e i controlli eseguiti
durante la migrazione. README, manuali e test report negli ZIP sono conservati
come documentazione del progetto. Il blocco della build CI riguarda la
disponibilità dell'SDK sul runner; la versione funzionante fornita dall'utente
è stata importata senza modifiche ai sorgenti.

## Provenienza, struttura e completezza

Su richiesta dell'utente, i progetti sono organizzati in sottocartelle per
versione: `mobile/v0.2.1/` e `windows/v5.4.15.4-burst4/`. Gli indici delle
piattaforme rimangono in `mobile/README.md` e `windows/README.md`.
La riorganizzazione sposta insieme tutti i file di ciascun pacchetto,
preservandone i contenuti e i percorsi relativi interni. Test, workflow e
documentazione della monorepository fanno riferimento alle nuove posizioni.
I 22 test di compatibilità sono stati ripetuti con esito positivo dopo lo
spostamento; tutti i 146 file originali conservano gli stessi digest SHA256.

| Progetto | Archivio | Contenuto importato |
|---|---|---|
| Android | `GOATS_RT_Manager_Android_V0_2_1_TRACK_EDITOR_WIFI_CLOUD_SYNC.zip` | 46 file in `mobile/v0.2.1/`: 8 Kotlin, 4 Python, Gradle, manifest e risorse, workflow originale e documentazione |
| Windows | `GOATS_RT_Manager_V5.4.15.4_BURST4.zip` | 100 file in `windows/v5.4.15.4-burst4/`: 17 Python, launcher e diagnostica BAT, requisiti, logo, manuali PDF/DOCX, esempi e note storiche |

SHA256 degli archivi ricevuti:

```text
861aea68687a85b342344d70a2ba6ce67ac133165dcaacf427e1a30d2760c7a6  Android ZIP
62103b5e23fb5cbc97c2cbd309cd17184e2cb0891c2b2f42426b0ba8d544f2e2  Windows ZIP
```

Tutti i 146 file importati sono identici byte per byte agli ZIP; i manifest
`mobile/v0.2.1/IMPORTED_SOURCE_SHA256SUMS.txt` e
`windows/v5.4.15.4-burst4/IMPORTED_SOURCE_SHA256SUMS.txt` ne registrano i digest.
`mobile/v0.2.1/gradlew` è stato reso eseguibile senza cambiarne il contenuto.
Tutti gli import Python locali delle applicazioni trovano il modulo corrispondente.
Le dipendenze esterne restano quelle dichiarate dai progetti.

Struttura Android: root Gradle in `mobile/v0.2.1/`, modulo `:app` mappato a `fullapp/`,
output in `mobile/v0.2.1/app/build/`. Il launcher dichiarato è `MainActivity`, che apre
la schermata diagnostica; `ManagerActivity` contiene il Manager Compose completo.
Gli script `gradlew`/`gradlew.bat` scaricano Gradle senza usare un wrapper JAR.

Struttura Windows: `AVVIA_GOATS_RT_MANAGER_V5.bat` → `goats_bootstrap.py` →
`goats_run_manager.py` → `goats_rt_manager_v5_4_13_11.py`.
Le altre cinque versioni storiche del file principale sono conservate come ricevute.

Sono aggiunti README di ingresso, manifest di importazione, esclusioni Git,
test di compatibilità e un workflow Android alla root della monorepository.
Il workflow Android originale resta intatto in `mobile/v0.2.1/.github/workflows/`;
in tale posizione GitHub non lo esegue. Quello nuovo usa la directory `mobile/v0.2.1/`
e il percorso reale dell'APK. I workflow firmware esistenti non cambiano.

## Esclusioni e dati

- Escluso dallo ZIP Windows `__pycache__/goats_test23_protocol.cpython-313.pyc`.
- La directory vuota `.gradle-dist/` dello ZIP Android non viene importata.
- Nessun ambiente virtuale, APK, build, cache Gradle, database o log generato
  dalle verifiche è incluso nelle modifiche.
- Non sono emersi token, chiavi private o credenziali incorporati nei file
  esaminati; i campi AssistNow sono vuoti e compilati dall'utente a runtime.
  Verificati anche testo e metadati dei manuali: autore DOCX `python-docx`,
  immagine incorporata del logo. Non sono importati profili Windows/Android.
- Conservati soltanto gli esempi distribuiti: circuito `esempio` con coordinate
  dimostrative e sessione `TEST` GRT8 da 50 punti/1,96 s con progressione
  artificiale di coordinate e velocità. Nessun archivio personale è allegato.
- Le regole Git escludono runtime, chiavi, database, log e archivi generati
  nelle posizioni convenzionali. I circuiti Windows creati dall'utente in
  `windows/v5.4.15.4-burst4/tracks/` sono esclusi salvo `esempio.json`.

## Funzionalità effettivamente presenti

“Presente” indica implementazione individuata nel codice, non collaudo completo.

| Funzione | Android V0.2.1 | Windows V5.4.15.4 | Evidenza nei sorgenti |
|---|---|---|---|
| Import GRT8/GSA2/GSA3/CSV/JSON | Presente, file multipli tramite selettore | Presente, file multipli e scansione cartelle | Entrambi: `goats_formats.py`; Android `ManagerActivity.kt::SessionsScreen`, `android_bridge.py::import_file`; Windows `Main.do_import/import_folder` |
| Archivio offline | SQLite e file originali separati | SQLite e sorgenti conservati nelle posizioni importate | Android `SessionArchiveCloud.kt::SessionArchive`, `android_bridge.py::init_app`; entrambi `goats_store.py` |
| Ricerca/eliminazione sessioni | Presente nella UI | Presente, anche selezione multipla | Android `SessionsScreen`; Windows `Main.sessions_page/delete_selected` |
| Note | Scrittura nel bridge e visualizzazione/ricerca UI; editor UI non individuato | Editor UI e salvataggio | `PythonBridge.kt::setSessionNotes`, `android_bridge.py::set_session_notes`; Windows `edit_selected_session_notes/save_current_session_notes` |
| Giri, traiettoria, velocità | Presente; selezione giro | Presente; analisi multi-giro | Android `AnalysisScreen`, `TrackCanvas`, `SpeedChart`, `analysis_json`; Windows `analysis_session_changed/render_analysis/render_chart` |
| Mappa | Compose nativa, tile Esri in cache, traccia offline, zoom/pan/FIT | QtWebEngine/Leaflet, mappe e cursori sincronizzati | Android `SatelliteTrackMap/loadSatelliteTile`; Windows `render_map`, `goats_track_editor.py::load_map` |
| Settori e giro potenziale | Gestione linee circuito e tempi giro; analisi settori/giro potenziale equivalente al PC non individuata | Presente | Android `TrackEditorScreen`; Windows `_analysis_sector_times_for_lap/_session_potential_lap_details` |
| Confronto sessioni | Backend riepiloghi fino a 8; UI completa assente | Presente nella UI | Android `android_bridge.py::compare_json`; Windows `compare_selected_sessions` |
| Replay/frenate | Interfaccia completa non presente | Replay, stime di decelerazione, delta e velocità curva | Android `InfoScreen` e assenza dei relativi controlli; Windows `_analysis_replay_*`, `_analysis_detect_braking_events/_analysis_build_brake_analysis` |
| Editor circuiti | Presente: traguardo/settori touch, ricerca, direzione e raggio | Presente: traguardo/settori, import/export e cataloghi | Android `TrackEditorScreen/TrackEditorMap`, `android_bridge.py::save_track_json`; Windows `TrackManager.collect_track_data/save_track/import_json/export_catalog` |
| Trasferimento circuiti USB | OTG seriale, lettura/invio e merge non distruttivo | Seriale, lettura/invio, merge, eliminazione | Android `UsbSerialManager.kt`, `TracksScreen`; Windows `TrackManager.send_to_laptimer/download_tracks_from_laptimer` |
| Sessioni dal dispositivo | Client Wi-Fi REST presente; server firmware non verificato | Pannello microSD GSD e altri percorsi storici GSES/GSDT | Android `LapTimerTransferManager.kt`, `LapTimerImportDialog`; Windows `goats_serial_sessions.py`, `goats_test23_protocol.py`, `TrackManager.download_sessions` |
| Cloud Sync | Cartella SAF, lettura/scrittura file, upload dopo import se auto attivo | Cartella locale gestita da client cloud, import/pubblicazione e timer 15 s | Android `CloudSessionSync`; Windows `Main._cloud_*` |
| Cartelle sessioni/circuiti personalizzabili | Archivio privato app; cartella cloud selezionabile | Due cartelle indipendenti, percorsi condivisi/NAS e fallback locale | Android `init_app/SessionArchive.dir`; Windows `apply_sessions_folder/apply_tracks_folder` |
| Export CSV/JSON/GPX | Modulo Python incluso; nessuna chiamata di export dalla UI individuata | Presente nella UI | Entrambi `goats_exporters.py`; Windows `export_current` |
| AssistNow | Sezione non presente | Profili multipli, ZTP, download Predictive e invio USB | Windows `goats_track_editor.py::register_assistnow_device/download_assistnow_predictive/_send_assistnow_payload` |
| Strumenti GNSS | Nessuna sezione equivalente individuata | Identificazione UBX e CFG-VALSET già presenti | Windows `gnss_page`, `goats_gnss.py` |
| Sessioni BLE | Assente | Non individuato in questo flusso | Nessuna implementazione BLE nei sorgenti Kotlin ricevuti |

## Formati e protocolli conservati

- **GRT8**: header 256 byte, versione 1, record 22/24 byte, CRC32.
- **GSA2**: versioni 1/2, tracce con tick 100 ms quando disponibili.
  **GSA3**: versione 3, tick 40 ms. JSON storico: sessioni con `laps[].trace[]`.
- **CSV SD**: delimitatore `,` o `;`, metadati iniziali `# key=value`, date
  conservate/normalizzate, coordinate e diagnostica iTOW/nav_seq/frequenze/crossing.
  Il parser usa un fallback sulla data locale del file quando i metadati mancano;
  non introduce conversioni di fuso orario. Gli elapsed maggiori di un giorno
  vengono normalizzati usando il primo valore. I nomi dei file originali
  restano soggetti alle regole già implementate per archivio/cloud e collisioni.
- **Giri**: i moduli `goats_store.py` conservano interpolazione crossing/iTOW
  quando disponibili e filtro del giro finale incompleto nei CSV. L'analisi
  settori Windows usa il catalogo e le intersezioni con le linee.
- **Circuiti**: JSON `schema_version: 3`, `start_line`, `sectors`, raggio e
  direzione. GTC3 versione 1: massimo 50 circuiti e 12 linee intermedie.
  Le linee intermedie non sono il numero dei settori reali, che è `linee + 1`.
  Il GTC3 non conserva tutti i metadati JSON (per esempio paese e ID originale).
- **USB circuiti**: `GTRK_GET`/`GTRK_DATA`/`GTRK_END` e
  `GTRK_BEGIN`/`GTRK_READY`/`GTRK_OK`, payload binario e CRC32, seriale 115200.
- **USB sessioni Windows**: handshake `GSD_PING`, stato/elenco e nomi UTF-8
  codificati in esadecimale, `GSD_GET`, `GSD_CAPS`, `GSD_NEXT4` o `GSD_NEXT`,
  `GSD_END`/CRC32, `GSD_CANCEL` e `GSD_DELETE`. BURST4 esiste già nello ZIP.
  Il baud USB 115200 non è il baud UART GNSS 230400.
- **Wi-Fi Android**: HTTP GET `/api/sessions`, fallback `/sessions` e
  `/goats/sessions`, download URL fornito dal server o percorsi derivati.
  Nessun endpoint è stato aggiunto ai firmware.
- **Sincronizzazione**: scambio dei file sessione originali; non condivisione
  simultanea del database SQLite tra PC e telefono. SAF richiede un provider
  Android che supporti la selezione di cartelle: non tutti i provider lo offrono.

## Verifiche eseguite

Ambiente Linux con Python 3.12.14. Dipendenze Windows installate in un venv
esterno alla repository: PySide6 6.11.3, pyserial 3.5, requests 2.34.2,
entro i vincoli originali. Nessuna versione delle dipendenze è stata cambiata.

| Controllo | Risultato |
|---|---|
| Collaudo precedente | Versione allegata confermata testata e funzionante dall'utente |
| Identità dei 146 file importati | Tutti i digest corrispondono agli ZIP |
| Sintassi/compilazione Python | Tutti i 21 moduli delle applicazioni passano `compile(...)` |
| Manifest e risorse XML Android | Parsing riuscito |
| Import moduli Windows e dipendenze Qt/Charts/WebEngine | Riuscito |
| Istanziazione finestra Qt senza schermo | Riuscita: 9 pagine di navigazione + confronto; rete HTTP bloccata durante la prova |
| Test Windows | 12 passati; 1 caso specifico Android escluso |
| Test motore Android | 10 passati; 3 casi specifici Windows esclusi |
| Build APK locale | Bloccata dalla mancanza di compilatore Java, nessun APK prodotto |
| GitHub Actions sul commit di importazione | Test motore Android passati; build bloccata da SDK `platforms;android-37` non trovato |
| Windows nativo / telefono / hardware / provider cloud | Prove non ripetute durante questa migrazione |

I 22 test passati coprono GRT8 con CRC, GSA2 v1/v2 e GSA3 sintetici, JSON
storico, CSV con entrambi i delimitatori, metadati/data/ora e diagnostica,
giro completato e crossing, SQLite/reimport/note/cancellazione, export
CSV/JSON/GPX, bridge Android, CRUD circuiti e merge, identità binaria GTC3
tra piattaforme, compatibilità dello schema SQLite e semantica CSV comune.
Il trasferimento USB è simulato con e senza BURST4, compreso rifiuto CRC e
pulizia del `.part`. Sono verificati anche i percorsi remoti `ROOT:` e il
rifiuto di percorsi che risalgono alle directory superiori.

Per ripetere i test dalla root con un ambiente Python che abbia le dipendenze Windows:

```sh
python tests/mobile_windows/verify_import.py windows
python tests/mobile_windows/verify_import.py mobile
```

Il controllo Qt verifica la costruzione dei widget; i warning OpenGL/DBus
del sistema Linux senza schermo non certificano la resa grafica Windows.
Non sono stati eseguiti `.bat`, configurazione GNSS, ZTP, upload cloud o comandi
su dispositivi reali. Gli archivi storici personali non sono disponibili;
la compatibilità accertata riguarda gli esempi e i casi sintetici descritti.

La prova Android ha usato gli stessi sorgenti in una copia di lavoro esterna,
Gradle 9.4.1 e il proxy dell'ambiente configurato solo nel Gradle user home.
Risolti i plugin AGP 9.2.0/Compose/Chaquopy, `:app:assembleDebug` si ferma con:

```text
Could not create task ':app:compileDebugJavaWithJavac'.
Toolchain installation '/usr/lib/jvm/java-21-openjdk-amd64'
does not provide the required capabilities: [JAVA_COMPILER]
```

Nell'ambiente locale sono assenti `javac`, `sdkmanager` e un Android SDK configurato.

### Verifica GitHub Actions dopo il push autorizzato

Importazione pubblicata con commit
[`a32c336d6ba84f3f86fc663a7f92bdc2a371abb7`](https://github.com/ady1972/TELEMETRY/commit/a32c336d6ba84f3f86fc663a7f92bdc2a371abb7).
Il [workflow automatico](https://github.com/ady1972/TELEMETRY/actions/runs/43740817846)
ha installato JDK 17 e Python 3.13 e superato i test del motore Android.
L'installazione SDK si è fermata con:

```text
sdkmanager "platforms;android-37" "build-tools;36.0.0"
Warning: Failed to find package 'platforms;android-37'
Process completed with exit code 1.
```

La compilazione Java/Kotlin non è quindi iniziata neppure in CI e non è stato
prodotto un APK. Questo esito non dimostra un errore nei sorgenti Kotlin;
la compilabilità completa rimane da verificare. Serve un SDK 37 ottenibile
dall'ambiente di build. `compileSdk`, `targetSdk` e dipendenze originali sono
conservati: non sono stati abbassati per aggirare il problema.

## Incongruenze e limiti già presenti, lasciati invariati

1. **Etichette versioni miste.** Windows mostra V5.4.15.4 nel file chiamato
   `goats_rt_manager_v5_4_13_11.py`; bootstrap e launcher citano V5.4.14.1 e il
   manuale V5.4.13.0. Android dichiara `versionName = "0.2.1"` ma launcher,
   README e workflow storico citano ancora V0.1.9.3. Sono conservati integralmente.
2. **Manifest storico Windows obsoleto.** In `SHA256SUMS.txt`, 85 digest
   corrispondono, 5 no (`AVVIA_GOATS_RT_MANAGER_V5.bat`, `VERSIONE.txt`,
   `goats_bootstrap.py`, `goats_rt_manager_v5_4_13_11.py`,
   `goats_rt_manager_v5_4_13_6.py`); 6 entry di cache non sono nello ZIP.
   I nuovi manifest descrivono i file realmente ricevuti e importati.
3. **Pannello USB Windows e Guition RC2.** `goats_test23_protocol.py::connect_port`
   accetta solo una risposta `GSD_PONG TEST...`; il Guition RC2 nel repository
   risponde `GSD_PONG GUITION_V1_0_10`. Inoltre l'elenco Guition usa `GSD_FILE`,
   mentre il pannello attende `GSD_ITEM`. Questo pannello non è compatibile
   con quel protocollo Guition così com'è. La verifica non si estende a tutti
   gli altri percorsi di import del Manager. RLCD RC2 espone il dialetto TEST
   e BURST4, ma richiede comunque prova hardware. Firmware consultati soltanto
   in lettura: `firmware/guition-43/goats_guition_43_rc2/goats_usb_tracks_v1025.h`
   e `firmware/rlcd-42/GOATS_RLCD_RC2/goats_sd_usb_export.h`.
4. **Wi-Fi e funzionamento offline.** È presente un client REST Android;
   non è verificata l'esistenza del relativo server sui dispositivi. La
   traiettoria Android è disponibile senza rete; tile nuove e ricerca località
   richiedono Internet. Windows usa anche Leaflet da CDN per le mappe.
5. **CSV non uniformi al 100%.** Il parser Android accetta alias aggiuntivi
   come `lat_e7`/`lon_e7` e coordinate E7. Windows non ha questa estensione.
   I due moduli restano distinti; non sono stati uniformati.
6. **Export e round-trip.** L'export JSON scrive `points`, mentre il parser
   JSON storico legge `laps[].trace[]`: reimportare il JSON esportato non
   ricostruisce automaticamente i punti. L'export CSV include 10 colonne base
   e non conserva tutti i metadati/diagnostici del CSV SD originale.
   Per Cloud Sync vengono scambiati i file originali, non gli export convertiti.
7. **Cloud e NAS.** Sono presenti le implementazioni di copia/importazione,
   non un collaudo end-to-end con Android e client cloud/NAS reali. Le
   decisioni sui conflitti usano anche nome e dimensione: non equivalgono a
   una sincronizzazione transazionale o a un confronto completo dei contenuti.

Questi punti sono separati dalla migrazione e non sono stati corretti qui,
per preservare il comportamento ricevuto e il vincolo sui protocolli.
