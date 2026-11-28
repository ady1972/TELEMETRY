# Verifica STEP3A LCD — 26/11/2026

```sh
esphome compile firmware/rlcd-42-3-colori/goats_42_diag3_rc33_step3a_lcd.yaml
python tests/diag3_rc33_step3a_lcd/run.py
python tests/diag3_rc33_step3a_lcd/check_build.py
```

- Tutti gli header del core/GNSS/store/USB, il renderer Racing, TTF e bitmap
  uguali allo STEP3. UART/logger/framework/partizioni invariati.
- controller_init_ eseguito su un osservatore SPI con lcd_data_swap false/true:
  sequenze identiche salvo un parametro 3A, da 0x11 a 0x01. Nessun cambio
  di BPS, comandi/tempi/tensioni/frame rate, MADCTL o pin.
- Funzioni pixel/region/poll/setup e trasferimento Racing confrontate con
  STEP3: identiche. Cambia il selettore opzionale della pagina di prova.
- Test C++ ASan/UBSan con i glyph realmente compilati: Racing LAP TIME/DELTA,
  font/freschezza/avvisi, packing, full-window SPI, limite 2400 byte/blocco,
  ritorno DIAG3/Racing. Nuova pagina di allineamento disegnata ed esportata
  dai byte trasmessi in simulazione.
- Preprocessore/ELF: un solo core/UART/controller, compensazione attiva nel
  main generato, pagina test disattiva nel factory, no SD/TinyUSB/MSC.
- Compilazione ESPHome 2026.7.3 / Arduino 3.3.10 / IDF 5.5.5 riuscita:
  app 616255 byte, RAM statica 150567 byte, config_hash 0xdf4a4ce2.
- Configurazioni Racing/DIAG3/test validate anche dopo estrazione dello ZIP;
  CRC/SHA256 del pacchetto controllati.

La verifica confronta comandi e bitmap; non simula la risposta del pannello,
il suo cablaggio o l'effetto fisico di XDE. L'efficacia sul disallineamento
richiede la foto/prova dello STEP3A. Non si dichiara risolto prima del collaudo.
Il firmware contiene una compensazione proposta in base al datasheet; non
contiene la modifica sperimentale dei font precedentemente preparata.

Le prove funzionali di telemetria/Manager dello STEP3 restano documentate
in GOATS_DIAG3_RC33_STEP3/VERIFICA.md. I relativi sorgenti sono invariati.
