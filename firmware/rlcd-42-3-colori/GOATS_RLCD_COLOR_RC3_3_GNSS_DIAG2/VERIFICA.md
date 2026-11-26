# Verifica RC3.3-GNSS2 — 26/11/2026

Comandi dalla radice del repository, con Python dell'ambiente ESPHome:

```sh
python tests/rlcd_color_gnss_diag2/run.py --all
esphome config firmware/rlcd-42-3-colori/goats_42_color_rc3_3_gnss_diag2.yaml
esphome compile firmware/rlcd-42-3-colori/goats_42_color_rc3_3_gnss_diag2.yaml
python tests/rlcd_color_gnss_diag2/check_build.py
```

Esiti:

- 19 header RC3.3 identici; lambda display, font, SPI, pulsanti e intervalli
  applicativi invariati rispetto al porting tricolore precedente.
- UART e logger confrontati con lo YAML funzionante V0.40.5/DIAG2.
- Corpo del configuratore identico al riferimento; parser identico salvo
  contatori passivi DIAG2 e callback del frame validato.
- C++ con AddressSanitizer/UBSan: stessi 17 frame trasmessi, cinque cambi baud
  host e ritardi; attesa iniziale; singolo lettore; stesso stato del parser;
  NAV-PVT frammentati, senza/con fix, burst, errori, frame corti, timeout,
  riacquisizione e timer a 32 bit; nessun comando runtime aggiuntivo.
- Bridge realmente usato dalla RC3.3 eseguito nel test: payload NAV-PVT
  originale consegnato esattamente una volta, coda secondaria svuotata,
  dati pubblici coerenti e timestamp con epoche Arduino/ESPHome differenti.
- Confronto delle vere lambda grafiche con il rasterizzatore font ESPHome:
  397 scenari Racing/menu/modalita', ancoraggi e pixel logici corrispondenti
  alla RC3.3, con le sole differenze preesistenti di modello/aiuti/rosso.
- Test del core RC3.3 su data/DST, clock, modalita' persistente, riepiloghi
  e ciclo salva/salva/scarta con riarmo senza riavvio: PASS.
- Configurazione e compilazione ESPHome 2026.7.3, Arduino 3.3.10,
  ESP-IDF 5.5.5: PASS. App 622675 byte; RAM statica 164211 byte.
- Preprocessore del compilatore reale: parser/configuratore presenti soltanto
  nel componente GNSS; macro di compatibilita' del clock soltanto in main.
- Flag USB reali: override privato alla sola libreria Arduino; nessun secondo
  proprietario dei callback MSC. Tabella partizioni compilata identica
  alla factory RC3.3 precedentemente consegnata.
- ZIP: CRC, manifest SHA256 e validazione ESPHome dopo estrazione.

La foto DIAG2 dell'utente conferma comunicazione/fix del diagnostico.
Questa integrazione completa deve ancora essere provata sul dispositivo;
nessun collaudo fisico di display, SD/USB, sessioni o giri e' dichiarato.
