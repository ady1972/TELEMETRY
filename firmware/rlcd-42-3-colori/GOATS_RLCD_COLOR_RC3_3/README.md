# GOATS RLCD 4.2 COLOR RC3.3

Aggiornamento richiesto il 26 novembre 2026 per il progetto completo **ESP32-S3
da 16 MB** con Osptek ST7306 rosso/nero/bianco. La Zero da 4 MB e il test
alimentazione non sono la destinazione di questo firmware.

## Allineamento all'ultima RLCD

Baseline: `firmware/rlcd-42/GOATS_RLCD_RC3_3`, commit di riferimento
`855954ed` (usare l'hash completo nel rapporto `VERIFICA.md`). Tutti i suoi
19 header applicativi sono copiati senza modifiche. Restano gli stessi:

- Acquisizione temporale e gestione dei NAV-PVT nel motore RC3.3 invariate;
  ricezione UART e configurazione del ricevitore dalla COLOR V0.40.5, descritte sotto.
- Motore giri, settori, delta e acquisizione temporale del riferimento.
- Correzioni data/ora italiana e nomi CSV, metadati di registrazione.
- Riepilogo con tempo, velocità massima/media e BEST evidenziato.
- Modalità LAP TIME / DELTA, scelta iniziale persistente nel menu.
- Best Lap a schermo intero con titolo e tempo lampeggianti ogni 500 ms.
- Chiusura sessione RC3.2/RC3.3 dal ciclo principale: drenaggio della coda GPS
  in piccoli gruppi, salvataggio/scarto e riarmo senza riavvio.
- Catalogo circuiti, archivio, esportazione USB e modalità disco microSD.

Tutte le schermate operative usano il rendering della RLCD RC3.3: stessa geometria,
stesse coordinate, etichette, riquadri e dimensioni dei font. In Racing:

- campo principale tempo/DELTA in alto, con settori immediatamente sotto;
- DELTA/LAP TIME e BEST a sinistra, velocità a destra;
- GPS/HDOP, nome circuito e icona batteria nella barra inferiore.

Sono identici anche menu, riepiloghi, schermate di conferma, post-giro, Best Lap
e USB. Le sole differenze di presentazione sono identità COLOR, indicazioni dei
quattro pulsanti e rosso nei riempimenti dei delta negativi. La batteria resta
non disponibile se non esiste un partitore: si mantiene lo stesso spazio e
l'icona senza inventare una percentuale.

Le cartelle V0.40.5 e V0.40.6 TEST26 e i firmware monocromatici restano intatti.
Questa è una nuova variante da collaudare, non una certificazione di stabilità.

## GNSS dalla COLOR V0.40.5 confermata funzionante

Grafica, menu, font, driver display, motore giri, settori, delta, sessioni e
scheduling sono quelli RC3.3. L'aggiornamento usa il GNSS della COLOR V0.40.5
che l'utente ha confermato funzionante nello ZIP
`GOATS_V0405_BOOT_FAST_FONT_TEST_2026_11_03.zip`: tutti i suoi 14 file sono
identici a quelli conservati nel repository. Non viene sostituito il motore
RLCD con il vecchio laptimer COLOR.

Sono ripresi sia il configuratore `goats_m9n_cfg.h` effettivamente chiamato
dalla COLOR, sia il parser `goats_ubx_m9n_ak97_full.h`, adattati alle API HAL
di ESPHome per ESP-IDF. Il parser è in `goats_color_gnss_v0405.h`; l'adattatore
`goats_color_gnss_bridge.h` inoltra ogni NAV-PVT valido, con payload e iTOW
originali, alla stessa funzione `goats_b::on_pvt` della RLCD RC3.3. Non introduce
un secondo motore giri né sostituisce il tempo con quello mappato dal vecchio
laptimer COLOR. La coda legacy viene svuotata dopo l'inoltro per evitare doppi
consumatori. Date, registrazioni, criteri di fix del motore (3D e almeno quattro
satelliti) e gestione dei duplicati rimangono RC3.3.

La ricezione drena la UART come la COLOR; conserva verifica checksum UBX,
limite payload 1024 byte, misura della frequenza, scadenze dello stato GNSS
e conteggio satelliti visibili dal campo NAV-SAT originale. Le righe NMEA non
alimentano il laptimer e vengono ignorate dal parser, come nella COLOR. Il
contatore diagnostico `nmea_ok` resta quindi zero. Il file `m9n_passive.h`
RC3.3 è conservato come riferimento, ma non è incluso nel firmware.


Servono **TX GPS → GPIO1 e RX GPS → GPIO2**, oltre a GND comune. La UART parte
come V0.40.5 a 38400 e prova 38400/9600/115200/230400; al termine ESP e ricevitore
sono a 230400. Richiede NAV-PVT a ogni epoca da 40 ms (25 Hz), NAV-DOP/NAV-SAT
una volta ogni 25 epoche e NMEA GGA/GSA/GSV/RMC alla stessa cadenza. Ripristina
anche le richieste di costellazioni della V0.40.5: GPS, Galileo, BeiDou, GLONASS,
SBAS attivi, QZSS disattivato e MAXSVS 32 soggetto ai limiti del ricevitore.

La sequenza è solo RAM, senza salvataggio flash/BBR, e viene ripetuta a ogni
avvio normale. Le attese esplicite sono circa 2,43 secondi, oltre ai tempi UART.
Non aspetta il fix e non riconfigura durante il cronometraggio. In USB MSC viene
saltata. Se il GPS perde alimentazione mentre l'ESP resta acceso, riavviare
anche l'ESP per ripetere la configurazione.

Come nel codice V0.40.5, non verifica ACK/NAK: si dichiara trasmessa la sequenza,
non accettata dal modulo. Controllare in Info GPS NAV-PVT Hz e satelliti dopo
un avvio a freddo. La trasmissione dei comandi appartiene soltanto al
configuratore iniziale `goats_cfg::configure`. La funzione di configurazione
alternativa presente nel vecchio parser COLOR non viene chiamata: invierebbe
impostazioni NMEA differenti da quelle della versione provata.

## Avvio senza splash

Lo splash è stato eliminato su richiesta dell'utente, che ne vedeva il logo
residuo nella schermata Racing. Il codice già ricomponeva il framebuffer
completo, quindi non è stata identificata una causa hardware certa del residuo.

Questa variante non carica né disegna più l'immagine di avvio e non attende i
precedenti tre secondi. Il primo frame è direttamente Racing, trasmesso per
intero; in modalità USB viene mostrata la relativa schermata. Non vengono
aggiunti flash bianco/nero, reset periodici o cambi sperimentali ai registri
ST7306. La versione resta visibile in Info.

Dopo il caricamento, eseguire un avvio a freddo togliendo completamente
alimentazione alla scheda, inclusa l'eventuale batteria. Verificare sul pannello
che la schermata Racing e i caratteri rimangano puliti.

## Refresh del display

Il driver mantiene la sequenza ST7306, i livelli del controller, il clock SPI
a 4 MHz e la mappatura tricolore già usati. Nessun cambio di frequenze interne
del pannello viene introdotto per tentativi.

La schermata viene composta interamente in RAM prima della trasmissione.
Lo svuotamento del framebuffer non viene mai inviato come frame intermedio.
L'aggiornamento differenziale invia solo i gruppi 6×2 pixel fisici cambiati:

- nessuna scrittura SPI se la schermata è identica;
- zone cambiate distanti trasmesse separatamente, senza includere la parte
  immutata fra loro;
- righe adiacenti raggruppate quando possibile nella stessa finestra;
- un solo aggiornamento completo al primo frame, nessun reset/blank periodico.

Il controllo del driver verifica che ogni gruppo cambiato venga trasmesso una
sola volta e che i gruppi immutati non siano riscritti. È una verifica software:
TE resta scollegato e la scansione fisica del pannello non è sincronizzata.
La riduzione dei piccoli refresh visibili va confermata al banco; i lampeggi
configurati di post-giro/Best Lap restano intenzionali.

## Definizione dei caratteri

Tutti i valori e testi usano il motore font nativo di ESPHome, **Roboto Condensed
Bold a 1 bit**, con le stesse dimensioni e la stessa selezione del font della
RC3.3. Nessuna compressione orizzontale, ingrandimento di bitmap, riparazione dei
fori o dithering temporale. Etichette laterali e relativi bitmap sono quelli
del riferimento RC3.3. Il TTF è locale, con licenza e provenienza in `fonts/`.

La risoluzione fisica resta 400×300. Le anteprime in `anteprime/` eseguono il
rendering effettivo degli YAML con la classe Font di ESPHome, usando dati
simulati. Non sono foto del pannello. Un test confronta i comandi di disegno e
i pixel logici della variante COLOR con la RC3.3 per tutte le pagine e nelle
due modalità Racing, ammettendo solo le differenze di testo/colore sopra.

## Collegamenti — aggiunta della linea RX GPS → GPIO2

| Funzione | Collegamento ESP32-S3 |
|---|---|
| LCD VCC / GND | 3V3 / GND |
| LCD CS / DC / RESET | GPIO10 / GPIO9 / GPIO8 |
| LCD MOSI / SCLK | GPIO11 / GPIO12, SPI mode 0, 4 MHz |
| LCD TE | Scollegato |
| TX GPS | GPIO1, RX ESP a 230400 baud |
| RX GPS | **GPIO2, TX ESP necessario per inviare la configurazione** |
| GPS VCC / GND | Secondo la scheda ricevitore / GND comune; 3V3 solo se ammesso su VCC |
| SU / GIÙ / BACK / OK | GPIO4 / GPIO5 / GPIO6 / GPIO7, pulsanti verso GND |
| microSD CMD / CLK / DAT0 | GPIO21 / GPIO38 / GPIO39, SDMMC a 1 bit |
| microSD VDD / VSS | 3,3 V / GND |
| USB nativa D− / D+ | GPIO19 / GPIO20, connettore secondo lo schema della scheda |

GPIO4 è SU: nessun ADC batteria viene inventato. Nessuna PSRAM richiesta.
Usare una scheda che esponga i GPIO richiesti. SD FAT32, pull-up 10 kΩ a 3V3
su CMD/DAT0 e DAT1/DAT2/DAT3 del socket se non già presenti; 100 nF + 10 µF
vicini al socket. CLK non richiede pull-up. Il bus SD non è lo SPI del display.
Per Manager/MSC serve la USB nativa, non CH340/CP210x. In MSC espellere dal PC
prima del riavvio. Modificare i collegamenti a dispositivo spento.

## Tasti

- GIÙ breve in Racing: alterna DELTA/LAP TIME fino al riavvio; lungo non agisce.
- OK breve: menu/conferma; OK lungo nel menu: indietro.
- OK tenuto almeno 3 secondi in Racing: conferma fine sessione.
- SU nel menu: voce precedente; GIÙ: successiva; BACK: indietro.
- In Opzioni gara → Modalità schermata si salva la scelta iniziale in NVS.
- Durante la chiusura sessione i tasti non interrompono il salvataggio/scarto.

## ESPHome e flash

Affiancare nella cartella ESPHome:

```text
goats_42_color_rc3_3.yaml
GOATS_RLCD_COLOR_RC3_3/
```

Aprire lo YAML esterno. Componenti e TTF sono locali. ESPHome,
ESP-IDF e dipendenze TinyUSB richiedono il normale download alla prima build.

Pacchetti aggiornati con grafica/logica RC3.3 e GNSS V0.40.5 completo (inizializzazione e ricezione):
[ZIP sorgenti](download/GOATS_RLCD_COLOR_RC3.3_GNSS_V0405_SORGENTI.zip) ·
[Primo flash USB](download/GOATS_RLCD_COLOR_RC3.3_GNSS_V0405_PRIMO_FLASH_USB.zip).
I pacchetti precedenti senza suffisso GNSS_V0405 restano archiviati per riferimento.

```sh
esphome config goats_42_color_rc3_3.yaml
esphome compile goats_42_color_rc3_3.yaml
esphome upload goats_42_color_rc3_3.yaml --device COM5
```

Sostituire la porta reale. Il **binario factory per 16 MB** include bootloader,
partizioni e app e va scritto a **0x0**, esclusivamente sulla scheda corretta.
Prima del flash esportare le sessioni importanti. Nessun erase-flash automatico.
Il file app da solo non è un'immagine completa da caricare a offset zero.

Non usare pacchetti firmati del modello RLCD_MONO_42 per questo display: il
progetto ESPHome è `goats_rt.rlcd42_color`. Questa consegna non aggiunge il modello
COLOR al catalogo di aggiornamento firmato del Manager Windows. Il trasferimento
di circuiti/sessioni e MSC mantengono invece il protocollo della baseline.
Nessun Wi-Fi o OTA. Nessun flash automatico eseguito.

## UART0 come la COLOR — nuova variante da verificare

Dopo la conferma che la V0.40.5 originale torna a funzionare sullo stesso
hardware, è disponibile la [variante UART0](UART0_COLOR.md). Disattiva il
logger seriale come la COLOR, liberando UART0 per il GPS. Include Racing
completa e diagnostica senza tasti. I precedenti test con RX zero restano
archiviati; non si dichiara ancora risolto il difetto sul dispositivo.

## Test UART dopo RX zero

La prima foto diagnostica conferma RX 0 byte. È disponibile il
[test ESPHome GPS UART TEST2](GPS_UART_TEST2.md), con cambio baud senza
ricreare il driver ESP-IDF e lettura del baud hardware. Usare temporaneamente
`goats_42_color_rc3_3_gps_uart_fix.yaml`; la pagina compare senza tasti.
La causa del difetto rimane da verificare sul dispositivo.

## Diagnostica GPS senza pulsanti

Se il GPS resta assente e i tasti non sono ancora saldati, usare temporaneamente
`goats_42_color_rc3_3_gps_diag.yaml`, affiancato allo YAML normale: mostra da solo
byte UART, UBX, NAV-PVT, satelliti, fix e risposte ACK/NAK CFG. La gestione GNSS
resta la stessa. Vedere [procedura e lettura dei dati](DIAGNOSTICA_GPS.md).
Questa variante raccoglie la diagnosi: la causa del mancato GPS segnalato
sull'ultimo firmware non è ancora determinata.

## Collaudo richiesto

1. Avvio a freddo: Racing diretta senza logo, Info COLOR RC3.3, colori corretti, nessun reset.
2. Racing ferma e in movimento: osservare i piccoli refresh, contorni di cifre,
   punto e segni, nelle due modalità, specialmente quando più valori cambiano.
3. Menu e ritorno: nessuna immagine residua; test post-giro e Best Lap.
4. Con entrambe le linee GPS collegate, verificare NAV-PVT e satelliti dopo
   avvio a freddo. Con GPS e SD: salvare due sessioni consecutive, scartarne una, riattraversare
   il traguardo senza riavvio; verificare CSV a 25 Hz, date e riepiloghi.
5. Catalogo circuiti e download sessioni via USB; MSC con espulsione corretta.

Esiti software e compilazione sono riportati in `VERIFICA.md`. Nessuna prova
fisica né prova in pista è stata eseguita con questa modifica.
