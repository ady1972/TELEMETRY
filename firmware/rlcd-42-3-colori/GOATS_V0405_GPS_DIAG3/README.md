# GOATS V0.40.5 GPS DIAG3 — fix e stabilita'

Diagnostico standalone derivato dalla **DIAG2** che l'utente ha confermato
con comunicazione e fix attivi. La versione Racing e' sospesa durante questa
prova. Nessun componente RC3.3, microSD, TinyUSB o Manager viene importato.

## Installazione ESPHome via USB

Estrarre tutto e tenere affiancati:

- `goats_42_v0405_gps_diag3.yaml`
- cartella `GOATS_V0405_GPS_DIAG3`

Aprire lo YAML in ESPHome e installare via USB come la DIAG2.
Lo ZIP include anche `bin/firmware.factory.bin`, immagine completa gia'
compilata per ESPHome Web via USB (offset 0x0 se richiesto dallo strumento).
`firmware.ota.bin` contiene soltanto l'applicazione, non l'immagine completa.
Non occorre il Manager. Nessun Wi-Fi o OTA e' stato introdotto.

Hardware: ESP32-S3-DevKitC-1 N16R8, flash 16 MB; ST7306 tricolore.
Cablaggio invariato: TX GPS -> GPIO1 ESP, RX GPS <- GPIO2 ESP, GND comune.
Display CS10/DC9/RST8/MOSI11/CLK12. Nessun tasto o microSD necessario.
PSRAM non richiesta. Lo YAML conserva anche la tabella partizioni DIAG2.

All'avvio compare brevemente il primo frame originale della V0.40.5,
per mantenere la sequenza provata; poi resta la pagina **GPS DIAG3 - STABILITA**.
Nessuna alternanza delle schermate e nessun tasto richiesto. Aggiornamento a 1 s.
La velocita' e' in caratteri nativi da 60 px, con etichetta KM/H separata e
punto decimale allineato alla base; satelliti e HDOP rimangono a 28 px.

## Valori sempre visibili

| Campo | Origine e significato |
|---|---|
| VISTI | Numero di satelliti elencati da UBX NAV-SAT; non un conteggio ricavato dalla potenza del segnale |
| USATI | numSV di NAV-PVT, satelliti usati nella soluzione; e' il dato utile da distinguere dai soli satelliti visti |
| HDOP | hDOP di NAV-DOP, scala originale 0.01; non pDOP e non una misura in metri |
| KM/H | Velocita' al suolo di NAV-PVT, convertita da mm/s come nella DIAG2 |
| FIX 2D / 3D / GNSS+DR | Tipo di soluzione e flag gnssFixOK; tempo-only e DR-only non sono indicati come posizione valida |
| PVT Hz / ETA | Frequenza osservata dal parser originale e tempo dall'ultimo NAV-PVT |
| FIX CONT | Durata della sequenza corrente di fix di posizione validi, dal primo all'ultimo PVT valido |
| PERSI | Passaggi da fix di posizione valido a non valido oppure scaduto; il primo periodo senza fix non incrementa il contatore |
| BUCHI PVT | Interruzioni oltre 1500 ms dopo che era arrivato almeno un NAV-PVT; una sola conta per interruzione |
| GAP MAX | Massimo intervallo tra ricezioni NAV-PVT sull'ESP, compreso il tempo del loop e del display |
| PASSO GPS | Differenza iTOW degli ultimi due NAV-PVT, con rollover della settimana gestito |
| ERR CK | Frame UBX scartati per checksum errato |
| RX / UBX / UP | Byte ricevuti, frame con checksum valido e uptime |
| ETA SAT / ETA HDOP | Eta' dell'ultimo NAV-SAT e NAV-DOP, per verificare che i valori siano aggiornati |

VISTI e HDOP diventano `--` se mai ricevuti o piu' vecchi di cinque secondi.
USATI e PVT diventano `--` se NAV-PVT e' piu' vecchio di 1500 ms; velocita'
`--` anche senza posizione valida. Uno zero di velocita' indica invece una
misura valida a 0 km/h. Nessun valore di default viene presentato come fresco.
I contatori ripartono dall'accensione; le nuove statistiche sono passive e in RAM.

A 25 Hz il passo iTOW atteso e' 40 ms. La frequenza Hz usa una finestra di circa
un secondo e puo' oscillare; GAP MAX include l'accodamento UART e l'aggiornamento
LCD, quindi un gap di ricezione piu' lungo non dimostra da solo che il GPS abbia
saltato epoche. BUCHI PVT pari a zero significa nessuna interruzione oltre 1.5 s,
non dimostra assenza di ogni singolo pacchetto perso. Il passo non assume che
il ricevitore abbia accettato i 25 Hz: frequenze effettive diverse sono osservate.

## Prima valutazione

Lasciare acceso all'aperto con cielo libero per alcuni minuti. Verificare
che VISTI, USATI e HDOP siano aggiornati, che il tipo di fix sia esplicito e
che FIX CONT cresca senza incrementi di PERSI/BUCHI PVT. Per la velocita',
un breve spostamento permette di vedere le variazioni in km/h.
Fotografare o filmare l'intera pagina; non servono log seriali.

## Cosa resta identico alla DIAG2

`goats_m9n_cfg.h`, parser `goats_ubx_m9n_ak97_full.h`, UART, logger,
framework Arduino, buffer, pin e partizioni sono conservati. Stessi 17 frame,
cinque cambi baud host tramite load_settings(), 2430 ms di ritardi espliciti,
richiesta 230400/25 Hz in RAM, stesse costellazioni e messaggi UBX/NMEA.
Nessuna nuova interrogazione, scansione, reset o tentativo di riconfigurazione.
Il codice non verifica l'accettazione completa dei comandi da parte del GPS.

Sequenza di boot, primo frame LCD, inizializzazione NVS di base e funzione
originale gps_poll_ della DIAG2 rimangono invariati. Sono conservati i file
storici COLOR che quel diagnostico gia' utilizzava; non si tratta del porting
Racing RC3.3. Cambiano la pagina finale e un osservatore passivo chiamato sui
frame gia' validati, piu' il controllo di scadenza nel loop. Il parser e la pagina
usano lo stesso orologio Arduino ::millis(), come nella DIAG2 corretta.

La DIAG2 originale rimane conservata. La base ha riscontro hardware positivo;
questa nuova pagina e le statistiche DIAG3 sono da verificare sul dispositivo.
Prove software in `VERIFICA.md`.

## Riscontro utente successivo

Il 26/11/2026 l'utente ha confermato «la diag3 e' perfetta». Questa versione
viene quindi conservata come riferimento funzionante per l'integrazione RC3.3.
La conferma non sostituisce il collaudo delle successive varianti STEP.
