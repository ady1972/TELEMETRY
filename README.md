# GOATS RT - Telemetria Kart

Sistema di telemetria e cronometraggio GPS per kart.

## Applicazioni

I progetti completi sono organizzati per piattaforma e versione:

- [GOATS Mobile — Android V0.2.3](mobile/v0.2.3/README.md): sessioni e circuiti
  nella stessa cartella cloud del PC.
- [GOATS Windows — Manager V5.4.15.9 BURST4](windows/v5.4.15.9-burst4/README.md):
  copia file importati, controllo cloud all’avvio, cancellazioni condivise e configurazione GNSS con salvataggio flash e lettura frequenza via USB-UART;
  conservati i controlli delle analisi in fullscreen.

[Guida alla cartella cloud comune](docs/CLOUD_SYNC_MOBILE_WINDOWS.md).

Gli indici [mobile/](mobile/README.md) e [windows/](windows/README.md)
raccolgono le versioni disponibili, ciascuna con sorgenti e dipendenze propri.

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

## RC2.1 — candidato da collaudare

Le configurazioni RC2 identificano ora la revisione RC2.1: aggiungono
**Modalità schermata → DELTA / LAP TIME**, con scambio dei due valori e delle
etichette nella schermata racing e preferenza salvata ai successivi avvii.
Includono la correzione della ripartenza RLCD e del filtro delta Guition,
oltre alla diagnostica della lentezza di salvataggio ancora da misurare.
Dettagli e piano di prova: [Modalità schermata](docs/MODALITA_SCHERMATA.md).
Nessun collaudo hardware o flash eseguito in questa preparazione.

## RC2.2 — riepilogo dei giri

RLCD e Guition mostrano tempo, velocità massima e media per ogni giro,
con BEST evidenziato. Su Guition i settori non compaiono più nel riepilogo.
Su RLCD la massima dei nuovi giri è conservata dopo il riavvio; i vecchi
archivi senza questo dato mostrano --. Dettagli e prove:
[Riepilogo sessioni RC2.2](docs/RIEPILOGO_SESSIONI_RC2.md).

## Sviluppo
- ESPHome
- Codex per analisi e modifiche ai sorgenti
- GitHub per versionamento e backup

## Regole
- Preservare sempre le versioni stabili.
- Non modificare i parametri GNSS senza autorizzazione.
- Compilare e testare ogni nuova versione.
