# Verifica TEST26 con GNSS V0.40.5 — 26 novembre 2026

## Sorgenti e integrazione

- Base: COLOR V0.40.6 TEST26 su `main`, commit
  `855954ed7c4b96e7f36ec8fffcd786c6c5973a07`.
- I 14 header applicativi TEST26, incluso il parser `m9n_passive.h`, e tutti
  i componenti/font/driver ST7306 sono copiati byte per byte senza modifiche.
- Il configuratore proviene da
  `GOATS_V0405_BOOT_FAST_FONT_TEST/components/goats_spi_diag/goats_m9n_cfg.h`.
  Le sole modifiche sono `Arduino.h` sostituito con `esphome/core/hal.h` e
  `delay()` qualificato come `esphome::delay()` per compilare con ESP-IDF.
- On boot ESPHome a priorità -100, una sola chiamata nel ramo normale, dopo
  la configurazione UART. In modalità USB MSC il configuratore viene saltato.
- UART RX GPIO1, TX GPIO2, bootstrap 38400, buffer RX 16384 come V0.40.5;
  il codice ripristina ESP e ricevitore a 230400 prima di entrare nel loop.
- Scheduling 1 s / 10 ms / 5 s, motore, sessioni, formato dati, SD e USB TEST26
  invariati. Nessuna riconfigurazione GNSS durante la registrazione.
- Splash eliminato come richiesto in precedenza: nessun asset immagine o attesa
  grafica di tre secondi. Layout operativo della COLOR TEST26 conservato.
- Versioni originali TEST26 e V0.40.5, firmware monocromatici e ramo RC3.3
  non modificati da questa variante.

## Test eseguiti

```sh
python tests/rlcd_color_test26_gnss/run.py
python tests/rlcd_color/check_reference.py
```

**PASS**. Il test del configuratore compila ed esegue sia il codice V0.40.5
originale sia quello portato, con AddressSanitizer e UndefinedBehaviorSanitizer.
UART e tempo sono simulati; non è un test del ricevitore reale.

- Identici **17 frame UBX**, baud di trasmissione, checksum e tempi delle attese.
- Identica sequenza host 38400/9600/115200/230400/230400.
- Attese esplicite pari a **2430 ms**, esclusi i tempi fisici UART.
- Tutti i VALSET indirizzati soltanto al layer RAM, nessun CFG-CFG di salvataggio
  o comando di reset del ricevitore.
- Modello di trasporto per tutti i quattro baud iniziali: i frame ricevuti al
  baud corretto portano il modello a 230400 e contengono le richieste finali
  di 40 ms, NAV-PVT/DOP/SAT, NMEA e costellazioni della V0.40.5.
- Due avvii normali consecutivi eseguono ogni volta la configurazione.
- Il codice reale della lambda on_boot viene compilato nel test: il ramo USB
  non scrive sulla UART GPS e non cambia baud.
- Confronto byte per byte dei 14 header e di tutte le dipendenze display;
  confronto delle sezioni interval, framework, SPI e pulsanti TEST26.
- Verifica di RX1/TX2, assenza di splash, rete, OTA e PSRAM.
- Riferimento COLOR TEST26 passivo: controlli storici superati.

Il modello UART verifica i pacchetti richiesti, non l'accettazione del firmware
u-blox. Come l'originale, questa versione non legge ACK/NAK per confermare ogni
impostazione. MAXSVS/25 Hz/costellazioni restano soggetti ai limiti del ricevitore.

## Validazione e build

- `esphome config`: **PASS**, ESPHome 2026.7.3.
- Compilazione e link ESP32-S3/ESP-IDF 5.5.5: **PASS**.
- RAM statica: **161.707 byte**, 47,3% dei 341.760 byte riportati dal linker.
- Applicazione: **673.047 byte**, 8,3% dello slot da 8.126.464 byte.
- Immagine factory ESP32-S3 da **16 MB** verificata con esptool; offset primo
  flash **0x0**. La factory contiene bootloader, partizioni e applicazione.
- Non si usano file .bin della RC3.3 o di altri modelli.

## Pacchetti e prove pendenti

Lo ZIP sorgenti contiene lo YAML e `GOATS_V0406_TEST26_GNSS_V0405/` affiancati,
senza dipendenze applicative da cartelle di altre versioni. Il pacchetto USB
contiene factory e istruzioni, con la nuova connessione RX GPS → GPIO2 evidenziata.
Manifest SHA-256 e integrità ZIP verificati; sorgenti estratti e configurazione
ESPHome verificata separatamente.

Nessun flash, misura elettrica, fix GNSS o collaudo in pista eseguito.
Verificare entrambe le linee UART, avvio a freddo, NAV-PVT effettivo prossimo
a 25 Hz, satelliti/fix e ripetizione dopo spegnimento. In seguito collaudare
giri, SD e trasferimenti USB sul dispositivo. I test software non certificano
il funzionamento del ricevitore o dell'alimentazione reali.
