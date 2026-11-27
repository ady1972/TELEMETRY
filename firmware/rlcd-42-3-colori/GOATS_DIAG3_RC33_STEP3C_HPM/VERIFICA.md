# Verifica STEP3C HPM — 27/11/2026

```sh
esphome compile firmware/rlcd-42-3-colori/goats_42_diag3_rc33_step3c_hpm.yaml
python tests/diag3_rc33_step3c_hpm/run.py
python tests/diag3_rc33_step3c_hpm/check_build.py
```

- Base: STEP3B SMOOTH, commit dff75be. Sfarfallio segnalato dall'utente sulla
  STEP3B; nessun collaudo hardware della STEP3C effettuato dall'agente.
- Header GNSS/configuratore/core/catalogo/flash/USB e font identici alla STEP3B.
  Loop, polling, renderer Racing, flush, packing e tasto BOOT identici.
- La trace SPI dell'inizializzatore reale verifica che HPM aggiunga soltanto
  D8:80,E9 dopo sleep-out e sostituisca 39 con 38. B2:15 invariato.
  Nessun'altra variazione a tensioni o waveform. Il ramo LPM e' esattamente la
  sequenza precedente; test indipendenti anche su XDE e fast_display.
- Test C++ ASan/UBSan su renderer/packing/frame/input: entrambe le modalita'
  Racing, GPS fresco/scaduto, evento best, pagina prova, cancel e cambio pagina
  passati. Frame invariato saltato; 30000 byte e finestra identici alla DIAG3;
  13 blocchi <=2400 byte, CS mantenuto per l'intero stream.
- Requester rapido nativo ESPHome: avvio/arresto/cancel, rispetto della richiesta
  di un altro componente e rilascio a frame finito verificati. Modello di invio
  invariato STEP3B: 63 ms contro 255 ms con le pause standard (simulazione, non
  benchmark o misura del pannello).
- Preprocessore/ELF: un core privato, una UART/controller, Canvas non registrato,
  HPM e fast_display attivi, avvio Racing/LAP TIME; USB serial JTAG e partizione
  flash presenti, nessun SD mount, TinyUSB/MSC o setup USB legacy.
- Compilazione ESPHome 2026.7.3 / Arduino 3.3.10 / IDF 5.5.5 superata:
  app 616543 byte, RAM statica 150575 byte, config_hash 0x06313c99.
- YAML diag/test validati. Nel pacchetto vengono verificati CRC ZIP, SHA256 di
  ciascun file e configurazione dei tre YAML dopo estrazione.

HPM 51 Hz e' nominale da datasheet, non un refresh misurato. Il caricamento di
nuove immagini resta al massimo 8/s. Non viene dichiarato risolto lo sfarfallio
prima del riscontro fisico. Da verificare anche contrasto/colori, continuita'
GPS e consumo. La diagnostica conserva l'aggiornamento dei valori ogni secondo.
