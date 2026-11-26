# DIAG3 + RC3.3 STEP2 — schermata Racing

Il 26/11/2026 l'utente ha confermato che la DIAG3 e' «perfetta» e che il GPS
continua a funzionare nello STEP1. Questo progetto aggiunge la Racing a quella
base, conservando separatamente le due versioni collaudate.

## Cosa cambia

La pagina Racing deriva dal corpo di disegno di `firmware/rlcd-42/goats_rlcd_rc3_3.yaml`:
400x300, tempo giro grande in alto, settori interni, delta e BEST a sinistra,
velocita' a destra, GPS/HDOP/circuito nella barra inferiore. Conserva anche la
modalita' DELTA grande, l'inversione dei valori negativi, LAST LAP e NEW BEST LAP.
Posizioni, bordi, testi, scelta dei font e tempi degli avvisi restano RC3.3.
Si usano Roboto Condensed Bold 1bpp nelle stesse tredici dimensioni, inclusi
72/78/82 px, da TTF locale incluso. Nessun ingrandimento dei bitmap DIAG3.

Il disegno passa attraverso un adattatore ESPHome che scrive nello stesso
framebuffer DIAG3. L'adattatore non e' registrato come componente/display:
non esiste un secondo proprietario dello SPI, dei pin o dell'aggiornamento.
L'inchiostro ON del renderer RC3.3 viene mappato al nero del driver tricolore.
Non viene disegnato uno splash.

La batteria mostra soltanto il contorno originale: non si abilita un ADC o
si ipotizza un collegamento del divisore. L'icona vuota significa **livello
non misurato**, non batteria scarica.

## GPS e fluidita'

UART RX1/TX2, 8N1, buffer 16384, configuratore e parser, osservatore DIAG3,
consumer e motore RC3.3 dello STEP1 rimangono identici. Configurazione RAM
230400 baud / richiesta 25 Hz, stessi comandi e ritardi della base funzionante.
Il vecchio poll UART resta l'unico lettore. I NAV-PVT validati alimentano lo
stesso motore una sola volta; il rendering legge soltanto lo stato.

Un'immagine viene composta al massimo ogni 100 ms e solo dopo aver completato
quella precedente. Lo SPI invia esclusivamente le righe fisiche cambiate,
con un massimo di 16 righe / 2400 byte per iterazione (4,8 ms di solo payload
a 4 MHz). Il GPS viene letto prima di ciascun blocco. Il tempo reale di un
frame dipende dalle righe cambiate e dal ciclo ESPHome; non si promettono 10
frame/s o assenza di refresh visibili senza prova hardware. Non vengono
trasmessi frame intermedi prima di aver finito di comporre l'immagine in RAM.
L'aggiornamento fisico avviene comunque a blocchi, senza sincronizzazione TE.

La pagina DIAG3 e' mantenuta: satelliti visti/usati, HDOP, velocita' a 60 px,
frequenza PVT, fix continuo, perdite e riga CORE. Conserva il refresh DIAG3
originale a 1 s; il trasferimento differenziale riguarda la Racing.

## Installazione ESPHome USB

Estrarre tutto. Tenere i due YAML accanto a `GOATS_DIAG3_RC33_STEP2/`.

- `goats_42_diag3_rc33_step2.yaml`: avvio normale in Racing, LAP TIME grande.
- `goats_42_diag3_rc33_step2_diag.yaml`: stesso codice, avvio nella DIAG3.
  Utile se BOOT non e' accessibile; non serve un pulsante esterno.

In ciascun YAML si possono impostare `start_in_diagnostics` e `delta_screen`.
Il binario factory incluso e' compilato dal primo YAML, quindi parte in Racing.
`bin/firmware.factory.bin` e' l'immagine completa per USB/ESPHome Web, offset
0x0 se richiesto dallo strumento. `firmware.ota.bin` e' solo l'applicazione,
non l'immagine completa. Non viene introdotto Wi-Fi/OTA o aggiornamento Manager.

Hardware invariato: ESP32-S3 N16R8 / flash16MB; GPS TX -> GPIO1 ESP,
GPS RX <- GPIO2 ESP, massa comune. LCD CS10/DC9/RST8/MOSI11/CLK12, 4MHz.

A firmware avviato, **BOOT della scheda (GPIO0)** permette:

- pressione breve: Racing <-> DIAG3;
- pressione di almeno 1,2 secondi e rilascio: LAP TIME <-> DELTA in RAM.

Non tenere BOOT premuto durante accensione/reset: e' il pulsante del bootloader.
Non occorre saldare i quattro tasti. I menu RC3.3 e i loro comandi arriveranno
in un passo successivo; non si attiva il vecchio menu COLOR.

## Prova sulla scheda e limiti

Controllare prima Racing: GPS usati/visti e HDOP devono aggiornarsi, velocita'
coerente, nessuna permanenza di splash o dati della pagina precedente.
Passare a DIAG3 (o compilare lo YAML diagnostico) e confrontare PVT Hz,
FIX CONT / PERSI / BUCHI PVT con STEP1 per alcuni minuti; CORE deve crescere.
Inviare una foto della Racing e della diagnostica dopo la prova.

Con nessun circuito salvato, AUTO e --:--.--- sono normali: il fix GPS da solo
non avvia un giro. Per cronometrare serve un traguardo nel catalogo esistente.
Come STEP1, sessione/giri restano in RAM. Menu, gestione circuiti, archivi,
Manager, SD e ADC batteria non vengono attivati. La NVS originale della DIAG3
rimane presente nella sequenza di avvio; non si aggiungono accessi per campione.

Le immagini in `preview/` sono anteprime software a pixel nativi, con dati
simulati e glyph effettivamente compilati: non sono foto o prove hardware.
Compilazione e test software superati; STEP2 resta da collaudare sulla scheda.
