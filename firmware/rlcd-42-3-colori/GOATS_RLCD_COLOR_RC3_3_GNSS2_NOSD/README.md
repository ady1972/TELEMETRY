# GOATS RC3.3-GNSS2-NSD — senza microSD

Variante per l'ESP32-S3 N16R8 dell'utente, con display ST7306 tricolore e
microSD non ancora saldata. Mantiene schermate e logiche di cronometraggio
RC3.3 e il componente GNSS derivato dalla DIAG2 funzionante.

## Perche' viene esclusa la SD

Nel completo precedente, dopo il primo fix valido, un intervallo da 1 secondo
ritentava il mount finche' la SD non risultava pronta. Ogni chiamata includeva
50+350 ms di attesa, oltre al tempo del driver SDMMC. Con la scheda assente
questo percorso poteva bloccare ripetutamente il loop che legge il GPS.
Il codice di questo percorso e' verificato; non e' ancora dimostrato che sia
la causa della mancata indicazione GPS riportata dall'utente. Poiche' il mount
parte soltanto dopo un fix valido, non puo' spiegare zero byte prima di
qualsiasi NAV-PVT: in quel caso servono i contatori AUDIT.

Qui sono rimossi l'intervallo di mount, le implementazioni SDMMC/FatFS,
la coda dei punti destinata ai file e lo stack USB Mass Storage/TinyUSB.
Non vengono configurati i GPIO SD 21/38/39. Nessuna lettura, scrittura,
inizializzazione o ritentativo verso la SD, neppure al primo fix o tramite
richiesta USB. Le funzioni SD restituiscono indisponibilita' senza errori
ripetuti o riavvii. I comandi GSD rispondono SD_DISABLED.

I giri, le sessioni, le velocita' e le date restano in **NVS interna**, con
le logiche RC3.3. Restano le funzioni USB seriali per catalogo circuiti e
archivio NVS; la voce Mass Storage non puo' attivarsi. Nessun Manager e'
necessario per l'installazione ESPHome.

## Installazione USB con ESPHome

Estrarre tutto lo ZIP e tenere affiancati i due YAML e la cartella:

```text
goats_42_color_rc3_3_gnss2_nosd.yaml
goats_42_color_rc3_3_gnss2_nosd_audit.yaml
GOATS_RLCD_COLOR_RC3_3_GNSS2_NOSD/
```

- **Racing normale**: aprire `goats_42_color_rc3_3_gnss2_nosd.yaml`.
- **Verifica senza tasti**: aprire `goats_42_color_rc3_3_gnss2_nosd_audit.yaml`.
  Alterna Racing e pagina **RC3.3 NOSD AUDIT** ogni 10 secondi, mantenendo
  l'esecuzione del renderer Racing originale anche durante AUDIT.

Sono disponibili anche i binari gia' compilati, per ESPHome Web via USB:

- `bin/firmware.factory.bin`: Racing normale senza SD.
- `bin/firmware.audit.factory.bin`: stessa variante senza SD, con AUDIT automatico.

Entrambi sono immagini complete; offset 0x0 se richiesto dallo strumento.
Per isolare differenze della compilazione locale, la prima prova puo' usare
il binario AUDIT gia' compilato. Non usare le immagini `*.ota.bin` come
immagine completa: contengono soltanto l'applicazione.

Per leggere i contatori non servono pulsanti o log seriale. Dopo circa un
minuto fotografare tutta la pagina AUDIT. Dettagli in [AUDIT_GPS.md](AUDIT_GPS.md).
Non cambiare cablaggio: TX GPS -> GPIO1, RX GPS <- GPIO2, GND comune;
LCD CS10/DC9/RST8/MOSI11/CLK12. Tasti 4/5/6/7 verso GND quando verranno saldati.

## Parti conservate

- UART ESPHome della DIAG2: 38400 iniziali, buffer 16384, 8N1 e logger seriale 0.
- Configuratore Arduino originale: stessi 17 frame, cinque cambi baud host
  con load_settings(), ritardi e richiesta 230400/25 Hz in RAM.
- Stesse costellazioni e messaggi; nessuna scansione o correzione dei parametri GPS.
- Parser originale e unico lettore; NAV-PVT grezzi validati inoltrati una volta
  al motore RC3.3. Clock Arduino del parser separato dai timestamp ESPHome UI.
- Quattordici header RC3.3 identici; le sole cinque interfacce di SD/tracce/MSC
  sono sostituite da implementazioni senza accesso all'hardware assente.
- Lambda grafica, font, driver differenziale, modalita' Delta/Lap Time, menu,
  sessioni, salva/scarta, date e laptimer conservati. Splash assente.
- Partizioni RC3.3 e NVS a 0xF90000 conservate. PSRAM non necessaria.

La DIAG2 accetta fix 2D/3D; il motore RC3.3 conserva il requisito di fix 3D,
gnssFixOK e almeno quattro satelliti. Un indicatore di fix assente non prova
che manchino i byte seriali: AUDIT serve a distinguere le condizioni.

## Stato della verifica

Compilazione ESPHome, prove GNSS e confronto di 397 scenari grafici RC3.3:
vedere `VERIFICA.md`. Il precedente completo con SD aveva dato esito negativo
per il GPS; questa variante senza SD richiede ancora la prova dell'utente.
Nessun funzionamento hardware viene dichiarato senza tale prova.
