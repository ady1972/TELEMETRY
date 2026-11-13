# Roadmap GOATS RT

Aggiornata il 13/11/2026. Ambito: laptimer RLCD 4.2 e Guition 4.3.

## Punto di partenza: RC1

L'utente riferisce che, nell'ultimo test comparativo, tempi e funzionamento
del laptimer RLCD e del Guition 4.3 si sono allineati. RC1 identifica questa
base (RLCD TEST26 e Guition V1.0.22 RLCD26 USB) come candidata al rilascio. L'esito riguarda il test riferito dall'utente;
non implica la risoluzione delle anomalie elencate sotto.

RC1 rimane conservata come base del confronto. Le correzioni seguenti sono
implementate nei pacchetti RC2. Test software e build sono verificati separatamente
dal collaudo hardware dell'utente, previsto nella settimana 16–22 novembre 2026.
Note: [RLCD RC2](firmware/rlcd-42/GOATS_RLCD_RC2/RC2.md) e
[Guition RC2](firmware/guition-43/goats_guition_43_rc2/RC2.md).

## 1. Orario locale RLCD — implementato in RC2, da collaudare

Segnalazione: RLCD visualizza un orario indietro di un'ora.

Obiettivo: ricavare l'orario locale Europe/Rome dalla data/ora GNSS valida,
gestendo ora solare, ora legale e cambio di giorno, con lo stesso risultato
sui due dispositivi. Evitare una correzione fissa di +1 ora valida soltanto
in una parte dell'anno. Non cambiare epoche GNSS, frequenza o tempi di gara.

Verifica hardware prevista: confronto RLCD/Guition con istanti UTC noti in inverno,
estate, transizioni dell'ora legale e attraversamento della mezzanotte.

## 2. Data e progressivo nei nomi dei file — implementato in RC2, da collaudare

Segnalazione: il nome RC1 conteneva anno/mese e progressivo, ma non il giorno.
RC2 adotta `TA06NO01.CSV`: TA circuito, 06 giorno, NO mese, 01 progressivo
per lo stesso circuito/giorno. Nessun nome esistente è sovrascritto.

Obiettivo: generare il nome dalla data effettiva di inizio registrazione,
con un progressivo sessione distinto dalla data. Definire una convenzione
comune ai due dispositivi e compatibile con FAT, esportazione e Manager;
non sovrascrivere file esistenti. I file già registrati devono rimanere leggibili.

Verifica hardware prevista: più sessioni nello stesso giorno, giorno successivo,
riavvio, cambio mese/anno, anno bisestile e registrazione iniziata senza
una data GNSS valida. I nomi devono restare univoci anche dopo un riavvio.

## 3. Data esatta di registrazione nei dettagli del file — implementato in RC2, da collaudare

Obiettivo: conservare data e ora reali di inizio registrazione e mostrarle
nei dettagli della sessione/file, mantenendole dopo riavvio ed esportazione.
Verificare anche i timestamp FAT visualizzati dal PC: la data di copia o
esportazione non deve essere presentata come data di acquisizione.

Data e ora devono riferirsi allo stesso istante usato per il nome del file,
con una convenzione di fuso orario esplicita. Per vecchi file senza questa
informazione mostrare "data non disponibile", senza inventare una data.

Verifica hardware prevista: confronto con l'ora reale di registrazione su dispositivo,
file esportato e dettagli nel Manager/PC; riapertura di file storici.

## Fasi successive al collaudo RC2

Le fasi seguenti sono pianificate, in questo ordine, dopo realizzazione e
collaudo di RC2 su RLCD e Guition. Non sono implementate in RC2; il loro
inserimento nella roadmap non modifica lo stato delle prove hardware RC2.

### Fase 1. RLCD: riavvio da USB Mass Storage — da fare

Consentire di riavviare RLCD dopo l'ingresso in modalità USB Mass Storage
premendo **uno qualsiasi dei due tasti esistenti**, KEY o BOOT, senza dover
spegnere il dispositivo o scollegare l'alimentazione.

Prima del riavvio, richiedere l'espulsione sicura della scheda dal PC e
completare gli I/O pendenti; gestire il distacco USB senza interrompere
scritture in corso. Il successivo avvio deve tornare alla normale modalità
laptimer, senza rientrare automaticamente in Mass Storage.
Gestire debounce e tasti già premuti all'ingresso per evitare riavvii involontari.

Verifica prevista: leggere/copiare file tramite MSC, espellere dal PC e
provare separatamente KEY e BOOT. Controllare riavvio normale, integrità dei
file e nuova registrazione; verificare anche pressione prolungata e tasto
mantenuto premuto all'ingresso in MSC.

### Fase 2. RLCD e Guition: aggiornamento OTA Wi-Fi su richiesta — da fare

Aggiungere per **entrambi i dispositivi** una voce nel menu delle opzioni
per attivare la modalità di aggiornamento firmware tramite OTA Wi-Fi.
Il Wi-Fi deve essere **spento all'avvio e durante il normale uso**: niente
connessione permanente o attivazione automatica della radio.

L'ingresso in modalità aggiornamento deve essere esplicito e avvenire a
gara/registrazione ferme, dopo la chiusura delle eventuali sessioni.
Mostrare stato della connessione e dell'aggiornamento; prevedere uscita
manuale e spegnimento della radio per inattività. Dopo uscita o riavvio,
il Wi-Fi deve tornare spento.

Definire configurazione della rete e credenziali OTA senza inserire segreti
nei sorgenti pubblici. Verificare compatibilità con ESPHome, dimensioni delle
partizioni/immagini e recupero da aggiornamento interrotto prima di abilitare
questa funzione sulle release distribuite.

Verifica prevista su entrambi: abilitazione dal menu, aggiornamento riuscito,
rete assente, connessione persa e interruzione dell'aggiornamento. Controllare
che i dati registrati restino disponibili, che il Wi-Fi si spenga all'uscita
e che tempi giro e acquisizione GNSS a 25 Hz restino allineati alla base.

### Fase 3. Valutazione delle interazioni con action cam — da valutare

Studiare possibili integrazioni con **GoPro, Insta360 e altre action cam**,
partendo da modelli e protocolli effettivamente supportati. L'obiettivo di
questa fase è una valutazione di fattibilità, non una promessa di compatibilità
con tutte le camere o un'implementazione già prevista in RC2.

Casi d'uso da valutare: avvio/arresto della registrazione in relazione alla
sessione del laptimer, marcatori di giro/evento e sincronizzazione fra video
e telemetria. Confrontare disponibilità di API/SDK, Wi-Fi/Bluetooth o altri
collegamenti supportati, limiti dei modelli, riconnessione e comportamento
quando la camera è assente o non risponde.

Esito atteso: matrice di compatibilità per modello e funzione, scelta di un
primo caso d'uso e piano di prova. Misurare impatto su consumi, memoria e
latenza; l'eventuale integrazione deve restare opzionale e non compromettere
cronometraggio, logging GNSS o modalità OTA.

## Vincoli comuni

Preservare il comportamento di cronometraggio allineato in RC1, i parametri
GNSS e la compatibilità dei dati. Verificare le correzioni su entrambi i
dispositivi con sessioni confrontabili prima di promuovere la release successiva.
