# GOATS RT - Telemetria Kart

Sistema di telemetria e cronometraggio GPS per kart.

## Hardware
- Guition 4.3" ESP32-S3
- RLCD 4.2" ESP32-S3
- RLCD 4.2" ST7306 a tre colori: rosso, nero e bianco
- Display transflettivo 5" RGB 800x480, ESP32-S3, non touch
- Ricevitore GNSS MG-902 / u-blox M9N
- Acquisizione GPS UBX a 25 Hz

## Firmware
- Guition: porting del motore RLCD TEST26
- RLCD: firmware di riferimento TEST26
- [5 pollici transflettivo](firmware/5%20pollici%20transflettivo/README.md):
  progetto ESPHome 0.1.0 con acquisizione GNSS passiva e test card display opzionale;
  cronometraggio, Racing, sessioni e microSD ancora da implementare.
- [RLCD 4.2 a tre colori](firmware/rlcd-42-3-colori/README.md):
  V0.40.5 BOOT FAST + FONT TEST, driver ST7306, font piccoli nativi 16px,
  motore giri/settori/delta, quattro pulsanti e storage giri NVS.
  Versione sperimentale importata dall'archivio del 03/11/2026;
  compilazione e funzionamento hardware non verificati per la V0.40.5 originale.
  La nuova [V0.40.6 TEST26](firmware/rlcd-42-3-colori/GOATS_V0406_TEST26/README.md)
  allinea GNSS, logiche e menu a TEST26 e aggiunge microSD SDMMC e USB nativa;
  mantiene la Racing e i font del display tricolore. Da collaudare su hardware.

## Sviluppo
- ESPHome
- Codex per analisi e modifiche ai sorgenti
- GitHub per versionamento e backup

## Regole
- Preservare sempre le versioni stabili.
- Non modificare i parametri GNSS senza autorizzazione.
- Compilare e testare ogni nuova versione.
