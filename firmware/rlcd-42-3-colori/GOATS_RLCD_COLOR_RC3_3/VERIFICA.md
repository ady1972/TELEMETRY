# Verifica COLOR RC3.3 — 26 novembre 2026

## Baseline e ambito

- Riferimento: RLCD monocromatico RC3.3 su `main`, commit
  `855954ed7c4b96e7f36ec8fffcd786c6c5973a07`.
- I **19 header applicativi di riferimento** sono conservati identici byte per
  byte a quelli RC3.3. Tra questi, `m9n_passive.h` resta solo come riferimento:
  la ricezione usa il parser COLOR e l'adattatore aggiunti senza modificare il motore.
- Framework ESP-IDF/TinyUSB e logger identici al riferimento. UART e ricezione
  usano la gestione GNSS V0.40.5 descritta sotto. Scheduling
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
- Applicazione: **611.803 byte**, 7,5% dello slot da 8.126.464 byte.
- RAM statica: **164.483 byte**, 48,1% dei 341.760 byte riportati dal linker.
  I picchi di RAM durante registrazione e trasferimento non sono misurati.
- Generati factory, app ed ELF. Il pacchetto USB contiene la factory da scrivere
  a **0x0**, esclusivamente per la scheda da 16 MB.
- La configurazione non include più il componente `image` né asset dello splash.
  Nessun errore di compilazione.
- Nessun firmware caricato automaticamente su un dispositivo.

## Test software

```sh
python tests/rlcd_color_gnss_config/run.py
python tests/rlcd_color_gnss_config/run_reception.py
python tests/rlcd_color_rc3/check_contracts.py
python tests/rlcd_color_rc3/run.py
python tests/rlcd_color/check_reference.py
python tests/rc2/run.py
# Con Python dell'ambiente ESPHome 2026.7.3:
python tests/rlcd_color_rc3/test_layout.py
```

Tutti **PASS**. Le suite storiche di acquisizione e sessioni sono state eseguite
nella stessa revisione funzionale: gli aggiornamenti successivi hanno
ricontrollato parità dei 19 header e delle schermate. L'ultima revisione ha
eseguito nuovamente tutte le suite COLOR sopra elencate (compresi salvataggio,
scarto e riarmo), aggiungendo il test della ricezione GNSS descritto sotto.
La suite storica `tests/rc2/run.py` era già passata e non è stata ripetuta.

- Parità RC3.3 del motore, ricezione e bootstrap UART COLOR V0.40.5, scheduling,
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
alla RLCD RC3.3. L'ambito funzionale modificato è esclusivamente il GNSS:
configuratore, ricezione e adattatore verso il motore RC3.3.

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


## Ricezione completa dalla versione provata — aggiornamento finale

Lo ZIP V0.40.5 allegato dall'utente è stato aperto e confrontato: **14 file su
14 identici byte per byte** alla copia V0.40.5 già archiviata. La nuova variante
usa il configuratore effettivamente chiamato da quel firmware e il suo parser
UBX completo, anziché ripristinare soltanto l'inizializzazione del ricevitore.

`run_reception.py` confronta il parser originale con la porta ESP-IDF,
ammettendo solo include HAL, qualifiche millis/delay e osservazione dei frame
validi/contatori. Il confronto runtime ASan/UBSan usa entrambi i parser reali
sugli stessi byte: stato, date, frequenza, campioni e tempi mappati coincidono.
Copre frammentazione byte per byte, checksum errati, recupero dopo payload
oltre 1024 byte, NAV-PVT corto, rumore/NMEA, NAV-DOP, NAV-SAT, raffica di 100
campioni, limite della coda a 64 e scadenze a 1,5/3 secondi.

Il test dell'adattatore verifica che tutti i 100 payload validi arrivino al
punto d'ingresso RC3.3 integri e in ordine, una sola volta; quelli corrotti o
corti non sono consegnati. Il conteggio satelliti segue il campo originale
NAV-SAT e HDOP è disponibile alla registrazione. Nessuna scrittura/configurazione
UART durante la ricezione. Le condizioni di eleggibilità dei campioni restano
nel motore RC3.3: l'adattatore non converte fix 2D in fix 3D né altera iTOW.
Il parser alternativo `m9n_passive.h` non è più incluso nello YAML; la funzione
`goats_m9n::configure` del parser COLOR non viene mai chiamata.

Questo verifica il software e la compilazione, non la ricezione radio reale.
Il buon funzionamento GPS confermato dall'utente riguarda lo ZIP originale;
la combinazione RC3.3 qui consegnata richiede ancora il collaudo hardware.
