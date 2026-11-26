# COLOR TEST26 — GNSS come V0.40.5

Variante richiesta il 26 novembre 2026: **COLOR V0.40.6 TEST26**, con
inizializzazione attiva del ricevitore MG902/M9N come **COLOR V0.40.5**.
Target ESP32-S3 da **16 MB**, display ST7306 tricolore, senza PSRAM richiesta.

Le versioni V0.40.5, TEST26 passiva e RC3.3 restano separate. Questa variante
usa motore, menu e grafica della COLOR TEST26; non è la COLOR RC3.3.
Lo splash rimane disabilitato, come richiesto per il residuo del logo sul pannello.
La versione di progetto è `0.40.6-gnss0405`; Info mostra `TEST26 GNSS 0.40.5`.

## Configurazione GNSS ripristinata

In ogni avvio normale, dopo l'inizializzazione della UART e prima delle attività
applicative, viene trasmessa la stessa sequenza V0.40.5:

| Parametro | Richiesta al ricevitore |
|---|---|
| Baud iniziali provati | 38400, 9600, 115200, 230400 |
| Baud finale ESP/ricevitore | 230400 |
| Frequenza navigazione | 25 Hz, epoca 40 ms |
| UBX NAV-PVT | Ogni epoca |
| UBX NAV-DOP e NAV-SAT | 1 Hz a regime 25 Hz |
| NMEA GGA, GSA, GSV, RMC | 1 Hz a regime 25 Hz |
| NMEA GLL, VTG, ZDA | Disabilitati |
| Costellazioni richieste | GPS, Galileo, BeiDou, GLONASS e SBAS attivi; QZSS disattivato |
| MAXSVS richiesto | 32, soggetto ai limiti del ricevitore |
| Memorizzazione | Solo RAM: nessun salvataggio in flash/BBR del ricevitore |

Le impostazioni vengono ripetute al successivo avvio, quindi non dipendono
da una configurazione GPS conservata dopo aver tolto alimentazione.
La sequenza contiene circa 2,43 secondi di attese software, oltre ai tempi UART
e all'avvio display. Non attende il fix e non modifica i tempi di acquisizione
durante il funzionamento. In modalità USB MSC il configuratore non viene eseguito.

Il codice originale **non verifica gli ACK/NAK** del ricevitore: si dichiara
trasmessa la sequenza, non confermata ogni impostazione. Alcune richieste
possono essere limitate dal modello/firmware GNSS. Frequenza e ricezione reali
vanno controllate nella schermata Info GPS dopo il caricamento.

Se il GPS perde alimentazione mentre l'ESP32 resta acceso, riavviare anche
l'ESP32 per ripetere l'inizializzazione. Non è introdotta una riconfigurazione
periodica durante il cronometraggio.

## Collegamenti GPS — ora servono entrambe le linee UART

| Ricevitore GPS | ESP32-S3 |
|---|---|
| TX | **GPIO1**, RX dell'ESP32 |
| RX | **GPIO2**, TX dell'ESP32 |
| GND | GND comune |
| VCC | Secondo la scheda del modulo; 3V3 solo se ammesso su VCC |

**Il collegamento RX GPS → GPIO2 è necessario per inviare la configurazione.**
I pin segnati TX/RX sulla DevKit possono essere GPIO43/44: usare i numeri
GPIO1/2 effettivi. Livelli UART compatibili con 3,3 V, nessun segnale a 5 V.
Cambiare i collegamenti a dispositivo spento.

Gli altri collegamenti sono quelli della COLOR TEST26:

| Funzione | GPIO |
|---|---|
| LCD CS / DC / RESET | 10 / 9 / 8 |
| LCD MOSI / SCLK | 11 / 12, SPI 4 MHz |
| LCD VCC / GND / TE | 3V3 / GND / scollegato |
| SU / GIÙ / BACK / OK | 4 / 5 / 6 / 7, pulsanti verso GND |
| microSD CMD / CLK / DAT0 | 21 / 38 / 39, SDMMC 1 bit |
| microSD VDD / VSS | 3,3 V / GND |
| USB nativa D− / D+ | 19 / 20, secondo lo schema della scheda |

SD FAT32 e pull-up 10 kΩ su CMD/DAT0 e DAT1/DAT2/DAT3 se non già presenti.
Il modulo SD deve essere compatibile SDMMC; non è il bus SPI del display.
Nessun ADC batteria assegnato. Nessun Wi-Fi o OTA.

## ESPHome e primo flash

Affiancare nella cartella ESPHome:

```text
goats_42_color_v0406_test26_gnss_v0405.yaml
GOATS_V0406_TEST26_GNSS_V0405/
```

Aprire lo YAML esterno. Tutte le dipendenze applicative sono nella cartella
dedicata. ESPHome/ESP-IDF, TinyUSB e i Google Font richiedono i normali download
alla prima compilazione; lo ZIP non richiede le cartelle di altre versioni.

```sh
esphome config goats_42_color_v0406_test26_gnss_v0405.yaml
esphome compile goats_42_color_v0406_test26_gnss_v0405.yaml
esphome upload goats_42_color_v0406_test26_gnss_v0405.yaml --device COM5
```

Per primo flash manuale con esptool 5:

```sh
python -m esptool --chip esp32s3 --port COM5 write-flash 0x0 firmware.factory.bin
```

Usare la porta reale. La factory include bootloader, partizioni e app ed è
esclusivamente per la scheda da 16 MB. Esportare le sessioni importanti prima
del flash. Non occorre un erase-flash preventivo. Non caricare pacchetti del
modello monocromatico o della Zero da 4 MB.

[Pacchetti sorgenti e USB su GitHub](https://github.com/ady1972/TELEMETRY/tree/codex/color-test26-gnss-v0405/firmware/rlcd-42-3-colori/GOATS_V0406_TEST26_GNSS_V0405/download).

## Verifica al banco

1. Collegare entrambe le linee UART, verificare massa e alimentazione del GPS.
2. Avviare da alimentazione completamente spenta. Non appare il logo.
3. Nel log UART0 cercare `m9n_init`: inizio configurazione e sequenza trasmessa.
4. In Info GPS controllare NAV-PVT Hz, satelliti usati/visti e HDOP. Un valore
   NAV-PVT maggiore di zero conferma ricezione di pacchetti anche prima del fix.
5. All'aperto, verificare fix e frequenza effettiva prossima a 25 Hz; ripetere
   dopo un'altra rimozione completa dell'alimentazione.
6. Collaudare più giri, salvataggio su SD e trasferimento USB sul dispositivo.

Gli esiti software sono in `VERIFICA.md`; nessuna prova hardware è dichiarata
eseguita. Il file `m9n_passive.h` resta il parser di sola lettura TEST26:
il nome storico non descrive il nuovo configuratore attivo eseguito all'avvio.
