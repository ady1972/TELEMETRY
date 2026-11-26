# Verifica software — 26/11/2026

- Copia di riferimento nel repository confrontata con lo ZIP allegato: identica.
- `python tests/gnss_v0405_diag/run.py`: PASS, C++ con AddressSanitizer e UBSan.
  Confronta configuratore, sezioni YAML, funzioni di avvio/lettura e dipendenze;
  confronta esecuzione di originali e variante con UART simulata: stessi 17 frame
  trasmessi, stessi cinque baud host, stessi ritardi (2430 ms espliciti).
  Confronta stato e coda campioni su ogni passo di un flusso NAV-PVT frammentato,
  burst oltre 64 campioni, senza/con fix, DOP/SAT, errori e timeout.
  Verifica ACK/NAK, checksum errati, lunghezze eccessive, nessuna lettura/scrittura
  UART extra e contatori/timeout al riavvolgimento del timer a 32 bit.
- `esphome config firmware/rlcd-42-3-colori/goats_42_v0405_gps_diag1.yaml`: PASS.
- `esphome compile` sullo stesso YAML: PASS con ESPHome 2026.7.3,
  Arduino 3.3.10 / ESP-IDF 5.5.5. UART gestita da ESPHome come nel riferimento;
  le dipendenze attuali usano il backend UART ESP-IDF anche sotto Arduino.
- App 374643 byte; RAM statica 87927 byte.
- Controllo a video di un esempio rasterizzato con i font bitmap originali:
  pagina diagnostica entro 400x300; nessun collaudo del pannello fisico.
- L'archivio consegnato viene controllato con CRC ZIP, SHA256 e validazione
  ESPHome dei sorgenti estratti.

Queste prove non dimostrano che il GPS risponda sulla scheda dell'utente,
che accetti tutte le impostazioni richieste o che raggiunga realmente 25 Hz.
Non e' stato possibile eseguire un collaudo hardware.
