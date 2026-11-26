# RC3.3 con runtime Arduino della COLOR — da collaudare

L'utente ha confermato che la V0.40.5 originale riceve GPS sullo stesso hardware.
Le prime diagnostiche RC3.3 mostravano RX/UBX/PVT/SAT a zero, con POLL e UPTIME
in aumento dopo l'avvio. La variante UART0 è stata successivamente segnalata
ancora senza segnale; i nuovi contatori non sono stati ancora trascritti.
La causa esatta non è identificata. Il solo cambio baud e la sola assegnazione
UART0 non costituiscono una soluzione hardware confermata.

## Allineamento al runtime originale

La V0.40.5 usa **Arduino** e logger seriale disattivato. Le precedenti porte
RC3.3 mantenevano il framework ESP-IDF della RLCD. Questa variante torna ad
Arduino tramite ESPHome, conservando i 19 header RC3.3 e tutte le schermate.
Il parser e i comandi sono quelli COLOR già importati. Su Arduino il bootstrap
riutilizza `load_settings()`, come l'originale; non usa il workaround di cambio
baud diretto riservato alla variante ESP-IDF. Pin RX1/TX2, buffer 16384,
UART finale 230400 e richiesta NAV-PVT 25 Hz invariati. Nessun retry/reset
periodico o nuova configurazione delle costellazioni.

Non è una dichiarazione di GPS riparato: è una variante con il runtime del
riferimento funzionante, da verificare sul dispositivo.

## Compatibilità RC3.3 preservata

- **Grafica e laptimer**: il renderer Racing è identico al base; i 19 header
  restano identici byte per byte. Date, settori, sessioni, CSV, SD e protocollo
  USB non vengono sostituiti dal vecchio laptimer COLOR. Splash assente.
- **Clock**: ESPHome genera macro Arduino che rendono invalide le chiamate già
  qualificate `esphome::millis()` / `esphome::delay()` nei sorgenti RC3.3.
  `goats_arduino_time.h` adatta le due macro con nomi univoci mantenendo le
  funzioni HAL ESPHome, senza modificare i 19 header o il comportamento temporale.
- **Partizioni**: `partitions_rc33.csv` mantiene esattamente indirizzi,
  dimensioni e flag della factory RC3.3 ESP-IDF già consegnata. La NVS resta
  a 0xF90000, dimensione 0x70000, senza introdurre lo spostamento dei default
  Arduino. Questo conserva la disposizione, non converte archivi di firmware diversi.
- **USB MSC**: `esp_tinyusb` resta l'unico proprietario della condivisione SD.
  Il componente locale `goats_arduino_usb_compat` esclude il wrapper MSC Arduino
  soltanto durante la compilazione della libreria Arduino. Non cambia sdkconfig
  per l'applicazione e non modifica file del framework. Il build vieta una
  seconda istanza TinyUSB Arduino. Il protocollo Serial/JTAG della RLCD resta invariato.

## Installazione con ESPHome

Scaricare [i sorgenti RC3.3 Arduino](download/GOATS_RLCD_COLOR_RC3.3_ARDUINO_SORGENTI.zip).
Estrarre lo ZIP mantenendo affiancati:

```text
goats_42_color_rc3_3.yaml
goats_42_color_rc3_3_uart0.yaml
goats_42_color_rc3_3_arduino.yaml
goats_42_color_rc3_3_arduino_diag.yaml
GOATS_RLCD_COLOR_RC3_3/
```

Per la prova senza pulsanti aprire **`goats_42_color_rc3_3_arduino_diag.yaml`**,
compilare e installare tramite ESPHome via USB sulla ESP32-S3 da **16 MB**.
La pagina mostra **RC3.3 - GPS ARDUINO**, SET/HW, periferica UART, byte,
UBX, NAV-PVT Hz, satelliti, fix, HDOP, ACK/NAK, errori e contatore POLL.

Dopo il flash spegnere completamente ESP e GPS, riaccendere e attendere circa
60 secondi prima di leggere/fotografare RX, UBX, PVT e SAT. Per il fix a freddo
possono servire alcuni minuti in condizioni di ricezione. Nessun tasto richiesto.
La prima foto immediata può mostrare i valori iniziali ancora a zero.

Per il firmware completo con Racing usare **`goats_42_color_rc3_3_arduino.yaml`**:
ha identica gestione GNSS della diagnostica e il rendering operativo RC3.3.
Gli altri due YAML sono basi incluse, da mantenere affiancate. Nessun Manager,
Wi-Fi o OTA richiesto. I precedenti pacchetti rimangono archiviati.

## Verifiche software

- Configurazioni risolte confrontate con la base: sono ammesse solo variazioni
  di framework, partizioni esplicite, compatibilità USB, identità e renderer
  diagnostico. Racing, boot, pin/UART, intervalli, font e header del core invariati.
- Confronto della tabella partizioni contro i dati binari della factory RC3.3
  precedente, verifica indirizzi/assenza sovrapposizioni e termine a 16 MB.
- Compilazione reale controllata: override USB applicato solo alle unità della
  libreria Arduino; non applicato all'app né a esp_tinyusb. Oggetto USBMSC Arduino
  privo di callback MSC; implementazione RLCD conservata e linkata.
- Test ASan/UBSan riproduce l'errore con le macro generate da ESPHome e verifica
  entrambe le forme qualificate/non qualificate con identica base dei tempi HAL.
- Test configuratore/bridge e parità RC3.3 conservati. Nessun test hardware o
  in pista eseguito sulla variante Arduino.


Build effettive con **ESPHome 2026.7.3, Arduino 3.3.10, ESP-IDF 5.5.5**:

| Variante | Applicazione | RAM statica |
|---|---:|---:|
| Racing completa | 620.279 byte | 163.935 byte |
| Diagnostica Arduino | 611.987 byte | 163.935 byte |

Configurazione, compilazione e link: **PASS** per entrambe. Test dei confini
USB, tabella partizioni compilata e macro clock: **PASS**. Confronti di
configurazione e contratti RC3.3: **PASS**. ZIP estratto con i quattro YAML e
componente locale, entrambe le varianti validate autonomamente e SHA-256
verificati. Restano da collaudare ricezione GPS, SD e USB sul dispositivo.
