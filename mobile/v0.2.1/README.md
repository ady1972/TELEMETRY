# GOATS Mobile — Android V0.2.1

Importazione di `GOATS_RT_Manager_Android_V0_2_1_TRACK_EDITOR_WIFI_CLOUD_SYNC.zip`.
I 46 file originali sono conservati senza modifiche al contenuto. Il manifest
`IMPORTED_SOURCE_SHA256SUMS.txt` permette di verificarli da questa cartella.

Il progetto Gradle va aperto da `mobile/v0.2.1/`: il modulo logico `:app` contiene i
sorgenti in `fullapp/` e produce l'APK in `app/build/outputs/apk/debug/`.

## Compilazione

Servono JDK 17, Android SDK Platform 37 e Build Tools 36.0.0, oltre a Internet
per il primo download. Sono mantenuti Gradle 9.4.1, AGP 9.2.0, Compose plugin
2.2.10, Chaquopy 17.0.0 e Python incorporato 3.13. Android minimo: API 24;
ABI: arm64-v8a e x86_64. Le altre versioni sono in `fullapp/build.gradle.kts`.

Da `mobile/v0.2.1/`, su Windows:

```bat
gradlew.bat :app:assembleDebug
```

Su Linux/macOS:

```sh
sh ./gradlew :app:assembleDebug
```

Gli script di bootstrap inclusi scaricano Gradle senza richiedere un wrapper JAR.
Il workflow attivo per la monorepository è
[`../../.github/workflows/mobile-android.yml`](../../.github/workflows/mobile-android.yml).
Quello originale in `mobile/v0.2.1/.github/` è conservato per provenienza e non viene
eseguito da GitHub in questa posizione.

## Funzionalità verificate nei sorgenti

- Archivio SQLite offline e file sessione originali; import GRT8/GSA2/GSA3/CSV/JSON.
- Elenco, ricerca ed eliminazione sessioni; analisi giri, traiettorie e velocità.
- Mappe native con cache tile, traccia offline, zoom/pan/FIT.
- Editor circuiti: traguardo, settori, JSON schema 3 e cataloghi GTC3.
- Upload/download circuiti USB OTG con merge; sessioni remote tramite client Wi-Fi REST.
- Cloud Sync tramite cartella scelta con Storage Access Framework e upload automatico
  dopo l'importazione. Disponibilità dei provider da verificare sul telefono.

L'activity iniziale è il launcher diagnostico, che offre il pulsante per aprire
il Manager completo. Replay/frenate e confronto completo del PC non sono presenti
nell'interfaccia Android; note, confronto ed export hanno capacità nel motore
che non sono tutte esposte nella UI. Non c'è trasferimento sessioni BLE.

Stato build, prove, compatibilità e limiti sono nel
[rapporto di migrazione](../../docs/MIGRATION_MOBILE_WINDOWS_REPORT.md).
I README e report storici inclusi nello ZIP descrivono anche versioni precedenti:
non costituiscono un collaudo della V0.2.1.
