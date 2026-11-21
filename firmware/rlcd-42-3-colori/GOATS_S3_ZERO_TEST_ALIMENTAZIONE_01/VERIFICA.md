# Verifica — TEST ALIMENTAZIONE 01

Data: 21 novembre 2026. Nessun flash o test elettrico eseguito.

## Sorgente

- Base richiesta dalla issue #33: `codex/rlcd-42-tricolore-v0405`,
  commit `36d98107c10df7a72d3ccf9497027dedacfd8d87`.
- Branch diagnostico: `codex/issue-33-s3-zero-power-test`.
- V0.40.5 e V0.40.6 TEST26 non modificate.

## Controlli e compilazione effettivi

- `esphome config goats_s3_zero_test_alimentazione_01.yaml`: **PASS**.
- `esphome compile goats_s3_zero_test_alimentazione_01.yaml`: **PASS**,
  ESPHome 2026.7.3, ESP-IDF 5.5.5, ESP32-S3.
- RAM statica: **83.219 byte**, 24,4% dei 341.760 byte riportati dal linker.
  I picchi dinamici e la corrente assorbita non sono misurati.
- Applicazione: **315.839 byte**, 17,2% dello slot da 1.835.008 byte.
- `sdkconfig`: flash **4 MB**, USB Serial/JTAG attivo, PSRAM disabilitata.
- Binario per primo flash: `firmware.factory.bin`, immagine combinata da
  scrivere a **offset 0x0**. L'output denominato `firmware.ota.bin` dal sistema
  di build non implica un servizio OTA: questo progetto non ne configura uno.

## Test del driver reale su host

Eseguire dalla cartella del progetto:

```sh
python tests/run.py
```

Richiede Python 3 e `g++`. ASan e UBSan abilitati.

**PASS**:

- Sequenza di inizializzazione, mapping RBW, rotazione, rasterizzatore e font
  corrispondono al riferimento V0.40.5. Il controllo di parità necessita della
  cartella originale affiancata; nello ZIP autonomo viene saltato esplicitamente.
- Tutti i 120.000 pixel controllati per bianco, nero e rosso, oltre a un pattern
  misto decodificato indipendentemente; coordinate fuori pannello non scrivono.
- Primo frame con zero senza fix o periferiche; impulso reset LCD di 200 ms e
  ritardi controller originali 400/200 ms; trasferimento SPI di 30.000 byte con
  finestra completa 0x05..0x36 / 0..199.
- Contatore da timer monotono a 64 bit: campioni 1, 2, 60 secondi, oltre 49 giorni
  e valore a dieci cifre; rendering del tempo atteso e ripartenza da zero.
- Cause di reset accensione, software e brownout mostrate dal codice reale
  usando un backend ESP-IDF simulato.
- Configurazione priva di UART, Wi-Fi, OTA, SD, tasti e PSRAM.

Questi test simulano GPIO, SPI e reset ESP: non attestano la risposta del
pannello, la precisione del refresh reale o la stabilità dell'alimentazione.

## PDF e consegna

Due PDF di due pagine, con tabelle dei GPIO e schemi a blocchi:

- `documentazione/COLLEGAMENTI_TEST_ALIMENTAZIONE_01.pdf`: Zero 4 MB,
  display, MG902 come carico, multimetro, prova A/B e primo flash.
- `documentazione/COLLEGAMENTI_RLCD_42_COLOR_TEST26.pdf`: firmware completo
  da 16 MB, display, GNSS passivo, pulsanti, SDMMC, pull-up e USB nativa.

PDF generati con ReportLab; controllati testo entro i margini, due pagine per
file, riferimenti cliccabili e anteprime renderizzate. Generatore incluso.
Pinout del progetto completo ricontrollato su YAML e header SD del branch base.

Lo ZIP sorgenti contiene YAML e cartella di supporto affiancati, font locali,
README, questa verifica, test e i due PDF. Non include cache o credenziali.
Lo ZIP per primo flash contiene immagine factory, istruzioni e SHA-256.

## Da eseguire al banco

- Conferma della specifica variante Zero da 4 MB e del pinout LCD.
- Compatibilità VCC a 3,3 V della specifica scheda MG902.
- Prova A/B a freddo, tensioni, continuità del contatore, eventuali riavvii,
  colori e causa reset dopo l'aggiunta del carico.
- Nessuna dichiarazione di problema elettrico risolto: i risultati sono da
  annotare nella tabella del README/PDF.
