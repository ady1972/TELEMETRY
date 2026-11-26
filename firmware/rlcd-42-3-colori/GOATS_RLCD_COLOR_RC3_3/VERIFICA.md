# Verifica COLOR RC3.3 — 26 novembre 2026

## Baseline e ambito

- Riferimento: RLCD monocromatico RC3.3 su `main`, commit
  `855954ed7c4b96e7f36ec8fffcd786c6c5973a07`.
- I **19 header applicativi** sono identici byte per byte a quelli RC3.3.
- UART, framework ESP-IDF/TinyUSB e logger identici al riferimento. Scheduling
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

Sono identici coordinate, riquadri, posizioni delle etichette, dimensioni e
selezione dei font. Le sole differenze ammesse nel confronto sono:

- identità `COLOR RC3.3` e istruzioni dei quattro tasti;
- canale rosso nei quattro riempimenti relativi ai delta negativi.

Il sensore batteria resta non disponibile sull'hardware senza partitore, ma
il suo riquadro/icona rimane nella posizione originale della RC3.3.

## Compilazione effettiva

- Validazione ESPHome 2026.7.3: **PASS**.
- Compilazione/link ESP32-S3, ESP-IDF 5.5.5: **PASS**.
- Applicazione: **625.675 byte**, 7,7% dello slot da 8.126.464 byte.
- RAM statica: **165.555 byte**, 48,4% dei 341.760 byte riportati dal linker.
  I picchi di RAM durante registrazione e trasferimento non sono misurati.
- Generati factory, app ed ELF. Il pacchetto USB contiene la factory da scrivere
  a **0x0**, esclusivamente per la scheda da 16 MB.
- Avviso noto: formato storico `image:` deprecato da ESPHome, ancora valido
  nella versione usata; nessun errore di compilazione.
- Nessun firmware caricato automaticamente su un dispositivo.

## Test software

```sh
python tests/rlcd_color_rc3/check_contracts.py
python tests/rlcd_color_rc3/run.py
python tests/rlcd_color/check_reference.py
python tests/rc2/run.py
# Con Python dell'ambiente ESPHome 2026.7.3:
python tests/rlcd_color_rc3/test_layout.py
```

Tutti **PASS**. Le suite storiche di acquisizione e sessioni sono state eseguite
nella stessa revisione funzionale: questa correzione successiva cambia soltanto
il rendering e i test delle schermate, con parità dei 19 header ricontrollata.

- Parità RC3.3 dei sorgenti, parser GNSS passivo, configurazione UART, scheduling,
  pinout, versione splash/Info, assenza di PSRAM/ADC inventato/Wi-Fi/OTA.
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
normalizzando soltanto i testi di modello/tasti e i quattro riempimenti rossi.
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
