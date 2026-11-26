# GOATS V0.40.5 GPS DIAG2

Diagnostico derivato direttamente dallo ZIP funzionante
`GOATS_V0405_BOOT_FAST_FONT_TEST_2026_11_03.zip` fornito dall'utente.
Non deriva da RC3.3 o da AUTOSCAN. Il riferimento V0.40.5 rimane invariato.

## Correzione rispetto a DIAG1

Il video dell'utente mostra frame UBX e NAV-PVT intorno a 25 Hz, senza fix,
ma anche alternanza tra comunicazione OK e flusso interrotto con ETA enorme.
Il parser globale usa `::millis()` Arduino (esp_timer), mentre la schermata in
namespace esphome risolveva `millis()` in `esphome::millis()` (tick FreeRTOS).
La sottrazione tra epoche diverse poteva andare in underflow e segnalare
un'interruzione falsa. DIAG2 usa esplicitamente `::millis()` nella schermata,
lo stesso orologio dei contatori. Il loop e i comandi GPS restano invariati.
DIAG1 e il suo pacchetto rimangono conservati per confronto.

Il video conferma che arrivano dati; non dimostra ancora continuita' a lungo
termine o acquisizione del fix. La correzione elimina la falsa segnalazione
causata dal confronto temporale, senza mascherare interruzioni reali.

## Installazione ESPHome via USB

Estrarre tutto lo ZIP. Tenere affiancati:

- `goats_42_v0405_gps_diag2.yaml`
- cartella `GOATS_V0405_GPS_DIAG2`

Compilare e installare lo YAML con ESPHome via USB, come la V0.40.5.
In alternativa lo ZIP contiene `bin/firmware.factory.bin` gia' compilato per
l'installazione completa con ESPHome Web via USB. Usare offset 0x0 se lo strumento
richiede l'indirizzo; `firmware.ota.bin` e' solo l'applicazione e non va scritta
come immagine completa. Non occorrono Manager, rete, microSD, tasti o log seriale.

Hardware: ESP32-S3-DevKitC-1 N16R8 (flash 16 MB, PSRAM 8 MB), RLCD ST7306
tricolore 300x400 fisici / 400x300 logici. Come nell'originale non viene
aggiunta una configurazione PSRAM: questo firmware usa la RAM interna.

Cablaggio invariato: TX GPS -> GPIO1 ESP; RX GPS <- GPIO2 ESP; GND comune.
LCD CS10/DC9/RST8/MOSI11/CLK12. Non spostare i fili e non collegare i tasti.

## Che cosa rimane identico

- Sezioni YAML `esp32` (comprese partizioni), `logger`, `uart` e componente.
- Framework Arduino; logger INFO con baud seriale 0.
- UART ESPHome, senza assegnare una diversa periferica hardware.
- RX1/TX2, 38400 iniziali, buffer 16384, formato predefinito 8N1.
- Intero `goats_m9n_cfg.h`, byte per byte: tentativi 38400/9600/115200/230400,
  poi 230400; costellazioni e SBAS; UBX/NMEA; richiesta 25 Hz in RAM.
- Sequenza di avvio LCD, prima schermata originale, inizializzazione NVS e
  chiamata del configuratore nello stesso ordine e con gli stessi ritardi.
- Unico lettore UART e parser UBX originali; criteri di fix, coda campioni,
  mappatura iTOW, timeout e passaggio dei campioni al laptimer.
- Driver ST7306, font bitmap e componenti laptimer/NVS/catalogo.

Come nel file originale, la versione delle dipendenze non e' fissata nello YAML.
La compilazione consegnata usa ESPHome 2026.7.3, Arduino 3.3.10 e IDF 5.5.5.
Non conosciamo la versione ESPHome usata per il binario originale dell'utente:
conservare framework e sorgenti non garantisce un binario identico a quello.

## Che cosa viene aggiunto

Dopo la configurazione appare automaticamente **V0.40.5 GPS DIAG2**. La prima
schermata da gara e' visibile brevemente durante l'avvio per preservare la
sequenza originale. La diagnostica si aggiorna ogni secondo, senza premere tasti.
Ogni 8 secondi si alternano i soli dettagli centrali; gli indicatori principali
restano sempre visibili. Nessuna scansione, interrogazione aggiuntiva, cambio
pin, reset GPS o riconfigurazione automatica dopo l'avvio.

- **BAUD ESP**: valore software impostato nella UART ESPHome, non lettura dal GPS.
- **RX BYTE / UBX / UP**: byte letti, frame UBX con checksum valido, uptime.
- **PVT Hz / TOT / ETA**: frequenza osservata dal parser originale, totale
  NAV-PVT completi e tempo dall'ultimo. ETA 0 con TOT 0 significa mai ricevuto.
- **SAT usati/visibili, FIX, HDOP**: valori del parser V0.40.5.
- **ACK / NAK**: risposte effettivamente lette dopo la configurazione.
  La loro assenza non dimostra un rifiuto: il configuratore originale non legge
  durante i cambi baud e alcune risposte possono andare perse. Non si dichiara
  accettata una configurazione soltanto perche' e' stata trasmessa.
- **CKERR / LEN**: checksum UBX errati / frame con lunghezza oltre 1024 byte,
  scartati anche dal parser originale. Il contatore UBX non conta NMEA.
- **ULTIMO ACK/NAK e UBX**: classe/ID esadecimali; ad esempio 06/8A e' VALSET.
- **DOP / SAT / GAP MAX**: messaggi NAV-DOP/NAV-SAT e massimo intervallo tra
  NAV-PVT osservati dall'ESP. Il gap include i tempi del loop/display; non e'
  una misura diretta dell'intervallo di soluzione interno del ricevitore.
- **LAT / LON**: ultime coordinate decodificate; controllare FIX prima di usarle.
- **PRIMI BYTE**: primi 12 byte letti dopo la configurazione, esadecimali.

Gli indicatori distinguono nessun byte, byte senza UBX valido, UBX senza PVT,
PVT interrotto, comunicazione senza fix e comunicazione con fix. Un ricevitore
senza fix puo' comunque comunicare correttamente.

## Prima prova

Lasciare acceso circa un minuto. Fotografare la schermata con RX, UBX, PVT,
SAT/FIX e i contatori ACK/NAK/errori. Se possibile fotografare anche l'altra
pagina automatica con GAP MAX. Nessun log seriale necessario.

Compilazione e prove software descritte in `VERIFICA.md`.
La comunicazione sul cablaggio dell'utente resta da collaudare.
