# DIAG3 + RC3.3 STEP3 — telemetria e Manager, senza SD

Parte dallo STEP2A e aggiunge la catena per un primo test: caricamento circuiti
USB, riconoscimento automatico, motore giri/settori RC3.3, registrazione dei
punti GPS nella flash interna e lettura dei CSV dal Manager Windows.
Non richiede microSD, tasti esterni, Wi-Fi, OTA o USB Mass Storage.

## Installazione e prova breve

1. Estrarre tutto e mantenere i due YAML accanto a `GOATS_DIAG3_RC33_STEP3/`.
   Compilare/installare via ESPHome USB `goats_42_diag3_rc33_step3.yaml`.
   Il secondo YAML `_diag.yaml` parte direttamente nella diagnostica.
   Incluso anche `bin/firmware.factory.bin`, immagine USB completa compilata
   dal primo YAML, per ESPHome Web (offset 0x0 se richiesto). Il file
   `firmware.ota.bin` e' solo l'applicazione, non l'immagine completa.
2. Chiudere la connessione ESPHome Web/log prima di aprire la stessa COM nel
   Manager. Usare la USB nativa ESP32-S3, quella utilizzata per programmare;
   non la porta del GPS o un eventuale convertitore USB-UART della scheda.
3. Da fermo, inviare il catalogo dal normale editor circuiti del Manager.
   Traguardo e linee settore devono essere reali. Rileggere il catalogo per
   controllare che sia stato memorizzato. I circuiti restano nella NVS anche
   dopo un riavvio. Non occorre selezionare la pista a mano.
4. Per il test Racing: ottenere un fix 3D con almeno quattro satelliti.
   Dopo tre NAV-PVT validi consecutivi entro 2 km dal centro di un traguardo
   viene selezionato il circuito piu' vicino. La pista non cambia durante
   un giro. Il solo fix non avvia il cronometro: serve il passaggio sul
   traguardo secondo le condizioni RC3.3. Da quel campione viene salvata
   la traccia, un punto per ogni NAV-PVT distinto valido, senza decimazione.
5. A fine prova, da fermo, tenere BOOT almeno 3 s e rilasciarlo, oppure usare
   il comando `stop` descritto sotto. La chiusura e' anche automatica dopo
   60 s senza campioni validi in movimento, come timeout RC3.3. Attendere
   `REC:0` prima dello scaricamento; la coda viene prima svuotata in flash.
6. Nel Manager Windows V5.4.15.20: **Importa Sessioni**, pannello
   **MICROSD VIA USB SERIALE — TEST23**, scegliere COM, **LEGGI MICROSD**,
   poi **SCARICA SELEZIONATI/TUTTI**. In questo firmware quei comandi leggono
   la flash interna: la scritta microSD e' dell'interfaccia esistente.
   Per importare nel database usare **SCANSIONA CARTELLA** sulla destinazione.
   Non usare **MODALITA USB SD / ATTIVA USB SD**: richiede SD/Mass Storage.

Il protocollo seriale di V5.4.15.19 e' identico a quello della V5.4.15.20.
Le prove usano codice reale del Manager per costruire il catalogo, elencare,
scaricare BURST4, controllare CRC e importare/cancellare il CSV. Nessuna nuova
versione del Manager e' necessaria per questi comandi. Non vengono aggiunte
funzioni live/streaming alla sua interfaccia.

## Test al banco senza circuito e senza tasti

E' possibile registrare una traccia libera senza attraversare un traguardo:

```sh
python manager_test.py --port COM5 status
python manager_test.py --port COM5 record
python manager_test.py --port COM5 stop
```

Sostituire COM5 con la USB del laptimer. Il comando usa Python con `pyserial`
(la stessa dipendenza del Manager; se assente: `python -m pip install pyserial`).
Chiudere il Manager mentre il comando usa la COM, poi riaprirlo per scaricare.
`record` richiede scheda ferma e memoria pronta; attende un fix valido per
iniziare. La registrazione libera usa lap 0 e appare come **Traccia completa**
nel Manager. `stop` richiede di essere fermi e lascia finire il salvataggio.
E' possibile terminare una traccia libera anche con BOOT o timeout 60 s.

BOOT dopo l'avvio:

- breve: Racing/DIAG3;
- da 1,2 a meno di 3 s: LAP TIME/DELTA;
- almeno 3 s: da fermo avvia una traccia libera se inattivo, altrimenti chiude
  la traccia attiva. Non tenerlo premuto all'accensione: e' il bootloader.

`arm` riarma il test in modalita' circuito senza cancellare file o circuiti.
Dopo la chiusura la modalita' circuito viene comunque riarmata per un nuovo
passaggio sul traguardo. La gestione dei menu completi RC3.3 e l'archivio
riepilogativo NVS RC3.3 non sono ancora attivati; i punti delle sessioni
sono invece persistenti ed esportabili.

## Diagnostica e capacita'

La Racing, i font e il flusso LCD completo a blocchi sono quelli STEP2A.
La DIAG3 conserva i valori GPS principali e mostra in basso:

- `MEM`: stato della flash e spazio residuo;
- `USB`: driver USB nativo disponibile, non garanzia di collegamento PC;
- `REC`: traccia attiva/in chiusura; `C`: NAV-PVT distinti elaborati dal core;
- `P`: circuiti caricati; `PT`: punti effettivamente scritti dell'ultima traccia;
- `D`: punti persi dalla coda RAM nell'ultima/attuale traccia.

Richiedere durante il test PVT stabile, C/PT crescenti mentre REC=1 e D=0.
La scrittura e' fuori dal parser GPS: solo coda RAM da 512 record nel callback,
poi al massimo otto record / 256 byte per iterazione. Il GPS viene letto prima
di USB, scrittura flash e blocco LCD; le scritture USB sono non bloccanti.
Il CRC del catalogo viene calcolato su caricamento/modifica, non a ogni PVT.

Si usa esclusivamente la partizione `goatsfs` di 2 MB gia' riservata nella
configurazione DIAG3. Il giornale binario interno e' specifico dello STEP3;
il CSV esportato mantiene le sette colonne RC3.3. Un record punto occupa
32 byte: capacita' teorica circa **43 minuti totali a 25 Hz**, meno metadati,
con un massimo di **64 sessioni**, incluse quelle cancellate. Non c'e' una
sovrascrittura circolare. A memoria/indice pieno la registrazione si ferma,
la Racing puo' continuare ma i punti successivi non vengono salvati.

I file possono essere letti dopo spegnimento. Una scrittura interrotta viene
rilevata dal CRC: il prefisso valido e' recuperabile, poi si deve scaricare e
svuotare la memoria prima di registrare ancora. Non vengono formattati dati
sconosciuti e non si abilita un filesystem/SD in avvio.

La cancellazione singola dal Manager nasconde il file con un record di
cancellazione, ma non recupera spazio fisico. Dopo avere scaricato le tracce:

```sh
python manager_test.py --port COM5 erase
```

Questo comando cancella **tutte le tracce STEP3**, a settori, senza toccare
circuiti/NVS. Attendere `READY=1 STATE=PRONTA`. Gli ID dei nuovi file non
vengono riutilizzati, anche dopo cancellazione o riavvio. Non eseguire erase
per il normale primo avvio su una partizione vuota: viene usata direttamente.

Hardware e GNSS invariati: ESP32-S3 N16R8/flash16MB; GPS TX->GPIO1,
RX<-GPIO2; LCD CS10/DC9/RST8/MOSI11/CLK12 a 4MHz; richiesta GPS 230400/25Hz.
SD, batteria ADC, TinyUSB/MSC, Wi-Fi e OTA rimangono esclusi. L'icona batteria
continua a essere un contorno senza livello misurato.

Compilazione e test software superati. Continuita' GPS durante USB/flash,
resa LCD, tempi reali di scrittura e cronometraggio restano da provare sulla
scheda. L'anteprima e la simulazione non sostituiscono questo test.
