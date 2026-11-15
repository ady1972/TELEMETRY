# GOATS RT Manager Android V0.1.9.3 — USB FULL + NATIVE MAP Z22 FIX

Questa build mantiene Dashboard, Sessioni, Analisi, Circuiti e USB OTG. AssistNow è stato rimosso. La mappa satellitare è ora disegnata nativamente in Jetpack Compose: la traiettoria GPS resta visibile anche se le tile satellitari non sono disponibili.

**Fix build:** il modulo Gradle `:app` usa fisicamente la cartella `fullapp/`, quindi eventuali vecchie cartelle `app/` rimaste nella repository vengono ignorate e non possono più mescolare i sorgenti V0.2 ridotti con la V0.1 completa.

# GOATS RT Manager Android 0.1

Porting Android del **GOATS RT Manager V5.4.13.4 REAL SECTOR COUNT FIX**.

## Architettura

- UI Android nativa: Kotlin + Jetpack Compose.
- Motore dati: Python 3.13 incorporato tramite Chaquopy.
- Riutilizzo dei moduli del Manager PC: `goats_formats.py`, `goats_store.py`, `goats_exporters.py`.
- Archivio locale SQLite, utilizzabile offline.
- Collegamento laptimer via USB OTG/seriale a 115200 baud.

## Funzioni presenti nella 0.1

- Import sessioni GRT8, GSA2, GSA3, CSV e JSON.
- Elenco sessioni e database locale.
- Analisi offline con traiettoria GPS, velocità e tempi giro.
- Gestione catalogo circuiti JSON/GTC3.
- Lettura catalogo dal laptimer (`GTRK_GET`).
- Invio dei soli circuiti selezionati con **merge non distruttivo**: i circuiti già presenti e non selezionati vengono conservati.

## Funzioni ancora da portare dal Manager PC

- Editor grafico completo di traguardo e linee settore.
- Replay avanzato e analisi frenate completa.
- Confronto sessioni completo.
- Download diretto dell'archivio sessioni dal laptimer (`GSES2`).

## Metodo consigliato: build automatica su GitHub

Il progetto contiene `.github/workflows/build-android.yml`. Dopo aver copiato tutto nella repository GitHub:

1. Apri la repository su GitHub.
2. Apri **Actions**.
3. Seleziona **Build Android APK**.
4. Premi **Run workflow**.
5. A build completata, apri l'esecuzione e scarica l'artifact **GOATS-RT-Manager-Android-debug**.
6. Dentro l'artifact trovi `app-debug.apk`, installabile sul telefono.

Anche ogni push su `main` o `master` avvia automaticamente una nuova build.

## Build da Android Studio su Windows

1. Installa/apri Android Studio.
2. **File > Open** e seleziona la cartella `GOATS_RT_Manager_Android_V0_1`.
3. Installa, se richiesto, Android SDK Platform 37 e Build Tools 36.0.0.
4. Usa JDK 17.
5. Esegui la sincronizzazione Gradle.
6. Compila con **Build > Build APK(s)** oppure esegui direttamente sul telefono.

La prima build richiede Internet per scaricare le dipendenze Gradle/Maven/Chaquopy/JitPack.

## Collegamento al laptimer

Serve un telefono Android con supporto **USB OTG** e un adattatore/cavo OTG appropriato. Nell'app:

1. Vai in **Circuiti**.
2. Premi **CERCA USB**.
3. Seleziona la seriale del laptimer e accetta il permesso Android.
4. Usa invio/scaricamento circuiti via USB OTG.

## Note

La traiettoria dell'analisi viene sempre disegnata direttamente dai punti GPS. Le tile satellitari Esri sono opzionali e richiedono Internet al primo caricamento; le tile già scaricate vengono riutilizzate dalla cache locale. Senza rete resta comunque visibile la traiettoria su sfondo scuro.

## V0.1.4 - Analisi su mappa

La pagina Analisi offre ora due viste della traiettoria:

- **SAT**: mappa satellitare online con pinch zoom e pan;
- **OFFLINE**: grafica locale senza Internet, ora anch'essa zoomabile e spostabile.

La mappa satellitare richiede accesso Internet; in assenza di rete usare OFFLINE.


## V0.1.7 - compatibilità workflow GitHub precedente
Il modulo logico resta `:app` e i sorgenti restano in `fullapp/`, ma l'output Gradle viene forzato in `app/build`.
In questo modo anche un workflow GitHub rimasto alla vecchia riga `path: app/build/outputs/apk/debug/app-debug.apk` trova correttamente l'APK.

## V0.1.8 - mappa e traiettorie
- Rimossa AssistNow dall'interfaccia e dalle funzioni esposte dall'app Android.
- Mappa satellitare riscritta senza dipendenza da Leaflet/unpkg: il viewer è HTML/JS autonomo.
- Le tile satellitari Esri restano online, ma le traiettorie SVG vengono mostrate anche se le tile non sono disponibili.
- In modalità TRACCIA i giri vengono disegnati separatamente con colori diversi.
- Zoom: pinch, pulsanti + / -, rotella (se presente), pan e FIT.
- Indicazione del numero di punti GPS presenti nell'analisi.


## V0.1.9.1 - mappa satellitare nativa
- Eliminato il WebView che nella V0.1.8 poteva lasciare il riquadro Analisi completamente nero pur con punti GPS validi.
- Tile Esri caricate direttamente dal codice Android e memorizzate nella cache locale.
- Traiettoria multi-giro disegnata nativamente sopra le tile e sempre visibile anche offline.
- Centratura automatica FIT sull'intero circuito.
- Pinch-to-zoom, trascinamento, pulsanti + / - e FIT.
- Stato mappa visibile: SAT ONLINE / CARICAMENTO / OFFLINE con traccia comunque attiva.


## V0.1.9.1 - Gradle build fix

Correzione della risoluzione dei plugin Gradle in GitHub Actions. Le versioni
sono ora esplicite nel modulo e in `pluginManagement`; il workflow forza la
root del progetto e mantiene invariata la mappa nativa della V0.1.9.


## V0.1.9.2 - zoom mappa esteso

- Zoom satellitare massimo aumentato da Z19 a Z22.
- Pinch-to-zoom reso più reattivo (cambio livello a circa ±10%).
- Zoom della vista offline/traiettoria aumentato da 20x a 80x.
- FIT continua a ricentrare automaticamente l'intero circuito.
- Se una tile satellitare non è disponibile ai livelli più alti, la traiettoria GPS resta comunque visibile sullo sfondo scuro.
- Core telemetria, USB, sessioni, circuiti e database invariati rispetto alla V0.1.9.1.


## V0.1.9.3 - fix mappa Z20-Z22 e traiettorie
- Vista telemetria fino a Z22.
- Tile satellitari richieste fino a Z19 e riutilizzate/ingrandite oltre Z19, evitando il riquadro Esri “Map data not yet available”.
- Tracce GPS non più decimate a 1600 punti globali: fino a 2500 punti per giro e 60000 complessivi.
- La decimazione di sicurezza avviene per giro, preservando la geometria della traiettoria.
