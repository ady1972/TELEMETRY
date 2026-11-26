# GOATS GPS AUTOSCAN 0.1.0 — ESPHome, RLCD a colori

Firmware diagnostico **indipendente** per ESP32-S3 da **16 MB** e display
ST7306 tricolore. Nasce per individuare il collegamento MG902/u-blox che funziona
con la COLOR V0.40.5 ma non con le precedenti integrazioni RC3.3.

Il firmware usa direttamente **HardwareSerial di Arduino**, senza il bus UART
ESPHome, il laptimer, SD o il protocollo Manager. Tutte le operazioni sono
automatiche; non servono tasti, log seriale o connessioni di rete.

## Cosa cerca e come si adatta

| Parametro ESP | Prove automatiche |
|---|---|
| Periferica UART | 1, 0, 2 |
| Baud | 230400, 38400, 9600, 115200, 57600, 19200, 4800, 460800, 921600, 2400, 1200 |
| Formato a 8 bit | 8N1, 8N2, 8E1, 8O1, 8E2, 8O2 |
| Polarità RX | Normale e invertita |
| Protocolli riconosciuti | UBX e NMEA con checksum valido |

In totale **396 combinazioni**. Il programma adatta baud, parità, stop e polarità
della seriale dell'ESP ai parametri trovati, mantenendo il GPS sui fili esistenti.
UART0/1/2 sono periferiche interne: **non sono nuovi numeri GPIO**.

Ogni prova ascolta per circa 2,1 secondi e scarta brevemente i byte di confine
dopo la riconfigurazione. Dopo 1,2 secondi prova anche una interrogazione UBX
MON-VER di sola lettura, utile se il modulo non invia spontaneamente dati.
Le prove iniziano dopo una attesa di avvio di 1,5 secondi.

Un primo checksum valido avvia la verifica, senza dichiarare ancora successo.
Servono almeno cinque pacchetti validi, distribuiti su almeno quattro secondi,
senza nuovi errori di decodifica/UART e con continuità dei messaggi. Un'eco dei
poll inviati non conta come risposta GPS. Un burst isolato non basta se il
flusso resta poi assente oltre la soglia prevista.

Quando l'aggancio è verificato, la scansione si ferma e mantiene quel profilo.
Se il flusso scompare, riprova prima la configurazione nota e poi riparte dalla
ricerca. **La mancanza di fix satellitare non fa ripartire la scansione** se
continuano ad arrivare messaggi validi.

Le interrogazioni al ricevitore sono esclusivamente letture **MON-VER,
CFG-PRT corrente e CFG-RATE**. Permettono di identificare versione, baud/formato,
maschere protocollo e periodo di navigazione, quando supportate dal modulo.
Nessun comando VALSET, CFG-CFG, reset, cambio costellazioni o salvataggio flash/BBR.
Il diagnostico non forza il GPS a 230400/25 Hz: prima trova e misura il suo stato
reale. Le impostazioni adattate sono quelle dell'ESP; al riavvio ricomincia la ricerca.

La polarità invertita è una prova di ricezione: in quel profilo non vengono
inviati poll, poiché la polarità del filo TX non è deducibile da quella RX.
Il formato a 8 bit copre il trasporto UBX; non si provano 5/6/7 bit o velocità
arbitrarie fuori dall'elenco. Il flow control rimane disattivato per il
collegamento esistente a due fili.

## Collegamenti invariati

| Funzione | ESP32-S3 |
|---|---|
| TX GPS → RX ESP | **GPIO1** |
| RX GPS ← TX ESP | **GPIO2** |
| GND GPS / LCD | GND comune |
| Display CS / DC / RST | GPIO10 / GPIO9 / GPIO8 |
| Display MOSI / SCLK | GPIO11 / GPIO12, 4 MHz |
| Display TE | Scollegato |

Mantenere le alimentazioni del progetto funzionante. La ricerca non scambia
fisicamente TX e RX e non usa altri GPIO. Nessuna SD o pulsantiera richiesta.

## Installazione con ESPHome

Scaricare [il progetto completo ESPHome](download/GOATS_GPS_AUTOSCAN_V0.1.0_ESPHOME.zip)
e tenere affiancati:

```text
goats_42_gnss_autoscan_v010.yaml
GOATS_GNSS_AUTOSCAN_V010/
```

Aprire **`goats_42_gnss_autoscan_v010.yaml`**, compilare e installare via USB.
La pagina deve intitolarsi **GPS AUTOSCAN 0.1.0**. Al primo build ESPHome scarica
le normali dipendenze Arduino; font e componenti del progetto sono locali.

Accendere il dispositivo con il GPS collegato e lasciare lavorare la scansione.
Con parametri comuni l'aggancio può avvenire nelle prime prove. Se resta in
ricerca, **un giro senza pacchetti validi richiede circa 14 minuti**; una
verifica parziale può allungarlo. Il contatore PROVA/CICLO mostra l'avanzamento.
La ricerca prosegue su nuovi giri se necessario.

Quando appare uno stato STABILE, fotografare le **due pagine** che si alternano
ogni otto secondi. Se non aggancia al termine di un giro, fotografare la pagina
con RX, UBX/NMEA, errori, FRONTI e numero di prova/ciclo. Una foto immediata
all'avvio può ancora mostrare soltanto i valori iniziali.

## Lettura della schermata

- **SCANSIONE AUTOMATICA**: profilo in prova, nessun collegamento confermato.
- **VERIFICA COMUNICAZIONE**: almeno un pacchetto riconosciuto, verifica in corso.
- **LINK RX/TX STABILE**: ricezione verificata e almeno due risposte MON-VER
  correlate ai poll di questa prova. È una prova del percorso TX/RX.
- **RX STABILE - TX NON CONFERMATO**: messaggi ricevuti correttamente, ma nessuna
  conferma sufficiente delle interrogazioni. Può essere un flusso NMEA senza
  protocollo UBX in ingresso; non dimostra da solo un filo TX interrotto.
- **FLUSSO PERSO - RECUPERO**: nessun messaggio valido recente, recupero in corso.

SET/HW sono baud richiesto e letto dalla UART dell'ESP; piccoli arrotondamenti
del divisore sono normali. RX ATT è la prova corrente; TOTALE è cumulativo.
UBX/NMEA, errori e BUONI si riferiscono al profilo in prova. Gli errori di
comunicazione resettano la finestra di stabilità, ma i contatori storici restano
visibili. Echo indica frame di poll ritornati identici, esclusi dalla verifica.

La frequenza **PVT** è misurata da NAV-PVT con iTOW distinti. Un collegamento
NMEA può essere stabile con PVT 0 Hz. SAT/FIX derivano da NAV-PVT, GGA/RMC
quando disponibili: link seriale e fix sono condizioni diverse.

**FRONTI** conta transizioni osservate sul GPIO1 durante la ricerca; il monitor
viene disattivato quando arrivano byte per ridurre il carico. È un indizio di
attività elettrica, non una validazione di baud/protocollo. Zero fronti da solo
non prova un guasto. MON ERR riguarda il monitor GPIO, non il ricevitore.
UART ERR raccoglie errori hardware, parità, framing e overflow rilevati dal driver.
I primi byte HEX aiutano a distinguere un flusso leggibile da dati non identificati.

La seconda pagina mostra i parametri letti dal GPS; porta GPS e UART dell'ESP
sono numerazioni di due dispositivi distinti. Valori non restituiti dal modulo
restano vuoti/zero. Il test non promette di riconoscere protocolli proprietari
diversi da UBX/NMEA.

## Struttura e verifiche

- Motore di scansione e parser testabili su host, separati da HardwareSerial.
- Budget di lettura e buffer bounded; ricezione non bloccante nel ciclo.
- Schermo a 1 Hz con un frame completo già composto, senza immagine di avvio.
- Tabella partizioni identica alla precedente RC3.3: stesso indirizzo NVS.
- Progetti COLOR/RC3.3 precedenti conservati; nessun Wi-Fi, OTA o scrittura SD.

I test ASan/UBSan coprono tutte le combinazioni, checksum, echi, corruzione,
NMEA nota e frammentata, assenza fix, modulo silenzioso interrogabile, errori
UART, perdita/riaggancio, cambio baud dopo riavvio e overflow di millis.
Sono test software; il collegamento elettrico e l'aggancio reale vanno collaudati.
