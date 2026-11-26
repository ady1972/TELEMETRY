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

## Compilazione effettiva

- Validazione ESPHome 2026.7.3: **PASS**.
- Compilazione/link ESP32-S3, ESP-IDF 5.5.5: **PASS**.
- Applicazione: **869.623 byte**, 10,7% dello slot da 8.126.464 byte.
- RAM statica: **165.555 byte**, 48,4% dei 341.760 byte riportati dal linker.
  I picchi di RAM durante registrazione e trasferimento non sono misurati.
- Generati immagine combinata factory, immagine app ed ELF. Nel pacchetto USB
  si consegna la factory da scrivere a **0x0**, per la scheda da 16 MB.
- Unico avviso di configurazione: formato `image:` storico deprecato da
  ESPHome, ancora valido per questa versione; nessun errore di compilazione.
- Nessun firmware caricato automaticamente su un dispositivo.

## Test software

```sh
python tests/rlcd_color_rc3/check_contracts.py
python tests/rlcd_color_rc3/run.py
python tests/rlcd_color/check_reference.py
python tests/rc2/run.py
```

Tutti **PASS**.

- Parità RC3.3 dei sorgenti, parser GNSS passivo, configurazione UART, scheduling,
  pinout, versione splash/Info, assenza di PSRAM/ADC inventato/Wi-Fi/OTA.
- Date e ora italiana/DST, metadati persistenti, massima e media per giro,
  selezione BEST, preferenza DELTA/LAP TIME in NVS.
- Save/save/discard e nuovi passaggi sullo stesso traguardo senza riavvio,
  richiesta di chiusura differita e scarto fallito che conserva la sessione.
- Suite storica: CSV 25 Hz, GSA3, recupero NVS, code, chiusura FAT, errori SD/NVS.
- Mapping di tutti i pixel ST7306 nei tre colori e pattern misti, limiti pannello.
- Driver reale e nuovo renderer eseguiti su host con **AddressSanitizer e
  UndefinedBehaviorSanitizer**: finestre SPI nei limiti, nessun gruppo immutato
  o duplicato trasmesso, nessun dato cambiato perso, frame uguale a quello inviato.
- Primo frame: una sola finestra completa. Frame identico: zero finestre e zero
  byte. Rettangolo stretto alto 200 righe: una finestra anziché 200.
- 120 sequenze pseudo-casuali di cambiamenti, aggiornamenti distanti, passaggi
  LAP TIME/DELTA, post-giro lampeggiante e pagina statica.
- Bounds dei glifi, segni e decimali, controllo che il numero dei pixel disegnati
  corrisponda esattamente ai bitmap nativi, fallback e troncamento UTF-8.

Il test di regressione delle sessioni condiviso ora accetta anche una cartella
firmware completa; il suo comportamento sulle versioni storiche rimane testato.

## Refresh e anteprime

Il caso simulato modifica insieme tempo, velocità e delta. Confronto sullo
stesso framebuffer finale:

| Metodo | Byte di pixel trasmessi |
|---|---:|
| Vecchio inviluppo sinistra/destra per ogni riga | 3.084 |
| Nuovi gruppi effettivamente modificati | 1.998 |

Sono dati di payload, esclusi comandi SPI. Non sono misure di velocità reale
né di flicker sul pannello. Il test verifica che i gruppi immutati fra aree
distanti non vengano più riscritti; il controller fisico non è emulato.

Anteprime dal renderer C++ effettivo, a risoluzione nativa, con valori simulati:

- [LAP TIME](anteprime/lap.png)
- [DELTA](anteprime/delta.png)

Controllati dimensioni/posizione delle cifre e dei punti nei riquadri. Nessuna
riscalatura orizzontale, interpolazione del raster o riparazione dei tratti.

## Prove ancora richieste

- Avvio, resa dei colori e assenza di refresh indesiderati sul vero ST7306.
- Leggibilità al sole, segni/punti, cambio modalità e menu.
- Sessioni consecutive con GPS e SD, salvataggio manuale/automatico, scarto,
  CSV, circuiti e trasferimento USB/MSC.
- Memoria dinamica e continuità dell'acquisizione sotto carico.

TE resta scollegato; non si dichiara sincronizzazione con la scansione del
pannello. I lampeggi Best Lap/post-giro configurati rimangono intenzionali.
La compilazione e i test host non certificano la soluzione del difetto visivo
osservato né l'affidabilità in pista. Nessuna prova hardware effettuata.
