# RC3.3 STEP3A LCD — prova allineamento pixel

La foto dell'utente mostra caratteri con tratti sdoppiati/spostati. Si verifica
un parametro del controller, mantenendo i font e tutte le funzioni STEP3.
La precedente sperimentazione sui contorni dei font non e' inclusa.

## Modifica da verificare sul pannello

Lo STEP3 imposta MADCTL=0x80 (ordine pagine invertito) e DTFORM=0x11.
La sezione 8.1.24, pagina 68 del [datasheet ST7306](https://admin.osptek.com/uploads/ST_7306_V0_1_c30c3541a3.pdf)
indica XDE come compensazione up/down da abbinare a MY=1, attiva a zero.
Questo test usa **DTFORM=0x01**: cambia soltanto il bit XDE, mantenendo BPS=1
(3 byte per 24 bit), rotazione e packing originali. E' una correzione proposta
per lo sfasamento a coppie di pixel, non una causa fisica gia' dimostrata.

Non cambiano la sequenza delle altre impostazioni LCD, i suoi livelli di
pilotaggio o la modalita' di refresh; il trasferimento completo a blocchi
resta STEP2A/STEP3. Font, dimensioni, spaziatura e layout Racing sono identici.
GPS, core, telemetria interna, CSV e protocollo Manager sono byte-identici.

Installare prima **goats_42_diag3_rc33_step3a_lcd.yaml** (Racing).
Se il difetto resta, compilare **goats_42_diag3_rc33_step3a_lcd_test.yaml**:
mostra una pagina statica con linee 1 px, cifre, diagonale, testo invertito e
tre campioni colore. GPS/Manager continuano a girare. Fotografare soprattutto
le cifre e la diagonale. L'anteprima software `preview/alignment_expected.png`
mostra il disegno atteso, non la risposta del pannello.

Per un confronto A/B, nello stesso YAML si puo' impostare
`lcd_data_swap: false`: ripristina il solo byte DTFORM=0x11 dello STEP3.
Serve ricompilare/installare e riavviare. `alignment_test: false` mantiene
la Racing normale; `_diag.yaml` parte nella diagnostica GPS.
Il factory incluso e' compilato dal primo YAML: Racing con compensazione attiva.

Le istruzioni di telemetria/Manager sotto restano quelle dello STEP3.
La nuova combinazione LCD deve ancora essere confermata sulla scheda.

Parte dallo STEP2A e aggiunge la catena per un primo test: caricamento circuiti
USB, riconoscimento automatico, motore giri/settori RC3.3, registrazione dei
punti GPS nella flash interna e lettura dei CSV dal Manager Windows.
Non richiede microSD, tasti esterni, Wi-Fi, OTA o USB Mass Storage.

## Installazione e prova breve

1. Estrarre tutto e mantenere i due YAML accanto a `GOATS_DIAG3_RC33_STEP3A_LCD/`.
   Compilare/installare via ESPHome USB `goats_42_diag3_rc33_step3a_lcd.yaml`.
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
   dopo un riavvio. Non occorre selezionare la pista a mano. Cataloghi molto grandi possono
   ricevere `GTRK_ERR MEMORY`: ridurre il catalogo per il test. Quello gia’
   memorizzato resta attivo se il nuovo invio viene rifiutato.
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
La copia legacy del catalogo viene liberata dopo l’attach. Il ricevitore USB
rifiuta un nuovo catalogo se non rimane RAM sufficiente per decodificarlo.

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
