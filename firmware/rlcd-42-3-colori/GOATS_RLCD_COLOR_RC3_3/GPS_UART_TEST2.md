# RC3.3 GPS UART TEST2 — ESPHome, senza tasti

La foto del primo test mostra UART impostata a 230400, RX 0 byte, UBX 0,
NAV-PVT 0 Hz, satelliti 0/0, nessun PVT e ACK/NAK 0. Quindi non sono stati
letti byte dalla UART: non basta modificare la decodifica NAV-PVT o attendere
il fix per spiegare quel contatore. La causa hardware/software non è ancora
accertata. L'utente non dispone del log seriale e dei pulsanti.

## Differenza corretta per la prova

La COLOR originale usa Arduino; questa RC3.3 usa ESP-IDF per conservare SD e USB
della RLCD. Nel backend ESP-IDF di ESPHome, `load_settings()` elimina e
reinstalla il driver UART. La precedente porta lo invocava a ogni passo di baud.
Il codice adesso usa `uart_set_baudrate()` sullo stesso numero UART scelto da
ESPHome, lasciando installati driver e buffer e conservando il routing GPIO.
Il valore nominale ESPHome viene aggiornato solo dopo il successo della API.

Questo è un intervento circoscritto sul cambio baud, **da collaudare**, non la
prova che il teardown causasse RX zero sul dispositivo dell'utente. Si leggono
anche baud effettivo hardware e codici errore, senza riconfigurare il ricevitore
nel loop. I 17 frame UBX, i quattro tentativi iniziali, il baud finale richiesto
230400 e le attese di 2430 ms rimangono quelli della COLOR V0.40.5. Nessuna
modifica a pin, costellazioni, NAV-PVT 25 Hz, parser, giri o formato CSV.

## Caricamento con ESPHome

Scaricare [i sorgenti TEST2](download/GOATS_RLCD_COLOR_RC3.3_GPS_UART_TEST2_SORGENTI.zip).
Estrarre lo ZIP e mantenere i tre YAML affiancati a `GOATS_RLCD_COLOR_RC3_3`.
Aprire **`goats_42_color_rc3_3_gps_uart_fix.yaml`**, compilare e installare via
USB con ESPHome, su ESP32-S3 da **16 MB**. Questo è il nuovo test; il file
`goats_42_color_rc3_3_gps_diag.yaml` è la precedente pagina diagnostica.

Dopo il flash spegnere completamente ESP e GPS, riaccendere, attendere circa
30 secondi e fotografare tutta la pagina **RC3.3 - GPS TEST2**. La pagina
compare automaticamente e resta visibile: nessun pulsante richiesto.

## Dati nuovi

- **U0/U1/U2**: numero periferica UART allocata da ESPHome, non il numero GPIO.
  I pin restano RX ESP GPIO1 e TX ESP GPIO2.
- **SET**: baud nominale configurato in ESPHome.
- **HW**: baud letto tramite API dal controller UART dell'ESP. Un piccolo
  scostamento dal nominale dovuto al divisore del clock è normale. Non indica
  direttamente il baud del ricevitore GPS.
- **POLL**: numero di chiamate al lettore GPS; deve crescere continuamente.
- **ERR x/y**: codice della API di applicazione del baud / codice della lettura
  hardware. Zero significa successo dell'API, non conferma di ricezione radio.
- **UPTIME**: secondi dall'avvio dell'ESP, visibili finché non arriva un PVT.

RX, UBX, NAV-PVT, SAT, FIX, OK, HDOP, CKERR e ACK/NAK mantengono il significato
spiegato in [DIAGNOSTICA_GPS.md](DIAGNOSTICA_GPS.md). I contatori ACK/NAK
non sono una conferma completa di tutti i comandi. La precedente richiesta
GPS non viene ripetuta automaticamente; nessun tentativo ciclico o reset.

## Verifiche software

I due rami del cambio baud (compatibilità generica e ESP-IDF) sono esercitati
con ASan/UBSan contro il configuratore COLOR originale: stessi 17 frame e
ritardi; avvii a 38400/9600/115200/230400, configurazione RAM e MSC senza scritture.
Sul ramo ESP-IDF simulato: zero reload del driver, buffer RX conservato, scelta
della periferica corretta, lettura baud, errori di set/get e cache nominale
non aggiornata se la API fallisce. Questi test non simulano un difetto reale
del silicio e non dimostrano da soli la causa del problema.

Il confronto ESPHome delle configurazioni risolte verifica che le due pagine
diagnostiche cambino solo renderer, nome descrittivo e commento rispetto al
firmware Racing. I 19 header del motore RC3.3 restano identici al riferimento;
layout Racing, font, driver display e intervalli restano congelati.
ESPHome 2026.7.3 / ESP-IDF 5.5.5: configurazione e compilazione **PASS**,
app 603.571 byte e RAM statica 164.515 byte. ZIP estratto e validato
separatamente, SHA-256 verificati. Prova sul dispositivo ancora necessaria.
