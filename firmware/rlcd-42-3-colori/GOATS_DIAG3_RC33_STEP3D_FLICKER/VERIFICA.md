# Verifica STEP3D FLICKER — 27/11/2026

```sh
esphome compile firmware/rlcd-42-3-colori/goats_42_diag3_rc33_step3d_flicker.yaml
python tests/diag3_rc33_step3d_flicker/run.py
python tests/diag3_rc33_step3d_flicker/check_build.py
```

- Base STEP3C 5ea147f; default HPM disabilitato dopo il riscontro negativo
  dell'utente. Test A/B distinto dalla Racing normale; nessuna nuova frequenza,
  tensione o waveform LCD introdotta rispetto al fallback LPM gia' provato.
- Header GNSS, core, cataloghi, flash, USB, font e renderer Racing invariati.
  Setup, pixel packing, invio a blocchi, cancel e BOOT invariati. Nel loop
  resta il polling GPS/USB/store prima di ogni blocco; un ramo separato serve
  il test A/B, senza cambiare il ramo Racing esistente.
- Trace C++ dell'inizializzatore reale verifica la stessa sequenza LPM STEP3B,
  scelta XDE, fast_display e ramo HPM preesistente. Factory configurato LPM.
- Test C++ ASan/UBSan con vere funzioni flicker_draw/tick/racing_draw/flush:
  A non invia nessun comando o byte dopo il primo frame; B invia gli stessi
  30000 byte ogni 125 ms simulati. Verificati il passaggio A/B/A, il completamento
  del frame immutabile prima del cambio fase, la pausa durante DIAG, il wrap
  di millis e il ritorno al renderer Racing. Nessun comando di cambio modo,
  oscillator/reset/display-off durante i tick di prova.
- Test su renderer originale, GPS fresco/scaduto, entrambe le Racing, best lap,
  finestra/packing, flusso completo uguale alla DIAG3, frame invariati saltati,
  13 blocchi <=2400 byte e BOOT passati. Requester rapido avviato/rilasciato
  correttamente, rispettando eventuali richieste di altri componenti.
- Il modello SPI/scheduler conserva 63 ms di invio rapido contro 255 ms con
  pause standard; e' simulazione, non benchmark fisico. Le preview A/B derivano
  dai pixel del flusso simulato e non rappresentano la resa ottica del pannello.
- Preprocessore/ELF: un core privato/UART/controller, Canvas non registrato,
  USB serial JTAG e partizione flash, niente setup USB legacy, SD mount,
  TinyUSB o MSC. Main: flicker_test true, lcd_high_power false.
- Build ESPHome 2026.7.3 / Arduino 3.3.10 / IDF 5.5.5 superata:
  app 617215 byte, RAM statica 150591 byte, config_hash 0x2ad2316d.
- YAML Racing e DIAG validati, non compilati in binari separati. Il factory
  incluso e' compilato dallo YAML principale del test A/B. Packaging con CRC
  ZIP, SHA256 di ogni file e validazione dei tre YAML dopo estrazione.

Non e' stato fatto un nuovo collaudo fisico STEP3D. Non viene dichiarato risolto
lo sfarfallio; e' richiesto il riscontro dell'utente su A, B oppure entrambe.
Il test ferma soltanto le scritture LCD in A: la scansione interna del pannello,
GPS, USB e telemetria continuano, con possibili differenze di carico elettrico
fra A e B. Un eventuale effetto non identifica da solo il componente difettoso.
