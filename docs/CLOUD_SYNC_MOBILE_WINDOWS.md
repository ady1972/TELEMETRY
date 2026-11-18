# Sessioni e circuiti: cartella comune Android/Windows

Richiede **Android V0.2.3** e **Windows V5.4.15.7**. Le versioni precedenti
rimangono disponibili, ma il nuovo scambio dei circuiti richiede entrambe.

1. Creare una cartella dedicata nel servizio cloud e renderla disponibile sul PC
   tramite il relativo client (Google Drive, OneDrive, Dropbox, Synology Drive).
2. Sul PC aprire Importa Sessioni → Cloud Sync e scegliere quella cartella.
3. Sul telefono aprire Sessioni → SYNC WINDOWS → CARTELLA CONDIVISA e scegliere
   **la stessa cartella**, con accesso persistente in lettura e scrittura.
4. Premere SINCRONIZZA ORA sui due dispositivi dopo che il client cloud ha
   completato il trasferimento. Sessioni importate e circuiti appaiono negli
   archivi locali; un errore lascia i dati originali disponibili.

Il provider Android deve supportare `ACTION_OPEN_DOCUMENT_TREE` e la creazione
lettura/scrittura dei documenti. Non tutti i servizi/app offrono tale accesso:
non basta installare il client. Se la cartella non è selezionabile, usare una
cartella locale sincronizzata o un provider compatibile. Non sono presenti
integrazioni OAuth o API native per i singoli servizi.

## Contenuto condiviso

- File sessione originali CSV/GRT/GSA/BIN e JSON sessione riconosciuti, nella
  radice. Nuovi nomi includono SHA-256; stesso nome e dati diversi restano distinti.
- Revisioni JSON dei circuiti in `circuiti/`. Sono buste di sincronizzazione,
  non file da caricare direttamente sul laptimer. L'editor usa i JSON normali
  nell'archivio locale e mantiene export/cataloghi/trasferimenti precedenti.
- Database SQLite, note, credenziali AssistNow e impostazioni non sono copiati.
  Non scegliere il database SQLite come oggetto da condividere.

I motori esistenti importano i formati storici; un JSON non riconosciuto come
sessione viene ignorato. Errori di parsing vengono segnalati e ritentati al sync
successivo; solo importazioni riuscite vengono marcate. Nessun dato GPS personale
è incluso nei test o negli esempi della release.

## Offline, conflitti ed eliminazioni

Android avvia il sync manualmente o, se abilitato, dopo importazioni/salvataggi
locali. Per ricevere aggiornamenti PC senza modifiche locali usare il pulsante.
Windows verifica i nuovi file ad ogni avvio, anche con sync periodico spento,
e pubblica i file copiati nelle importazioni. Il controllo ogni 15 secondi
è opzionale mentre il Manager rimane aperto.
La velocità effettiva dipende anche dal trasferimento del provider cloud.

Revisioni concorrenti dello stesso circuito sono conservate come varianti
`(conflitto …)`: controllarle nell'editor e salvare esplicitamente la versione
preferita dopo aver ricevuto tutte le varianti. Non si sceglie il vincitore
in base all'orologio dei dispositivi. Le copie già modificate non vengono
sovrascritte. Le eliminazioni dei circuiti non sono propagate: un circuito eliminato può
ricomparire. Da Windows V5.4.15.7 il comando Elimina rimuove invece le sessioni
e i file gestiti e condivisi, dopo conferma. Android V0.2.3 riceve la rimozione
al sync successivo e non ripubblica la propria copia. `sessioni_eliminate/`
contiene ricevute per SHA-256 che vanno mantenute anche quando il cloud non
contiene più il file originale. Le rimozioni avviate solo dall'interfaccia Android
mantengono il comportamento locale precedente. Non è previsto il ripristino
automatico di sessioni eliminate.

Il trasferimento pubblica nuovi file senza troncare quelli già esistenti,
verifica SHA-256 e conserva una cache privata delle revisioni. I file incompleti
con nome contenente hash o revisioni corrotte sono segnalati e ignorati; attendere
la fine del trasferimento e riprovare. I provider reali e l'esecuzione su telefono
richiedono ancora collaudo: i test automatici usano cartelle temporanee e dati
sintetici, bridge Python/SQLite reali e seriale GNSS simulata.

Le note aggiunte nel database non vengono sincronizzate. I file sessione originali
conservano tutti i campi già presenti all’origine, incluse eventuali note in un
JSON esportato e poi importato come file.

## File Windows e archivi storici

Il Manager copia gli originali importati in `session_files/` nell'archivio scelto
nelle Impostazioni e usa copie con nome contenente SHA-256. Deduplica per contenuto
anche importando lo stesso file da percorsi diversi. All'avvio copia anche le
sorgenti disponibili delle sessioni storiche senza sostituire ID o note.
Se rimane soltanto il database e l'originale non esiste più, segnala la mancanza:
quella sessione resta consultabile sul PC, ma il file non è ricostruito per il sync.

Un file JSON può contenere più sessioni: eliminare il file le coinvolge tutte;
la conferma Windows ne mostra il numero. Sorgenti al di fuori dell'archivio e
della cartella cloud e file sulla microSD non vengono eliminati. File bloccati
o provider non disponibile generano un avviso e vengono ritentati al sync.
