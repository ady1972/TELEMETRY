# GOATS Mobile — Android V0.2.2

Progetto completo derivato dalla [V0.2.1](../v0.2.1/README.md), conservata invariata.

## Sincronizzare sessioni e circuiti con Windows

Usare il Manager Windows **V5.4.15.6**. In Sessioni → **SYNC WINDOWS**, scegliere
**CARTELLA CONDIVISA** e indicare la stessa cartella cloud selezionata sul PC.
**SINCRONIZZA ORA** scarica e pubblica sessioni e circuiti. L'opzione automatica
esegue il sync dopo importazioni e salvataggi locali; per ricevere modifiche PC
senza operazioni locali usare il pulsante manuale. Non è un servizio Android
sempre attivo in background.

Il selettore Android deve offrire accesso persistente in lettura/scrittura a una
cartella del provider. La presenza dell'app Google Drive, OneDrive, Dropbox o
Synology Drive non garantisce questa funzione: se la cartella non compare,
usare un provider compatibile o una cartella locale sincronizzata dal servizio.
Non sono implementati login/API proprietari dei servizi cloud.

Sono scambiati i file sessione originali e le revisioni JSON dei circuiti.
SQLite, note, preferenze e credenziali rimangono locali. File con lo stesso nome
ma contenuto diverso sono conservati; i circuiti modificati contemporaneamente
producono varianti «conflitto». Le eliminazioni locali non si propagano.
Si può continuare a lavorare offline e ripetere il sync dopo un errore.
I dettagli sono nella [guida comune](../../docs/CLOUD_SYNC_MOBILE_WINDOWS.md).

## Funzionalità presenti

- Archivio SQLite offline; import GRT8/GSA2/GSA3/CSV/JSON e note lato motore.
- Elenco, ricerca ed eliminazione sessioni; analisi giri, traiettorie e velocità.
- Mappe native con cache tile, traccia offline, zoom/pan/FIT.
- Editor circuiti schema 3 e cataloghi GTC3, traguardo e settori su mappa.
- Upload/download circuiti USB OTG con merge; client sessioni Wi-Fi REST.
- Sincronizzazione sessioni e circuiti compatibile con Windows V5.4.15.6.

Il launcher diagnostico apre il Manager completo. Replay/frenate e confronto
completo del PC non sono presenti nell'interfaccia Android. Il client Wi-Fi
richiede un laptimer con API compatibile; questa release non modifica i firmware.

## Compilazione

Aprire questa cartella in Android Studio. Modulo `:app`, sorgenti `fullapp/`,
APK `app/build/outputs/apk/debug/`. JDK 17, SDK **platforms;android-37.0**,
Build Tools 36.0.0, Gradle 9.4.1, AGP 9.2.0, Compose 2.2.10, Chaquopy 17 e
Python 3.13. Min API 24; ABI arm64-v8a e x86_64. Dipendenze invariate.

```sh
sh ./gradlew :app:assembleDebug
```

Su Windows usare `gradlew.bat :app:assembleDebug`. VersionCode 22; applicationId
invariato. Workflow attivo: `.github/workflows/mobile-android.yml` nella radice
del repository. Il workflow annidato è storico e inattivo.

I `.txt` descrittivi sono in `documentazione/`. `SHA256SUMS.txt` verifica il
pacchetto corrente; documenti storici descrivono le rispettive versioni.
Test software in `tests/cloud_gnss/`; provider reali e telefono da collaudare.
