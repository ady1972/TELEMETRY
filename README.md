# GOATS RT - Telemetria Kart

Sistema di telemetria e cronometraggio GPS per kart.

## Hardware
- Guition 4.3" ESP32-S3
- RLCD 4.2" ESP32-S3
- Ricevitore GNSS MG-902 / u-blox M9N
- Acquisizione GPS UBX a 25 Hz

## Firmware
- Guition: porting del motore RLCD TEST26
- RLCD: firmware di riferimento TEST26

## Sviluppo
- ESPHome
- Codex per analisi e modifiche ai sorgenti
- GitHub per versionamento e backup

## Regole
- Preservare sempre le versioni stabili.
- Non modificare i parametri GNSS senza autorizzazione.
- Compilare e testare ogni nuova versione.
