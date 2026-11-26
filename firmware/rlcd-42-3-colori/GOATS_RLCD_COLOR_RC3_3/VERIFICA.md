# Verifica COLOR RC3.3 — 26 novembre 2026

## Baseline e ambito

- Riferimento: RLCD monocromatico RC3.3 su `main`, commit
  `855954ed7c4b96e7f36ec8fffcd786c6c5973a07`.
- I **19 header applicativi** sono identici byte per byte a quelli RC3.3.
- Framework ESP-IDF/TinyUSB e logger identici al riferimento. UART modificata
  soltanto per il bootstrap GNSS V0.40.5 descritto sotto. Scheduling
  1 s / 10 ms / 5 s invariato, con il solo adattamento di arming ai quattro tasti.
- Pinout e sequenza comandi/reset/pixel packing ST7306 conservati dalla COLOR.
- V0.40.5, COLOR TEST26 e le versioni monocromatiche non modificate.
- Target confermato dall'utente: ESP32-S3 **16 MB**, nessuna PSRAM abilitata.

## Layout identico alla RC3.3

La prima bozza della PR conservava la vecchia disposizione COLOR. In seguito
alla correzione richiesta dall'utente, è stata sostituita con l'intera lambda
di rendering della RC3.3, comprendente Racing, menu, conferme, sessioni,
post-giro, Best Lap e USB. Il driver ora si occupa solo del trasporto dei pixel,
senza un renderer Racing alternativo.

Sono identici, per le schermate operative, coordinate, riquadri, posizioni delle etichette, dimensioni e
selezione dei font. Le sole differenze ammesse nel confronto sono:

- identità `COLOR RC3.3` e istruzioni dei quattro tasti;
- canale rosso nei quattro riempimenti relativi ai delta negativi;
- splash eliminato nella variante COLOR su richiesta dell’utente.

Il sensore batteria resta non disponibile sull'hardware senza partitore, ma
il suo riquadro/icona rimane nella posizione originale della RC3.3.

## Compilazione effettiva

- Validazione ESPHome 2026.7.3: **PASS**.
- Compilazione/link ESP32-S3, ESP-IDF 5.5.5: **PASS**.
- Applicazione: **610.831 byte**, 7,5% dello slot da 8.126.464 byte.
- RAM statica: **165.515 byte**, 48,4% dei 341.760 byte riportati dal linker.
  I picchi di RAM durante registrazione e trasferimento non sono misurati.
- Generati factory, app ed ELF. Il pacchetto USB contiene la factory da scrivere
  a **0x0**, esclusivamente per la scheda da 16 MB.
- La configurazione non include più il componente `image` né asset dello splash.
  Nessun errore di compilazione.
- Nessun firmware caricato automaticamente su un dispositivo.

## Test software

```sh
python tests/rlcd_color_gnss_config/run.py
python tests/rlcd_color_rc3/check_contracts.py
python tests/rlcd_color_rc3/run.py
python tests/rlcd_color/check_reference.py
python tests/rc2/run.py
# Con Python dell'ambiente ESPHome 2026.7.3:
python tests/rlcd_color_rc3/test_layout.py
```

Tutti **PASS**. Le suite storiche di acquisizione e sessioni sono state eseguite
nella stessa revisione funzionale: gli aggiornamenti successivi hanno
ricontrollato parità dei 19 header e delle schermate; è stato aggiunto soltanto
il bootstrap GNSS V0.40.5, con i test dedicati descritti sotto.

- Parità RC3.3 dei sorgenti, parser GNSS passivo, bootstrap UART attivo V0.40.5, scheduling,
  pinout, versione Info, assenza di PSRAM/ADC inventato/Wi-Fi/OTA.
- Date e ora italiana/DST, metadati persistenti, massima e media per giro,
  selezione BEST, preferenza DELTA/LAP TIME in NVS.
- Save/save/discard e nuovi passaggi sullo stesso traguardo senza riavvio,
  chiusura differita e scarto fallito che conserva la sessione.
- Suite storica: CSV 25 Hz, GSA3, recupero NVS, code, chiusura FAT, errori SD/NVS.
- Mapping di tutti i pixel ST7306 nei tre colori e pattern misti, limiti pannello.
- Driver reale con **AddressSanitizer e UndefinedBehaviorSanitizer**: finestre
  SPI nei limiti, nessun gruppo immutato/duplicato trasmesso, nessun gruppo
  cambiato perso e framebuffer uguale al contenuto inviato.
- Primo frame: una sola finestra completa. Frame identico: zero finestre e zero
  byte. Rettangolo stretto alto 200 righe: una finestra anziché 200.
- 120 sequenze pseudo-casuali e pixel distanti: solo i due gruppi cambiati
  vengono trasmessi, per un totale di 6 byte di pixel.

## Confronto dei layout e anteprime

`test_layout.py` confronta l'intera lambda COLOR con quella della RC3.3,
rimuovendo dal confronto lo splash del riferimento e normalizzando soltanto i testi di modello/tasti e i quattro riempimenti rossi.
Poi esegue i due renderer effettivi su host con la classe C++ **Font originale
di ESPHome**, glifi generati con `glyph_to_glyphinfo` e lo stesso TTF locale.
ASan e UBSan sono abilitati anche per questo test.

**397 scenari superati**: tutte le 17 pagine, sei posizioni del cursore, le due
modalità Racing, delta negativo/zero/positivo/non disponibile, post-giro,
lampeggio, Best Lap e USB. Vengono confrontati i comandi e gli ancoraggi di
disegno, le dimensioni dei font e i pixel logici normalizzando il canale rosso.
I pixel dei testi di modello/aiuto, volutamente differenti, sono esclusi dal
confronto delle rispettive fasce; i loro ancoraggi rimangono confrontati.

Anteprime native con valori simulati, prodotte dagli YAML effettivi:

- [LAP TIME](anteprime/lap.png)
- [DELTA](anteprime/delta.png)

Queste sostituiscono le anteprime con la vecchia disposizione COLOR. Non sono
foto del pannello. La classe Font rasterizza nativamente a 1 bit: nessuna
riscalatura orizzontale, interpolazione o riparazione dei tratti.

## Avvio senza logo — test aggiunto

- Configurazione priva di `image:`, riferimenti a `goats_splash_static`, timer
  `splash_started` e chiamate `it.image`. Asset eliminato dalla nuova variante.
- Il primo frame contiene già il riquadro principale Racing, senza chiamate
  al disegno dell'immagine, ed è trasmesso in una sola finestra da 30.000 byte.
- Con dati fermi, verificati istanti prima, durante e dopo la vecchia scadenza
  dei tre secondi: nessun logo, pagina vuota o cambio ritardato; nessuna
  ritrasmissione SPI aggiuntiva. Test sotto ASan/UBSan.
- Il test layout continua a confrontare le schermate operative della RC3.3.
- Il framebuffer viene ricomposto completamente anche senza lo splash. La
  rimozione evita di disegnare il logo, ma non identifica né certifica una
  soluzione del possibile residuo fisico del pannello. Nessuna prova hardware.

## Prove ancora richieste

- Avvio, resa dei colori e riduzione del refresh indesiderato sul vero ST7306.
- Leggibilità al sole, segni/punti, cambio modalità e menu.
- Sessioni consecutive con GPS e SD, salvataggio manuale/automatico, scarto,
  CSV, circuiti e trasferimento USB/MSC.
- Memoria dinamica e continuità dell'acquisizione sotto carico.

TE resta scollegato; non si dichiara sincronizzazione con la scansione del
pannello. I lampeggi Best Lap/post-giro rimangono intenzionali. I test host non
certificano la soluzione del difetto visivo né l'affidabilità in pista.
Nessuna prova hardware effettuata.

## GNSS V0.40.5: unica modifica funzionale alla base RC3.3

Baseline grafica/logica congelata: commit `c49e7423d4d07382700f4f806cf12117deb4326d`.
Il test `tests/rlcd_color_gnss_config/run.py` verifica **identità del rendering
YAML, dello scheduling, dei pulsanti, dei font, delle anteprime e di ogni file
del driver** con un manifest SHA-256. I 19 header applicativi restano identici
alla RLCD RC3.3. Si aggiunge solo `goats_m9n_cfg.h`, con il codice della COLOR
V0.40.5 adattato da Arduino.h a esphome/core/hal.h e delay qualificato.

Test ASan/UBSan PASS: identici 17 frame UBX e tempi della V0.40.5, checksum,
layer solo RAM, nessun CFG-CFG/reset, bootstrap da tutti e quattro i baud,
richieste NAV-PVT/DOP/SAT, NMEA e costellazioni. Due avvii normali ripetono
la configurazione; il ramo MSC non scrive al GNSS. Il test esegue la lambda
on_boot reale e verifica anche setup date, preferenze schermata e menu.

RX1/TX2, bootstrap 38400, buffer RX 16384; UART finale 230400. Attese esplicite
2430 ms. La configurazione finisce prima di iniziare il normale loop RC3.3.
Nessuna modifica ai messaggi durante la registrazione. La sequenza non verifica
ACK/NAK come nell'originale: la risposta reale del ricevitore, i 25 Hz e il fix
restano da collaudare. Nessuna misura o prova hardware effettuata.
