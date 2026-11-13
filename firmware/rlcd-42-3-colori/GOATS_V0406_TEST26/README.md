# GOATS 4.2 COLOR V0.40.6 TEST26

Porting richiesto dall'utente il 13/11/2026: firmware tricolore con GNSS,
logiche e menu di **RLCD TEST26**. La V0.40.5 originale resta affiancata e intatta.

## Cosa viene allineato

Tutti i 14 header della cartella `firmware/rlcd-42/GOATS_RLCD_MG902_R12_1_SD_R14_2_TEST_26`
sono copiati **byte per byte**: parser GNSS passivo, circuito automatico/manuale,
Manager GTRK, motore giri/settori/delta, notifiche post-giro e BEST,
sessioni GSA3, recupero/scarto, tracce GNSS CSV, salvataggio SD e USB MSC.
Gli intervalli di elaborazione e archiviazione del YAML TEST26 sono conservati;
l'unico adattamento in essi è l'abilitazione dei quattro tasti dopo l'avvio.
Non viene importato il worker dual-core TEST27.

La versione usa ESP-IDF, necessario per SDMMC, USB nativa e moduli originali.
Non abilita PSRAM: l'archivio della scheda tricolore non ne specifica la presenza.
Flash prevista: 16 MB. La partizione `goatsfs` della V0.40.5 non serve al backend
TEST26; il layout flash/NVS cambia, quindi i dati di una precedente installazione
vanno esportati prima del flash. Non viene eseguito alcun flash automatico.

## Display e interfaccia

Driver locale `components/goats_st7306`: stessa inizializzazione ST7306,
mappatura RBW e orientamento del display originale, ora tramite SPI ESPHome.
La schermata Racing conserva geometria, colori e bitmap/font V0.40.5;
i dati arrivano dal motore TEST26 mediante una struttura di sola presentazione.
I menu, le conferme, i dettagli dei giri, le opzioni post-giro e gli avvisi
sono quelli TEST26; i testi di aiuto riportano i quattro pulsanti.
Il display si aggiorna ogni 100 ms come TEST26 e invia solo i gruppi di pixel
cambiati. Questo non garantisce la frequenza effettiva sul dispositivo.
Non è il timer di refresh grafico a determinare l'accuratezza GNSS.

Il renderer non contiene parser, scritture NVS/SD o copie indipendenti degli
stati della telemetria. Le decisioni rimangono nel contesto TEST26.

## Collegamenti

Tutti i GPIO e il display lavorano a **3,3 V**. Confermare che i pin siano
esposti e liberi sulla scheda ESP32-S3 effettivamente utilizzata.

| Funzione | Collegamento |
|---|---|
| LCD CS / DC / RESET | GPIO10 / GPIO9 / GPIO8 |
| LCD MOSI / SCLK | GPIO11 / GPIO12, SPI 4 MHz |
| LCD TE | Non collegato |
| TX GNSS → RX ESP | GPIO1, UART 230400 8N1 |
| RX GNSS | Non collegato all'ESP: nessun TX, nessuna configurazione GNSS inviata |
| SU / GIU / BACK / OK | GPIO4 / GPIO5 / GPIO6 / GPIO7, pulsanti verso GND |
| microSD CMD | GPIO21, contatto 3 della scheda |
| microSD CLK | GPIO38, contatto 5 |
| microSD DAT0 | GPIO39, contatto 7 |
| microSD VDD / VSS | 3,3 V / GND, contatti 4 / 6 |
| USB nativa D− / D+ | GPIO19 / GPIO20, verso connettore USB dati nativo |

La SD usa **SDMMC a 1 bit**, come TEST26: non il bus SPI del display.
Usare un socket/modulo microSD a 3,3 V che esponga CMD, CLK e DAT0.
Prevedere pull-up esterni da 10 kΩ verso 3,3 V sulle linee CMD e DAT0;
anche DAT1, DAT2 e DAT3 vanno mantenute alte con pull-up sul socket se non
sono già presenti sul modulo. CLK non richiede pull-up. Alimentazione
stabile e disaccoppiamento vicino alla scheda (100 nF e 10 µF).
Non usare un modulo a soli quattro segnali SPI con DAT1/DAT2 inaccessibili
senza verificarne lo schema e la compatibilità SDMMC.

Per FATFS/CSV e USB MSC usare una scheda FAT32, coerente con il firmware
TEST26. Il mount è differito al primo fix GNSS valido o alla richiesta USB.
In modalità MSC il PC possiede la scheda: espellere dal sistema operativo
prima del riavvio del dispositivo, come nel riferimento.

La USB via CH340/CP210x non fornisce Manager/MSC: serve la USB nativa
ESP32-S3 su GPIO19/20. VBUS e alimentazione del connettore devono seguire
lo schema della scheda usata, evitando alimentazioni in conflitto.

Il ricevitore deve essere **già configurato** per UBX NAV-PVT a 25 Hz e
230400 baud. La V0.40.5 configurava il GNSS in RAM; questa versione
TEST26 non lo fa e non modifica costellazioni o frequenza.

Non è stato assegnato un ADC batteria: GPIO4 è SU. Il menu mostra batteria
non disponibile; non si inventano percentuali senza un partitore definito.

## Comandi

- GIU: comportamento KEY originale (scorre in menu, lungo apre da Racing).
- OK: comportamento BOOT originale (breve conferma/apre, lungo torna indietro,
  almeno 3 secondi da Racing apre la conferma fine sessione).
- SU: scorre indietro nel menu.
- BACK: esegue l'azione indietro di BOOT lungo; da Racing non cambia stato.

Opzioni gara, circuiti, info GPS, sessioni, dettagli giro, salvataggio/scarto,
timeout automatico 30/60/90 s e doppia conferma USB conservano le logiche TEST26.

## Build e verifiche

```sh
cd firmware/rlcd-42-3-colori/GOATS_V0406_TEST26
python -m esphome config goats_42_color_v0406_test26.yaml
python -m esphome compile goats_42_color_v0406_test26.yaml
```

Richiede ESPHome e download delle dipendenze ESP-IDF/TinyUSB e dei font
Roboto Condensed. Nessun Wi-Fi, OTA o server web configurato.

Dalla root del repository:

```sh
python tests/rlcd_color/check_reference.py
g++ -std=c++17 -Wall -Wextra -Werror -I firmware/rlcd-42-3-colori/GOATS_V0406_TEST26/components/goats_st7306 tests/rlcd_color/test_pixel_pack.cpp -o /tmp/test_pixel_pack
/tmp/test_pixel_pack
```

Controlli di parità TEST26 e test C++ di packing/orientamento/colori ST7306
superati il 13/11/2026. Validazione ESPHome 2026.7.3 superata.
Compilazione e link ESP32-S3 superati con ESPHome 2026.7.3 ed ESP-IDF 5.5.5.
RAM statica: 161.747 byte (47,3%); applicazione: 687.611 byte (8,5% dello slot).
Queste misure non includono i picchi dinamici durante la registrazione.
Nessuna prova hardware, SD, USB o pista effettuata.

## Limiti ereditati

Allineare significa conservare anche i limiti di TEST26: il motore usa
`millis()` per i passaggi, ignora l'iTOW ricevuto come parametro e non
interpola temporalmente l'attraversamento. Le scritture e i possibili blocchi
SD restano quelli del riferimento; non sono dichiarati risolti riavvii o
problemi di prestazioni. Le sessioni e il protocollo Manager non vengono
convertiti in un nuovo formato. Questo porting va collaudato al banco
prima dell'uso in pista.
