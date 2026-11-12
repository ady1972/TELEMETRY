# GOATS Guition V1.0.21 DIAG USB

Base: V1.0.20 alla revisione 2dd77edbf2b6fcee7a94dccad042567024c1441c.
Branch: diagnostics/guition-v1.0.21. La V1.0.20 resta intatta.
Il motore goats_laptimer.h e' copiato senza alcuna modifica, byte per byte.

## Compilazione con ESPHome Builder su Windows

Nel repository usare **firmware\guition-43**, selezionando
**goats_guition_43_v1_0_21_diag_usb.yaml**. Accanto al YAML deve restare la
cartella **goats_guition_43_v1_0_21_diag_usb** con tutti gli header e il logo.
Non selezionare la sola sottocartella degli header e non usare il YAML V1.0.20.
Nel pacchetto autonomo usare invece la cartella radice del pacchetto, dove si
trovano lo stesso YAML e la stessa sottocartella.

Comandi equivalenti:

```powershell
python -m esphome config goats_guition_43_v1_0_21_diag_usb.yaml
python -m esphome compile goats_guition_43_v1_0_21_diag_usb.yaml
```

Conservati GNSS passivo, UART/pin, 230400 baud, 25 Hz, layout Racing,
formati CSV/GSA3, flussi e comandi Manager/USB. Nessun Wi-Fi o OTA.

## Contatori

Tutti i contatori sono in RAM, globali dall'avvio (BOOT) e relativi alla sessione
(SESSION). La sessione diagnostica inizia quando GoatsSessionManager attiva la
sessione circuito/libera, prima dell'apertura SD; termina dopo la finalizzazione
esistente, oppure al reset/scarto/errore iniziale di apertura. Nessun reset o
filtraggio dei dati applicativi viene aggiunto. I contatori non persistono al reboot.

- PVT: frame NAV-PVT completati dal parser, compresi quelli con checksum errato.
  Un frame incompleto o scartato dal limite di lunghezza del parser non e' contato.
- valid: checksum corretto e payload di almeno 92 byte, come nella V1.0.20.
- fix: valid con il criterio fix originale (gnssFixOK e fix_type >= 2).
- bad_ck: NAV-PVT completati con checksum errato.
- dup: iTOW uguale al precedente PVT valid, anche senza fix. Nessun duplicato viene scartato.
- itow_max_ms: massimo passo iTOW in avanti, gestendo il confine settimana.
  gaps conta passi >40 ms; seq_err conta passi non multipli di 40 ms,
  epoche fuori settimana e inversioni/reset interpretati come passo >mezza settimana.
  Non sono prove di overflow UART, ne' stime certe di campioni persi.
- decode_max_ms: massimo intervallo fra decodifiche PVT valid. Piu' pacchetti
  decodificati insieme possono avere intervalli quasi nulli; non e' la latenza GNSS assoluta.
- q_in/q_out/processed: push, pop riusciti e chiamate al motore.
- overflow: campioni vecchi eliminati dalla coda piena (politica originale invariata).
- cleared: campioni eliminati intenzionalmente da clear(), per esempio in modalita' libera.
- high: massimo riempimento dopo un push (limite 50).
- CSV: righe punto scritte integralmente con successo da fat_write_all_.
  Non include intestazioni, tentativi falliti o scritture parziali; non garantisce
  persistenza fisica dopo una successiva sync fallita o perdita di alimentazione.
  Non garantisce campioni GNSS distinti: resta il campionamento CSV della V1.0.20.

I campioni gia' in coda all'inizio della sessione possono essere elaborati durante
la sessione: q_in e q_out della singola sessione non devono necessariamente coincidere.

## Tempi microSD

Orologio esp_timer_get_time(), risoluzione in microsecondi. Per categoria:
numero chiamate, durata massima, conteggi strettamente **>10, >20, >40 ms**.
Le soglie sono cumulative: una chiamata da 41 ms incrementa tutti e tre i contatori.

Categorie: MOUNT (anche recovery), OPEN, POINT, SYNC periodica, CHECKPOINT,
METADATA (archivi, meta, stato salvataggio e cancellazioni), READ, FINALIZE.
Si misura il tempo dell'intera funzione strumentata, comprese formattazione,
verifiche e attese gia' esistenti, anche uscite anticipate senza I/O.
SD_ALL conta soltanto le chiamate esterne, senza duplicare quelle annidate.
Le categorie possono invece sovrapporsi: POINT include la SYNC periodica.
Non sommare le categorie per ricavare il numero di accessi fisici alla scheda.
Le letture grezze eseguite direttamente dai trasferimenti USB non sono tutte
strumentate; queste misure non sono un profiler completo del driver SD/SPI.
Le attese/mount/sync bloccanti della V1.0.20 sono misurate, non corrette.

## UART

UART_OVF=NA significa **non rilevabile**, non zero overflow.
ESPHome 2026.7.3 installa il driver UART ESP-IDF senza coda eventi
(event queue size 0 e nullptr). Non si riconfigura il driver per recuperare
UART_FIFO_OVF/UART_BUFFER_FULL. Nessun accesso aggiuntivo alla UART.

## Riepiloghi e limite del logger

Nessuna stampa diagnostica nel parser o durante il cronometraggio. Nessuna
scrittura diagnostica SD. Gli snapshot di fine sessione sono mantenuti in una
coda RAM fissa di quattro elementi; a coda piena si conserva quanto gia' accodato
e si incrementa reports_lost per i nuovi riepiloghi non accodabili.
BOOT nello snapshot fotografa i totali alla chiusura, non all'istante della stampa.

Al massimo una riga WARN goats_diag al secondo, 24 righe per snapshot, soltanto
con motore fermo, nessuna sessione attiva, nessun CSV live aperto, nessuna modalita'
MSC e nessuna transazione USB pendente. Si attende inoltre almeno 2 s dall'ultima
attivita' USB. Se parte un'altra sessione/trasferimento, l'emissione si sospende.
I trasferimenti sincroni e la diagnostica sono sullo stesso task applicativo.

**Limite intenzionale:** il logger originale resta `level: WARN`, `baud_rate: 0`,
senza API/rete. I riepiloghi vengono consegnati al logger ESPHome ma questa
configurazione NON offre un'uscita seriale visibile nel monitor USB. Non vengono
iniettati messaggi nel canale Manager. Per leggere le misure sono disponibili
le strutture RAM goats_diag_v1021::boot, session e reports tramite debugger;
un'uscita osservabile aggiuntiva richiede un successivo accordo sul canale.
Questa build non promette log visibili via USB con la configurazione invariata.

## Prove hardware da eseguire

Confrontare V1.0.20 e V1.0.21 sullo stesso scenario: sessione normale, GNSS
interrotto, SD lenta/assente, chiusura/scarto, modalita' libera e trasferimenti
Manager. Controllare 40 ms fra epoche, overflow, max SD e righe CSV contro punti
scritti. Nessuna validazione dell'accuratezza del cronometro e' implicita.
