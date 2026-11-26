# Verifica STEP3 — 26/11/2026

```sh
python tests/diag3_rc33_step3/run.py
esphome compile firmware/rlcd-42-3-colori/goats_42_diag3_rc33_step3.yaml
python tests/diag3_rc33_step3/graphics_check.py
python tests/diag3_rc33_step3/check_build.py
```

- UART/configuratore/parser/stabilita', motore giri, funzioni SPI e renderer
  confrontati con le basi DIAG3/STEP1/STEP2A. Il bridge Racing ha una sola
  sostituzione: CRC catalogo in cache, aggiornato su caricamento/modifica;
  le condizioni matematiche e temporali del motore non cambiano.
- Manager e store iniziano solo dopo la configurazione GPS e l'attach STEP1.
  L'unico metodo gps_poll_ e' ancora quello DIAG3. Nessuna NVS o flash nel
  callback PVT: verificato con stubs che falliscono se invocati da quel contesto.
- ASan/UBSan: crossing/settori/LAST/BEST/passo del core, PVT duplicati/checksum,
  burst, tre fix validi per AUTO con reset dopo fix invalido e blocco del cambio
  pista durante un giro. Traccia a passo simulato 40ms mentre USB non accetta
  scritture: tutti i campioni distinti validi attesi, senza perdite della coda.
- Controllo di memoria prima del nuovo catalogo; rifiuto MEMORY senza perdere
  quello precedente e ricaricamento da NVS dopo riavvio: verificati.
- Catalogo Manager persistente, GTRK_GET identico al payload inviato, CRC
  errato preserva il catalogo; un commit NVS fallito segnala STORAGE e
  preserva il catalogo RAM. Il mock NVS non dimostra atomicita’ fisica sotto
  interruzione di alimentazione durante la sostituzione del catalogo.
- Backend flash: solo partizione goatsfs; nessuna cancellazione automatica;
  recupero dopo riavvio, cancellazione con tombstone, CRC di record interrotto,
  memoria piena senza sovrascrittura, erase esplicito per singolo settore,
  ID riservati fuori dal parser e non riutilizzati dopo erase/riavvio.
- Chiusura da fermo e automatica dopo timeout RC3.3 60s, flush della coda e
  riarmo verificati. Il backend non scrive oltre 256 byte per iterazione.
- Test end-to-end con GTC3 builder reale del Manager Windows V5.4.15.20,
  client goats_test23_protocol.py per elenco/BURST4/CRC/download/delete e
  parser CSV reale: 301 punti, passi di 40ms, data/ora Europe/Rome e traccia
  libera riconosciuti. Elenco coerente dopo download, riavvio e cancellazione.
  Il file protocollo V5.4.15.19 ha lo stesso SHA256 della V5.4.15.20.
- Test del flusso SPI STEP2A rieseguiti sui metodi STEP3: identita' finestra
  completa/30000 byte, limite 2400 byte per blocco, pixel packing, ritorno
  diagnostica e BOOT breve/lungo; aggiunte le azioni REC/STOP >=3 secondi.
- Preprocessore e binario: un solo motore privato, un solo lettore UART,
  Canvas non registrato; USB serial JTAG e partizione collegati, setup/tick
  USB legacy, mount SD e TinyUSB/MSC assenti.
- ESPHome 2026.7.3 / Arduino 3.3.10 / ESP-IDF 5.5.5: compilazione riuscita.
  App 615579 byte, RAM statica 150559 byte, config_hash 0x4482559a.
- ZIP controllato per CRC/SHA256 e validazione dei due YAML dopo estrazione.

Non sono stati fatti test fisici ESP32/GPS/flash/USB con questo STEP3, ne'
una prova del Manager Windows contro la scheda. Il test usa il vero codice
client/firmware con backend simulati; non misura latenze/erase reali o jitter.
La grafica e il percorso GNSS restano quelli precedenti, ma il nuovo lavoro
USB/flash richiede collaudo della continuita' PVT e della coda sul dispositivo.
