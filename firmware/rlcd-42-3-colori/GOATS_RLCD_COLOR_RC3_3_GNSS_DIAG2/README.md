# GOATS RLCD COLOR RC3.3-GNSS2

Firmware completo: schermate e logiche della RLCD RC3.3, con trasporto e
configurazione GNSS della V0.40.5 GPS DIAG2 confermata dall'utente il 26/11/2026.
La foto DIAG2 mostra comunicazione e fix attivi; il firmware completo di questa
cartella deve ancora essere collaudato sulla scheda.

## Installazione ESPHome USB

Estrarre tutto lo ZIP e tenere affiancati:

- `goats_42_color_rc3_3_gnss_diag2.yaml`
- cartella `GOATS_RLCD_COLOR_RC3_3_GNSS_DIAG2`

Aprire questo unico YAML in ESPHome, compilare e installare via USB come prima.
Lo ZIP include anche `bin/firmware.factory.bin`, immagine completa per
ESPHome Web via USB (offset 0x0 se richiesto dallo strumento).
`firmware.ota.bin` e' soltanto l'applicazione: non usarla come immagine completa.
Non serve aggiornare tramite Manager. Nessun Wi-Fi o OTA introdotto.

All'avvio compare direttamente la Racing RC3.3, senza splash o pagina
GPS diagnostica automatica. Nella pagina Info GPS la versione e' RC3.3-GNSS2.
Attendere l'inizializzazione del modulo e verificare satelliti/fix in Racing;
per il fix a freddo lasciare l'antenna con cielo libero.

## Hardware e collegamenti

ESP32-S3-DevKitC-1 N16R8 (16 MB flash, 8 MB PSRAM), display ST7306 tricolore.
Non viene attivata la PSRAM: il firmware usa la RAM interna come le versioni
precedenti. Mantenere il cablaggio esistente.

| Funzione | GPIO ESP32-S3 |
|---|---|
| Ricezione GPS: TX del modulo -> RX ESP | 1 |
| Trasmissione GPS: RX del modulo <- TX ESP | 2 |
| LCD CS / DC / RESET | 10 / 9 / 8 |
| LCD MOSI / SCLK | 11 / 12 |
| SU / GIU / INDIETRO / OK | 4 / 5 / 6 / 7, verso GND |
| microSD SDMMC CLK / CMD / D0 | 21 / 38 / 39 |

Massa comune tra ESP, GPS e display. I pulsanti non occorrono per vedere
la Racing o acquisire il fix. Rimangono necessari per navigare nei menu.

## Porting GNSS

- UART ESPHome e logger identici allo YAML DIAG2: RX1/TX2, bootstrap 38400,
  buffer 16384 byte, logger INFO e baud seriale 0; formato predefinito 8N1.
- Codice di `goats_m9n_cfg.h` conservato integralmente dentro una guardia
  privata di compilazione. Stessi 17 frame, stessi cambi baud tramite
  `set_baud_rate()` e `load_settings()`, stessi ritardi espliciti (2430 ms).
- Tentativi 38400/9600/115200/230400, poi 230400; richiesti 25 Hz in RAM,
  stesse costellazioni, SBAS e messaggi UBX/NMEA della DIAG2. Nessuna scansione
  o interrogazione supplementare e nessuna riconfigurazione dopo l'avvio.
- Attesa minima iniziale di 900 ms come DIAG2; il display RC3.3 usa la propria
  inizializzazione. La sequenza completa di boot include anche SD/USB RC3.3,
  quindi non si dichiara identica nei tempi complessivi al diagnostico.
- Configuratore e parser Arduino sono compilati in un file .cpp separato.
  Le guardie private impediscono che gli header raccolti in esphome.h
  creino un secondo parser o ricevano le macro del clock di main.cpp.
- Il parser e i contatori DIAG2 mantengono l'orologio Arduino originale.
  I timestamp pubblici per Racing/Info GPS vengono registrati separatamente
  con l'orologio ESPHome della RC3.3: nessuna sottrazione tra epoche diverse.
- Un solo lettore UART; ogni NAV-PVT con checksum valido e almeno 92 byte
  passa una sola volta, integro, a `goats_b::on_pvt()`. Nessun payload
  ricostruito, timestamp sostituito o laptimer della COLOR importato.

Il parser conserva le proprie elaborazioni V0.40.5; il motore RC3.3 continua
ad applicare i propri criteri di fix, gestione iTOW, data/ora e registrazione.
Non viene richiesta conferma ACK completa delle impostazioni: come nella
DIAG2, il fatto che i comandi siano inviati non ne dimostra l'accettazione.

## Schermate e logiche RC3.3 conservate

I 19 header originali RC3.3 sono identici byte per byte. La lambda grafica,
font, SPI, pulsanti, intervalli applicativi e pin restano quelli del porting
tricolore RC3.3: Racing Delta/Lap Time, settori, LAST/BEST, post giro,
modalita' persistente, menu, circuiti, sessioni e dettagli giro.
Restano il rosso per i delta negativi e gli aiuti a quattro tasti della variante
tricolore; geometria e disegno corrispondono alla RC3.3.

Driver ST7306 differenziale e font nativi conservati: primo frame completo,
poi sole zone modificate, nessun ripristino periodico del pannello.
Splash assente. Non viene importata la grafica del vecchio diagnostico.

microSD, CSV, sessioni, protocollo USB e proprieta' della USB MSC restano RC3.3.
L'accesso SD automatico resta differito al primo fix valido; il Manager puo'
richiederlo secondo il protocollo esistente. Partizioni RC3.3 conservate,
con NVS a 0xF90000; il diagnostico standalone usava una tabella diversa.
Compatibilita' Arduino/esp_tinyusb limitata alla libreria Arduino come nella
precedente variante completa, senza modificare il framework installato.

## Verifica

Vedere `VERIFICA.md`. Configurazione, compilazione, confronto GNSS e prove
RC3.3 superati. Il funzionamento della DIAG2 sul dispositivo non sostituisce
il collaudo di questo firmware completo, incluse microSD, USB e cronometraggio.
Le versioni precedenti rimangono conservate nelle proprie cartelle.
