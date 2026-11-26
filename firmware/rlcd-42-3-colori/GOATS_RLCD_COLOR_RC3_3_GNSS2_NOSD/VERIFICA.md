# Verifica RC3.3-GNSS2-NSD — 26/11/2026

```sh
COLOR_GNSS_NOSD=1 python tests/rlcd_color_gnss_diag2/run.py --all
python tests/rlcd_color_gnss_diag2/test_nosd.py
python tests/rlcd_color_gnss_diag2/check_audit.py
esphome compile firmware/rlcd-42-3-colori/goats_42_color_rc3_3_gnss2_nosd.yaml
COLOR_GNSS_NOSD=1 python tests/rlcd_color_gnss_diag2/check_build.py
esphome compile firmware/rlcd-42-3-colori/goats_42_color_rc3_3_gnss2_nosd_audit.yaml
```

Prove software:

- Quattordici header RC3.3 conservati identici; cinque interfacce esclusivamente
  SD/tracce/MSC sostituite. Renderer/font/SPI/tasti invariati; rimosso solo
  l'intervallo da un secondo che montava la SD. Polling GNSS 10 ms invariato.
- GNSS C++ ASan/UBSan: stessi comandi e ritardi, parser equivalente, singolo
  lettore, inoltro raw una volta, burst/errori/time-out, clock con epoche
  diverse, riacquisizione e wrap a 32 bit: PASS.
- Vera grafica RC3.3 e rasterizzatore font ESPHome: 397 scenari corrispondenti.
- Clock/data/DST, modalita' persistente, riepiloghi, salva/scarta e riarmo
  del cronometraggio senza riavvio: PASS.
- Facade NOSD con ASan/UBSan: nessun mount, scrittura, errore ripetuto o
  reboot MSC; comandi SD non disponibili; data sessione e clock mantenuti.
- Confronto configurazioni ESPHome risolte: AUDIT conserva tutto il runtime
  NOSD, esegue anche la lambda Racing originale e usa getter UART di sola lettura.
- Racing normale: compilazione ESPHome 2026.7.3 / Arduino 3.3.10 / IDF 5.5.5
  superata; app 525171 byte, RAM statica 125387 byte.
- Preprocessore e binario reale: clock del parser isolato da main; nessuna
  funzione di mount SDMMC/FatFS, inizializzazione card o TinyUSB MSC collegata.
- AUDIT: compilazione superata; app 527263 byte, RAM statica 125387 byte.
  Stesso controllo del preprocessore e assenza di simboli SD/MSC nel binario: PASS.
  Ulteriori misure e provenienza riportate in BUILD.json nello ZIP.
- Pacchetto verificato per CRC ZIP, SHA256 e validazione degli YAML estratti.

La prova DIAG2 dell'utente e' positiva. Il completo precedente aveva GPS
assente secondo l'utente; il suo firmware era ricompilato dallo YAML, versione
ESPHome non ancora nota. Questa variante senza SD e' da collaudare sulla scheda.
