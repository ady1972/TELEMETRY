# DIAG3 + RC3.3 STEP2A — correzione trasferimento LCD

La foto dello STEP2 mostra blocchi di colonne spostati e testi frammentati.
L'anteprima software era corretta, ma non verificava la resa reale delle
finestre RAM parziali sul pannello ST7306. Il difetto osservato e' compatibile
con quel nuovo percorso di trasferimento; non viene attribuito al GPS o
alla definizione dei font. STEP2A elimina le finestre parziali.

## Correzione

Ogni immagine Racing modificata usa esattamente la stessa finestra completa
usata dalla DIAG3 funzionante: `2A:05..36`, `2B:00..C7`, quindi un solo `2C`
RAMWR con 30000 byte nel medesimo ordine. Non si cambiano MADCTL/orientamento,
packing dei pixel, font, layout, inizializzazione o tensioni del display.
Il corpo Racing resta quello RC3.3 introdotto nello STEP2.

Il flusso RAMWR e' suddiviso in 13 blocchi, ciascuno fino a 2400 byte
(4,8 ms di solo payload a 4 MHz). CS rimane basso e DC alto tra i blocchi:
le pause non aprono nuove finestre e non riavviano il puntatore RAM del LCD.
Il componente continua a leggere il GPS prima di ogni blocco. Non ci sono
altri proprietari SPI e la SD rimane esclusa. Un cambio pagina/modalita'
chiude prima l'eventuale flusso aperto e richiede una nuova immagine completa.

Se l'immagine e' identica all'ultima completata, non viene trasmessa.
Quando cambia, vengono inviati tutti i 30000 byte: non si saltano righe
nel mezzo del flusso. Il tempo di un frame dipende dalle pause del loop;
non si promettono 10 frame/s. Il trasferimento fisico non e' sincronizzato
con TE; refresh, leggibilita' e orientamento richiedono la nuova prova.

## Installazione ESPHome USB

Estrarre tutto, mantenendo i due YAML accanto a `GOATS_DIAG3_RC33_STEP2A/`.

- `goats_42_diag3_rc33_step2a.yaml`: avvio Racing, LAP TIME grande.
- `goats_42_diag3_rc33_step2a_diag.yaml`: avvio nella pagina DIAG3 con velocita'
  60 px; utile se il pulsante BOOT della scheda e' inaccessibile.

Il pacchetto comprende `bin/firmware.factory.bin`, compilato dal primo YAML,
immagine USB completa per ESPHome Web (offset 0x0 se richiesto).
`firmware.ota.bin` e' solo l'applicazione, non un'immagine completa.
Nessun Wi-Fi/OTA o aggiornamento Manager viene abilitato.

A firmware avviato: BOOT breve commuta Racing/DIAG3; BOOT premuto almeno
1,2 secondi e rilasciato commuta LAP TIME/DELTA in RAM. Non tenerlo premuto
all'accensione/reset: e' il pulsante del bootloader. Non servono tasti esterni.

Hardware invariato: ESP32-S3 N16R8, flash16MB. GPS TX -> GPIO1 ESP,
GPS RX <- GPIO2 ESP, massa comune. LCD CS10/DC9/RST8/MOSI11/CLK12, SPI4MHz.

## Cosa verificare

Controllare che Racing corrisponda alle anteprime: LAP TIME in alto,
settori S1-S2-S3 da sinistra a destra, delta/BEST a sinistra e velocita'
a destra, testi interi e leggibili. Poi controllare nella DIAG3 per alcuni
minuti PVT Hz, satelliti, HDOP, FIX CONT/PERSI/BUCHI e CORE che aumenta.

UART, configuratore/parser/stabilita' DIAG3 e motore STEP1 sono byte-identici.
Nessuno splash, SD, ADC batteria, archivi RC3.3 o Manager viene attivato.
L'icona batteria e' solo un contorno, non indica un livello di carica misurato.
Giri/sessione restano in RAM; senza circuiti salvati, AUTO e --:--.--- sono
normali. Il solo fix GPS non avvia il giro. Menu/circuiti/archivi verranno
integrati nei passi successivi.

DIAG3 e STEP1 hanno conferma hardware positiva; STEP2A e' compilato e
verificato via software ma deve ancora essere provato sulla scheda.
Le anteprime `preview/` sono simulazioni, compresa quella ricostruita dai
byte del flusso completo: non sono una misura della risposta del pannello.
