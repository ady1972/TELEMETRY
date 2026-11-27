# Verifica STEP3E POSTFIX — 27/11/2026

```sh
esphome compile firmware/rlcd-42-3-colori/goats_42_diag3_rc33_step3e_postfix.yaml
python tests/diag3_rc33_step3e_postfix/modes.py
python tests/diag3_rc33_step3e_postfix/run.py
python tests/diag3_rc33_step3e_postfix/check_build.py
```

- Base STEP3D 22c08ed. Nuovo dispatcher di avvio/tick/REC con tre profili;
  default schema FULL per compatibilita', YAML principale GPS_ONLY esplicito.
- Header GNSS/configuratore/stabilita', core, cataloghi, backend flash e USB,
  font e renderer RC3.3 identici a STEP3D. Inizializzatore LCD invariato.
  Il ramo FULL conserva ordine e chiamate del runtime precedente.
- Test C++ ASan/UBSan del vero nuovo dispatcher con parser M9N e core reali:
  tre processi distinti, ciascuno riceve 50 NAV-PVT senza fix e 500 con fix a
  25 Hz, attraverso la vera funzione gps_poll_ e una UART simulata.
  GPS_ONLY: fix e flusso validi, C=0, nessun attach/cattura core.
  CORE_ONLY: C=550 e 500 validi, AUTO riconosce il circuito; FULL delega gli
  ingressi al backend. Nessuna configurazione UART o scrittura al ricevitore
  aggiunta dal dispatcher. Duplicati iTOW, checksum errato e coda legacy verificati.
- Le funzioni esterne di avvio/tick/REC di storage/Manager nel test dispatcher
  sono contatori sostitutivi: verificano che siano invocate solo in FULL.
  Parser, contatori, callback e engine RC3.3 sono reali. Il backend completo e'
  identico al precedente, non e' dichiarato ricollaudato fisicamente.
- Il solo fix a velocita' zero non avvia un giro nei test. I profili ridotti
  non eseguono REC/STOP anche richiamando il comando. La lettura NVS del
  catalogo all'avvio rimane nel setup originale; la telemetria non viene cancellata.
- Regressioni native su renderer, pixel packing, input/BOOT, frame immutabile,
  finestra e 30000 byte uguali alla DIAG3, 13 blocchi <=2400 byte, requester
  rapido e wrap millis passate. Prova A/B preservata: nessun comando/dato
  dopo il primo frame di A e byte identici a ogni reinvio in B.
- Modello SPI/scheduler invariato: 63 ms rapidi contro 255 ms con pause standard,
  simulazione e non benchmark del dispositivo. Preview da pixel simulati.
- Build e preprocessore/ELF: una UART/controller/core privato, Canvas non
  registrato; nessun SD mount/TinyUSB/MSC/setup USB legacy. Il backend USB e'
  ancora collegato per FULL ma l'avvio e il tick sono esclusi in GPS_ONLY.
  main generato: post_fix_mode 0, diagnostica iniziale true, HPM false.
- ESPHome 2026.7.3 / Arduino 3.3.10 / IDF 5.5.5: compilazione principale passata;
  app 617567 byte, RAM statica 150591 byte, config_hash 0x4891f208.
- Altri tre YAML validati, non compilati in binari separati. CRC ZIP, SHA256
  di ciascun file e validazione dei quattro YAML estratti nel confezionamento.

Non e' stato fatto un test fisico STEP3E. Serve prima il riscontro in GPS_ONLY
con fix reale. I risultati fra profili possono essere influenzati anche dal
carico elettrico: non viene dichiarata individuata la causa o risolto il difetto.
