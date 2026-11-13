# GOATS RT — RLCD 4.2 a tre colori

Versione **V0.40.5 BOOT FAST + FONT TEST**, per ESP32-S3 con display
riflettivo ST7306 rosso/nero/bianco. Importata dall'archivio
`GOATS_V0405_BOOT_FAST_FONT_TEST_2026_11_03.zip` fornito dall'utente.

I 14 file originali sono conservati senza modifiche nella sottocartella
[GOATS_V0405_BOOT_FAST_FONT_TEST](GOATS_V0405_BOOT_FAST_FONT_TEST/).
Le note originali descrivono anche release precedenti: per lo stato attuale
fare riferimento all'analisi dei sorgenti qui sotto.

## Versione allineata a TEST26

Disponibile anche [V0.40.6 TEST26](GOATS_V0406_TEST26/README.md), sviluppata
su richiesta dell'utente: GNSS passivo e logiche/menu della RLCD TEST26,
con driver ST7306 tricolore, quattro pulsanti e microSD SDMMC.
La V0.40.5 originale qui descritta rimane invariata.

## Apertura del progetto

Aprire la sottocartella della versione e usare `v0405_boot_fast_font_test.yaml`,
mantenendo accanto la cartella `components`. Il componente locale richiede
ESPHome, framework Arduino per ESP32-S3, libreria SPI e API NVS ESP-IDF.

```sh
cd firmware/rlcd-42-3-colori/GOATS_V0405_BOOT_FAST_FONT_TEST
python -m esphome config v0405_boot_fast_font_test.yaml
python -m esphome compile v0405_boot_fast_font_test.yaml
```

Nessun caricamento sul dispositivo viene eseguito dall'importazione.

## Contenuto e comportamento rilevato

| Modulo | Funzione |
|---|---|
| YAML principale | ESP32-S3, flash 16 MB, Arduino, UART e componente locale |
| `goats_spi_diag.cpp/.h` | Driver ST7306 SPI 4 MHz, framebuffer 30.000 byte, layout logico 400x300 su pannello fisico 300x400, menu e pulsanti |
| `goats_font_bitmap.h`, `goats_speed_95.h`, `goats_layout39_font.h` | Font bitmap; etichette piccole a 16px, numeri grandi dedicati |
| `goats_m9n_cfg.h` | Configurazione attiva M9N in RAM, bootstrap baud e richiesta UBX NAV-PVT a 25 Hz |
| `goats_ubx_m9n_ak97_full.h` | Parser UBX/NMEA, stato GNSS e campioni con iTOW mappato sul tempo ESP |
| `goats_laptimer.h` | Traguardo, settori, LAST/BEST, delta e passo gara; dichiarato nelle note derivato da RLCD V1.7.18 |
| `goats_track_catalog.h` | Lettura catalogo GTC3 da NVS e ricerca circuito entro 350 m |
| `goats_lap_storage.h` | Metadati sessione e record per giro in NVS; nessun file CSV o export |
| `__init__.py` | Registrazione del componente e collegamento UART in ESPHome |

### Collegamenti definiti nell'archivio

| Funzione | GPIO |
|---|---|
| ST7306 CS / DC / RESET | 10 / 9 / 8 |
| ST7306 MOSI / SCLK | 11 / 12 |
| GNSS RX ESP / TX ESP | 1 / 2 |
| SU / GIU / INDIETRO / OK | 4 / 5 / 6 / 7, INPUT_PULLUP verso massa |

TE non collegato. Pinout conservato dall'archivio, non verificato su hardware.

Il GPS parte nel YAML a 38400 baud; il codice tenta 38400/9600/115200/230400
per portare il ricevitore a 230400, poi richiede epoche da 40 ms e configura
le costellazioni in RAM. Questa versione trasmette comandi al GNSS;
il progetto 5 pollici transflettivo usa invece ricezione passiva.

Il display aggiorna il cronometro ogni 20 ms e gli elementi ausiliari ogni
400 ms. Si tratta di intervalli richiesti dal loop, non di prestazioni misurate.
L'avvio usa una sequenza a stati ma contiene attese bloccanti nel reset,
nell'inizializzazione LCD e nella configurazione GPS.

## Limiti e incongruenze da conoscere

- Nessun catalogo circuiti è incluso: su un ESP32 nuovo il catalogo NVS
  `goats_tracks/catalog` deve già essere caricato con un mezzo esterno.
  Senza circuito non vengono rilevati giri. Import Manager non implementato.
- Le vecchie note citano LittleFS/CSV, ma il codice corrente salva in
  `goats_laps` su NVS. Il YAML conserva una partizione `goatsfs` da 2 MB
  che questo backend non usa.
- La chiave dei giri usa solo gli 8 bit bassi del numero giro: nella stessa
  sessione i nomi si ripetono ogni 256 giri e possono sovrascrivere record.
- I commit NVS avvengono durante l'elaborazione dei campioni: il loro impatto
  sui tempi di acquisizione va misurato.
- YAML e nome archivio indicano V0.40.5; la schermata Info indica V0.40.4
  e diversi messaggi diagnostici V0402. Conservati per mantenere l'importazione
  identica all'originale; da allineare in una successiva revisione.
- Il motore ignora il parametro `gnss_itow_ms`, ma riceve `now_ms` ricavato
  dal parser tramite mappatura dell'iTOW: non è corretto descriverlo come
  del tutto indipendente dal tempo GNSS. Non è presente interpolazione
  temporale dell'attraversamento della linea.
- Non sono presenti export USB/Manager, logging GNSS completo a 25 Hz,
  microSD, Wi-Fi o OTA. Le note indicano anche la terminazione automatica
  dopo 60 secondi come non ancora portata.

## Verifiche dell'importazione — 13/11/2026

- Integrità ZIP e corrispondenza byte per byte dei 14 file originali verificate.
- Analisi statica di configurazione, dipendenze locali, pinout e moduli.
- ESPHome non installato nell'ambiente di importazione: validazione ESPHome,
  compilazione/link ESP32 e prove hardware non eseguiti.
- Le note dell'archivio dichiarano questa variante non compilata né provata
  su hardware. Il progetto è sperimentale e non viene dichiarato pronto gara.
