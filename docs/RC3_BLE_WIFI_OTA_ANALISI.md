# RC3 — Analisi BLE, Wi-Fi e OTA

Baseline esaminata: `93971fe86123e10adbc93be095f44f800c47c8fd`.
Branch di sviluppo: `feature/rc3-ble-wifi-ota`.

## Baseline e partizioni

| Dispositivo | Sorgente di partenza | Flash dichiarata | Capacità di ogni slot OTA |
|---|---|---:|---:|
| Guition 4.3 (480×272, touch) | `firmware/guition-43/goats_guition_43_rc2.yaml` e `goats_guition_43_rc2/` | 4 MiB | `0x1C0000` (1.835.008 byte) |
| RLCD 4.2 monocromatico (300×400, pulsanti) | `firmware/rlcd-42/goats_rlcd_rc2.yaml` e `GOATS_RLCD_RC2/` | 16 MiB | `0x7C0000` (8.126.464 byte) |

Le dimensioni degli slot provengono dai due `partitions.csv` generati con ESPHome 2026.7.3, la versione fissata dalla CI RC2. Entrambi i layout contengono `otadata`, `phy_init`, `ota_0`, `ota_1` e `nvs`. La flash fisica e le partizioni installate restano da leggere via USB su un'unità di ciascun modello. Le RC2 sono le basi di sviluppo più recenti. Guition V1.0.15 e RLCD TEST26 restano i riferimenti di stabilità e cronometraggio descritti in `AGENTS.md`.

Nei due YAML RC2 non sono configurati servizi BLE, Wi-Fi e OTA. L'app di partenza è `mobile/v0.2.3` (modulo `:app` in `fullapp/`). Il client `LapTimerTransferManager.kt` riguarda il trasferimento delle sessioni via HTTP e non gestisce gli aggiornamenti firmware. La nuova versione Android va conservata in una directory propria, secondo la convenzione di `mobile/README.md`.

## Guition 4 MiB — esito della prova di ingombro

La baseline RC2 Guition compila con un'immagine applicativa di 1.249.648 byte e lascia 585.360 byte per slot. Su una copia isolata dello stesso sorgente ho aggiunto `esp32_ble` (Bluedroid), `wifi` in modalità access point con accensione automatica disabilitata e `web_server` locale. Il linker ha prodotto un'immagine di 2.120.912 byte. Il controllo ESP-IDF ha rifiutato entrambi gli slot per un'eccedenza di 285.904 byte ciascuno. La prova non include GATT applicativo, upload OTA o verifica firma.

Su 4 MiB due copie della sola immagine sperimentale richiederebbero già più della flash totale. Propongo di misurare NimBLE in modalità periferica con un endpoint ESP-IDF HTTP dedicato all'upload, senza il server web generico. Il criterio è far entrare l'intera immagine firmata con margine nello slot attuale, preservando il comportamento GNSS, il display e USB. Se l'immagine ottimizzata continua a eccedere lo slot, i risultati della lettura fisica potranno stabilire se esiste una revisione Guition con più flash da qualificare separatamente. Evitare modifiche a geometria e bootloader prima di queste misure.

## Lettura USB prima della migrazione

Con il dispositivo fermo e in modalità download USB, ESP-IDF 5.5.5 include esptool 4.14.0. Sostituire `PORTA` con la porta del modello collegato e usare un nome di file distinto per ogni modello.

```sh
python -m esptool --chip esp32s3 --port PORTA flash_id
python -m esptool --chip esp32s3 --port PORTA read_flash 0x8000 0x1000 partizioni.bin
python "$IDF_PATH/components/partition_table/gen_esp32part.py" partizioni.bin
```

L'offset `0x8000` è quello della baseline generata. Confrontare il risultato con il layout generato. I comandi interrogano la flash senza scriverla.

## Bootloader, firma e recupero

ESPHome 2026.7.3 disabilita la configurazione di rollback se non sono presenti sia OTA sia safe mode. I due slot generati per RC2 non dimostrano la disponibilità del rollback sul bootloader già installato. Per RC3, propongo di conservare la geometria di ciascuna scheda se l'immagine completa firmata entra nel relativo slot. Il primo caricamento USB deve installare anche bootloader e tabella partizioni compatibili. Prima di scegliere modifiche a bootloader o partizioni occorre verificare il layout installato e misurare su Guition l'immagine collegata con BLE, access point, server di upload e verifica firma. Il controllo a runtime deve comunque usare la capacità effettiva dello slot inattivo.

Per la conferma post-avvio, verificare che il meccanismo scelto lasci l'immagine nello stato di verifica fino ai controlli essenziali dell'applicazione. Provare un riavvio forzato prima della conferma sul dispositivo. La via di recupero è il caricamento USB di un'immagine completa specifica per modello; la migrazione deve verificare anche la persistenza delle preferenze NVS e delle registrazioni microSD.

Per distribuire aggiornamenti GitHub e installarli offline, propongo lo stesso manifesto firmato con modello, revisioni compatibili, versione, layout, dimensione, digest SHA-256 e URL. La chiave pubblica di rilascio va incorporata in app e firmware. La firma di rilascio richiede una chiave sotto il controllo del progetto. Il telefono deve poter conservare manifesto e immagine insieme; l'ESP32 deve verificare il manifesto e l'immagine anche se il telefono ha già effettuato quei controlli. La verifica della tensione riutilizza `battery_voltage` su Guition e `bat_voltage_raw` su RLCD. Soglia e comportamento con alimentazione collegata vanno verificati sotto carico sui due modelli.

## Build e verifiche

- Firmware: `esphome compile firmware/guition-43/goats_guition_43_rc2.yaml` e `esphome compile firmware/rlcd-42/goats_rlcd_rc2.yaml`. ESPHome distingue l'immagine completa `firmware.factory.bin` dall'immagine applicativa `firmware.ota.bin`.
- Android: da `mobile/v0.2.3`, la CI usa JDK 17, Gradle 9.4.1, SDK `platforms;android-37.0` e `gradle :app:assembleDebug`. Il repository contiene la configurazione del wrapper ma manca il relativo JAR. L'ambiente di analisi dispone di Java e richiede SDK e Gradle per l'APK.
- Test software della baseline: `python tests/rc2/run.py` PASS. `python tests/mobile_windows/verify_import.py mobile` ha eseguito 13 casi, con 10 riusciti e 3 saltati perché riguardano Windows o Qt. Passano anche i 16 casi di bridge, cancellazioni mobili e gestione dei file di sessione.
- Generazione ESPHome `compile --only-generate`: riuscita per entrambi i modelli. La dimensione Guition di cui sopra è stata misurata dopo linking.
- Build complete RC2 con ESPHome 2026.7.3 ed ESP-IDF 5.5.5: entrambe riuscite. Immagine applicativa Guition 1.249.648 byte, RLCD 645680 byte.
- Collaudo fisico da eseguire: lettura della flash; identificazione di due unità uguali; spegnimento e riattivazione radio; avvio sessione con radio accese; trasferimento offline da Android; rifiuto per modello, firma, batteria o dimensione; perdita della rete; ritorno alla versione precedente; recupero USB; confronto GNSS 25 Hz, cronometraggio, microSD e USB con la baseline.

Il brief RC3 prevede che OTA blocchi l'avvio della sessione finché l'aggiornamento è in corso. La roadmap precedente parla di annullare i trasferimenti all'avvio di una sessione. La distinzione proposta è bloccare l'avvio durante OTA e spegnere le radio prima di iniziare una sessione in tutti gli altri stati. Il trasferimento di sessioni e AssistNow hanno requisiti propri nella roadmap.
