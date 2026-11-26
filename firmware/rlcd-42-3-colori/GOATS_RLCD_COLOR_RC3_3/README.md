# GOATS RLCD 4.2 COLOR RC3.3

Aggiornamento richiesto il 26 novembre 2026 per il progetto completo **ESP32-S3
da 16 MB** con Osptek ST7306 rosso/nero/bianco. La Zero da 4 MB e il test
alimentazione non sono la destinazione di questo firmware.

## Allineamento all'ultima RLCD

Baseline: `firmware/rlcd-42/GOATS_RLCD_RC3_3`, commit di riferimento
`855954ed` (usare l'hash completo nel rapporto `VERIFICA.md`). Tutti i suoi
19 header applicativi sono copiati senza modifiche. Restano gli stessi:

- GNSS passivo UBX NAV-PVT, 25 Hz già configurati nel ricevitore, UART RX1
  a 230400 baud, nessun TX né comandi GPS.
- Motore giri, settori, delta e acquisizione temporale del riferimento.
- Correzioni data/ora italiana e nomi CSV, metadati di registrazione.
- Riepilogo con tempo, velocità massima/media e BEST evidenziato.
- Modalità LAP TIME / DELTA, scelta iniziale persistente nel menu.
- Best Lap a schermo intero con titolo e tempo lampeggianti ogni 500 ms.
- Chiusura sessione RC3.2/RC3.3 dal ciclo principale: drenaggio della coda GPS
  in piccoli gruppi, salvataggio/scarto e riarmo senza riavvio.
- Catalogo circuiti, archivio, esportazione USB e modalità disco microSD.

Tutte le schermate usano il rendering della RLCD RC3.3: stessa geometria,
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

## Collegamenti, invariati dalla COLOR TEST26

| Funzione | Collegamento ESP32-S3 |
|---|---|
| LCD VCC / GND | 3V3 / GND |
| LCD CS / DC / RESET | GPIO10 / GPIO9 / GPIO8 |
| LCD MOSI / SCLK | GPIO11 / GPIO12, SPI mode 0, 4 MHz |
| LCD TE | Scollegato |
| TX GPS | GPIO1, RX ESP a 230400 baud |
| RX GPS | Scollegato: GNSS passivo |
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

Aprire lo YAML esterno. Componenti, TTF e splash sono locali. ESPHome,
ESP-IDF e dipendenze TinyUSB richiedono il normale download alla prima build.

[Pacchetti sorgenti e binario factory su GitHub](https://github.com/ady1972/TELEMETRY/tree/codex/rlcd-color-rc3-3-display/firmware/rlcd-42-3-colori/GOATS_RLCD_COLOR_RC3_3/download).
I pacchetti di download sono separati dalle dipendenze di compilazione.

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

## Collaudo richiesto

1. Avvio a freddo: splash/Info COLOR RC3.3, colori corretti, nessun reset.
2. Racing ferma e in movimento: osservare i piccoli refresh, contorni di cifre,
   punto e segni, nelle due modalità, specialmente quando più valori cambiano.
3. Menu e ritorno: nessuna immagine residua; test post-giro e Best Lap.
4. Con GPS e SD: salvare due sessioni consecutive, scartarne una, riattraversare
   il traguardo senza riavvio; verificare CSV a 25 Hz, date e riepiloghi.
5. Catalogo circuiti e download sessioni via USB; MSC con espulsione corretta.

Esiti software e compilazione sono riportati in `VERIFICA.md`. Nessuna prova
fisica né prova in pista è stata eseguita con questa modifica.
