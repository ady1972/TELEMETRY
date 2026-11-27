# Verifica software GPS AUTOSCAN 0.1.0 — 26 novembre 2026

- ESPHome 2026.7.3, Arduino 3.3.10, ESP-IDF 5.5.5: configurazione,
  compilazione e link per ESP32-S3 16 MB **PASS**.
- Applicazione: **287.095 byte**; RAM statica: **84.707 byte**.
  Memoria dinamica e risposta elettrica non misurate sul dispositivo.
- Bus GPS diretto HardwareSerial, senza componente UART ESPHome. Logger seriale
  e log del framework disabilitati per lasciare pulite tutte le UART in prova.
- Motore di ricerca con **ASan/UBSan PASS**: enumerazione delle 396 combinazioni,
  attraversamento completo senza dati, gestione aperture fallite, checksum UBX
  e NMEA, echo non accettato, pacchetti corrotti e lunghi, NMEA nota/frammentata,
  modulo silenzioso interrogabile, link senza fix, verifica di continuità,
  errori UART, perdita/riaggancio su altro baud e rollover millis.
- Ogni frame trasmesso nei test è verificato indipendentemente: checksum,
  payload vuoto e sole classi MON-VER / CFG-PRT / CFG-RATE. Non ci sono comandi
  di configurazione, salvataggio o reset del ricevitore.
- Tabella partizioni esplicita con regione NVS uguale alla precedente RC3.3.
- ZIP estratto e validato autonomamente; componenti, font e partizioni locali;
  integrità ZIP e SHA-256 verificati.
- Nessun flash automatico, test hardware o in pista effettuato. I test simulano
  il trasporto per esercitare la ricerca, non certificano i profili elettrici.

Per riprodurre dal repository:

```sh
python tests/gnss_autoscan/run.py
esphome config firmware/rlcd-42-3-colori/goats_42_gnss_autoscan_v010.yaml
esphome compile firmware/rlcd-42-3-colori/goats_42_gnss_autoscan_v010.yaml
```

Il test sul dispositivo deve confermare titolo corretto, avanzamento delle
prove e aggancio con pacchetti validi. Documentare separatamente un link RX
stabile, la conferma TX/RX e il fix satellitare.
