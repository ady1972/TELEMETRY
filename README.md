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
- [Guition 4.3 RC2](firmware/guition-43/README.md): correzioni data/ora, base RC1 V1.0.22.
- [RLCD 4.2 RC2](firmware/rlcd-42/README.md): correzioni data/ora, base RC1 TEST26.
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


RC1 recepisce l’allineamento di tempi e funzionamento riferito dall’utente
nell’ultimo test comparativo, comunicato il 13/11/2026; le anomalie di data/ora restano
da collaudare in RC2.

## Workspace ESPHome Builder

Gli ingressi dei progetti nuovi seguono il layout del Guition 4.3: YAML nella
radice del workspace, componenti e risorse in una cartella dedicata per versione.
Copiare da `firmware/rlcd-42-3-colori` e `firmware/5 pollici transflettivo`
gli YAML e le rispettive cartelle `GOATS_*` nello stesso workspace:

```text
workspace/
  goats_42_color_v0405_boot_fast_font_test.yaml
  GOATS_V0405_BOOT_FAST_FONT_TEST/
  goats_42_color_v0406_test26.yaml
  GOATS_V0406_TEST26/
  goats_5_transflettivo.yaml
  goats_5_transflettivo_display_test.yaml
  GOATS_5_TRANSFLETTIVO_V010/
```

La variante display 5 pollici include anche lo YAML base: tenerli entrambi
nel workspace. I sorgenti, il pinout e le logiche dei firmware restano invariati.

## Roadmap

Le tre correzioni di [ROADMAP.md](ROADMAP.md) sono implementate in RC2:
orario Europe/Rome, nomi `TA06NO01.CSV` e data effettiva nei dettagli.
Prove hardware previste dall'utente nella settimana 16–22 novembre 2026.

Dopo il collaudo RC2, la roadmap prevede nell'ordine:

1. RLCD: riavvio dalla modalità USB Mass Storage premendo KEY o BOOT.
2. RLCD e Guition: OTA Wi-Fi attivabile dal menu opzioni, con radio normalmente spenta.
3. Valutazione delle interazioni con action cam GoPro, Insta360 e altri modelli.

Queste fasi sono pianificate e non incluse in RC2.

## Sviluppo
- ESPHome
- Codex per analisi e modifiche ai sorgenti
- GitHub per versionamento e backup

## Regole
- Preservare sempre le versioni stabili.
- Non modificare i parametri GNSS senza autorizzazione.
- Compilare e testare ogni nuova versione.
