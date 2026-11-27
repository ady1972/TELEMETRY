# Verifica STEP3F BACKEND — 27/11/2026

```sh
esphome compile firmware/rlcd-42-3-colori/goats_42_diag3_rc33_step3f_backend.yaml
python tests/diag3_rc33_step3f_backend/modes.py
python tests/diag3_rc33_step3f_backend/backend.py
python tests/diag3_rc33_step3f_backend/run.py
python tests/diag3_rc33_step3f_backend/check_build.py
```

- Base STEP3E 8cd4ef4. Aggiunti STORE_ONLY/USB_ONLY; start backend accetta
  enable_store/enable_usb, entrambi true per default. Init/tick/PVT gated per
  servizio; REC/STOP locale abilitato solo con storage. Nessuna commutazione live.
- Parser/configuratore/stabilita' GNSS, core RC3.3, catalogo, protocollo USB,
  font, renderer, controller LCD e loop SPI invariati. Store cambia solo per
  i contatori RAM write_ops/id_commits; record/header/CSV invariati.
- Dispatcher: C++ ASan/UBSan, parser/core reali su 50 PVT senza fix e 500 con
  fix a 25 Hz in ognuno dei cinque profili; callback, AUTO, cattura UI e guardie
  di init/tick/REC verificate. Double esterni solo per contare le chiamate.
- Backend reale: parser/core/runtime/store/USB produttivi su modelli IDF di
  flash/NVS/USB. Cinque processi separati provano le due combinazioni nuove:
  nessuna installazione/lettura/scrittura USB quando disabilitato; nessuna
  partizione telemetria/scansione/prenotazione ID/scrittura quando store off.
  Fix da fermo: nessuna registrazione o scrittura flash; ID=1 solo con store.
- STORE_ONLY e FULL registrano e chiudono 101 punti a 25 Hz, D=0 e CSV valido;
  nessuna scrittura nel callback PVT, W uguale alle chiamate flash riuscite.
  USB_ONLY risponde al PING ma rifiuta REC/ERASE senza storage. Nessun erase
  automatico o comando al ricevitore aggiunto.
- Regressioni FULL con il test Manager originale: cataloghi/CRC/persistenza,
  AUTO, registrazione anche con USB scollegata, recovery, cancellazione e
  memoria piena. Client reale Windows V5.4.15.20: builder GTC3 e protocollo
  BURST4/list/download/delete/CRC/CSV passati contro il backend nuovo.
- Renderer, packing, BOOT, stream RAMWR completo e immutabile, requester,
  prova A/B senza traffico in A/byte identici in B e wrap millis passati.
  Tempi simulati di invio 63/255 ms: non benchmark o refresh fisico misurato.
- Preprocessore/ELF: una UART/controller/core privato, Canvas non registrato,
  niente SD mount/TinyUSB/MSC/setup USB legacy. Main post_fix_mode=3,
  diagnostica iniziale true, HPM false. Backend USB collegato per FULL ma
  avvio/tick esclusi dal profilo factory STORE_ONLY.
- ESPHome 2026.7.3 / Arduino 3.3.10 / IDF 5.5.5: build passata,
  app 617879 byte, RAM statica 150599 byte, config_hash 0x8d9c8b92.
- Altri tre YAML validati, non compilati in binari separati. Il confezionamento
  verifica CRC ZIP, SHA256 di ciascun file e i quattro YAML dopo estrazione.

Nessun collaudo fisico STEP3F. Il riscontro FULL con leggero sfarfallio non
identifica ancora la causa; resta da confrontare STORE_ONLY/USB_ONLY, tenendo
conto anche del diverso carico elettrico. Non viene dichiarato risolto il difetto.
