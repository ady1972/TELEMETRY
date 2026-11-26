# GOATS 5″ transflettivo — GPS DIAG3 / V0.1.0

Nuovo diagnostico indipendente basato su **RLCD tricolore GPS DIAG3** del
branch `codex/gnss-diag3-stability`, commit
`1e73b8bd7bc1df0647569a8dd768909af2c4d345` (velocità ingrandita).
Usa la configurazione attiva del ricevitore DIAG3, il suo parser e i suoi
osservatori di stabilità. La precedente variante passiva MG902 DIAG-R1
rimane un progetto separato. Questo firmware non registra sessioni.

## Installazione

Estrarre lo ZIP direttamente nella cartella ESPHome. Tenere affiancati:

```text
goats_5_gps_diag3.yaml
GOATS_5_GPS_DIAG3/
  components/goats_diag3/...
  tests/...
  README.md
```

Compilare **goats_5_gps_diag3.yaml** e installare via USB UART/CH340C della
scheda. Non occorrono secrets, Wi-Fi, Manager, Home Assistant o microSD.
Il pacchetto include anche `bin/firmware.factory.bin`: immagine completa per
flash USB tramite ESPHome Web/esptool, offset **0x0**. Quel binario è per il
5″ VIEWE, non per RLCD/Guition. I log USB UART0 sono a 115200 baud.
La compilazione da YAML richiede Internet al primo download di font e dipendenze.

## Collegamenti necessari

Scheda VIEWE **UEDX80480050E-WB-B**, ESP32-S3, flash 16 MB, PSRAM octal 8 MB,
display RGB 800×480. Segnali UART a livelli compatibili con ESP32.

| Segnale | Collegamento |
|---|---|
| TX del ricevitore GPS | **GPIO17 del 5″** — RX ESP |
| RX del ricevitore GPS | **GPIO10 del 5″** — TX ESP |
| Massa | GND comune tra GPS, scheda e alimentazione esterna |
| Alimentazione GPS | Secondo le specifiche del modulo utilizzato |

**Entrambi i fili UART sono necessari**: DIAG3 invia la configurazione al GPS.
Collegare soltanto TX GPS → GPIO17 non permette di applicare la sequenza.
GPIO10 è il CS della microSD: **lasciare lo slot vuoto**. GPIO2 è dedicato
alla retroilluminazione del 5″ e non può essere usato come TX, come sulla RLCD.
Non collegare le uscite TX di due telemetrie contemporaneamente al RX del GPS.

## Gestione GNSS ripresa da DIAG3

- UART inizialmente a **38400**, buffer RX originale **16384 byte**.
- La stessa sequenza DIAG3 tenta 38400/9600/115200/230400 baud e termina
  con UART host a **230400**.
- Stessi **17 frame inviati**, stessi payload e checksum, stessi cinque
  aggiornamenti del baud host e **2430 ms di ritardi espliciti**.
- Configurazione VALSET **RAM**, senza scritture flash/BBR; stesse richieste
  delle costellazioni, SBAS, MAXSVS e messaggi UBX/NMEA della base.
- NAV-PVT richiesto a **25 Hz**, NAV-DOP/NAV-SAT ogni 25 epoche. Come DIAG3,
  alcune frasi NMEA restano richieste ogni 25 epoche.
- Unico lettore UART: `goats_m9n::poll`; parser originale e batch da 8 campioni.
- Nessun reset GPS, nuova scansione, poll o riconfigurazione periodica aggiunti.

La configurazione cambia lo stato RAM del ricevitore: questa è la differenza
voluta rispetto al precedente diagnostico passivo. La sequenza **non verifica
l'accettazione completa** di tutti i comandi; ACK/NAK e frequenza effettiva
sono osservabili. Il valore 25 Hz è una richiesta, non una misura presunta.
Il numero di satelliti non viene aumentato artificialmente.

## Schermata diagnostica unica

Pagina fissa, sfondo bianco e testo nero; aggiornamento ogni **1 secondo**.
Non servono tasti, touch o cambio pagina.

| Campo | Significato DIAG3 |
|---|---|
| VISTI | `numSvs` dell'ultimo NAV-SAT, satelliti elencati dal modulo; comprende anche canali C/N0=0 |
| USATI | `numSV` di NAV-PVT, satelliti usati nella soluzione |
| HDOP | hDOP da NAV-DOP, scala 0,01; non pDOP né metri |
| KM/H | Velocità NAV-PVT, mm/s × 0,0036, visibile con fix di posizione valido |
| FIX CONT / PERSI | Durata continua del fix valido e perdite del fix |
| BUCHI PVT / GAP MAX | Interruzioni >1500 ms e massimo intervallo di ricezione PVT |
| PVT Hz / PASSO GPS | Frequenza misurata e differenza iTOW con rollover settimana |
| ERR CK / RX / UBX | Checksum errati, byte ricevuti e frame UBX validi |
| ACK / NAK | Risposte positive/negative effettivamente osservate |
| ETA PVT / SAT / HDOP | Età dei tre tipi di dato; MAI se ancora assenti |
| UP / DRAW / ETA DRAW | Uptime e contatori software del rendering |

PVT/USATI scadono dopo 1500 ms; VISTI e HDOP dopo cinque secondi e diventano
`--`. Velocità `--` anche senza fix di posizione valido. Un fix solo tempo
viene indicato come tale e non abilita la velocità. Zero indica una misura
valida, non un valore sostitutivo. Le soglie e i contatori sono quelli DIAG3.
Il conteggio VISTI può differire dal vecchio DIAG-R1, che contava solo C/N0>0:
confrontare soprattutto USATI, FIX e freschezza dei dati.

## Adattamenti al 5″ e display

I due header GNSS cambiano **solo l'include dell'orologio**: da `Arduino.h`
a `goats_diag3_clock.h`. Il 5″ usa ESP-IDF come nel suo profilo RGB già
compilato; l'adattatore fornisce `::millis()` e `::delay()` tramite HAL ESPHome.
Parser, osservatore e interfaccia usano tutti lo stesso orologio. Codice dei
frame, parametri e ritardi restano identici. Gli hash originali sono in
`ORIGINE.json`, verificabili dal test senza rete.

GPIO RGB identici al precedente progetto 5″, **PCLK 32,4 MHz invertito**,
porch orizzontali 24/136/40 e verticali 2/21/37 (totale 1000×540).
PSRAM octal 80 MHz; cache 64 KB/linea 64 byte, esecuzione da PSRAM,
ISR RGB in IRAM. LVGL parziale, buffer 25%, rendering 33 ms, senza pausa idle.
Retroilluminazione GPIO2 PWM 1 kHz al **50%** dopo l'avvio.
Il controllo ogni 10 s riprende LVGL solo se effettivamente in pausa e scrive
nei log lo stato del rendering. Non sono introdotti Wi-Fi o OTA.

La soglia di avvio del configuratore resta 900 ms dalla sua inizializzazione.
Sequenza SPI ST7306, primo frame RLCD, NVS, laptimer, circuiti e tasti della
base non vengono importati: sono sostituiti dal display RGB e dalla pagina
unica. Non si dichiara parità dei tempi complessivi di boot o del backend UART
tra Arduino/RLCD e ESP-IDF/5″; la parità verificata riguarda sorgenti GNSS,
frame inviati, ritardi espliciti e comportamento del parser/osservatore.

## Verifica e collaudo

Test host, con g++ e Python 3:

```sh
python3 GOATS_5_GPS_DIAG3/tests/run.py
```

Il test verifica gli hash DIAG3 (normalizzando il solo include dell'orologio),
confronta la traccia trasmessa con una fixture generata dal sorgente RLCD
originale, esegue l'osservatore originale e il componente portato con
ASan/UBSan. Include avvio, frammentazione UBX, checksum, ACK/NAK, frequenza,
assenza di scritture successive al boot, dati scaduti, fix solo tempo,
interruzioni e rollover. `VERIFICHE.txt` riporta la compilazione ESPHome.

**Da collaudare sul dispositivo**: aggancio GNSS e stabilità del display.
Provare con il ricevitore già verificato su RLCD, entrambi i fili UART e stessa
posizione/antenna. Fotografare tutta la pagina dopo alcuni minuti all'aperto,
oppure conservare i log. La compilazione non conferma né il fix né l'assenza
del precedente oscuramento dello schermo.
