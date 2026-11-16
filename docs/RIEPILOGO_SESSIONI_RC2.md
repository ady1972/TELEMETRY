# RC2.2 — riepilogo sessioni RLCD e Guition

Per ogni giro conservato della sessione, il riepilogo mostra:

- numero del giro;
- tempo giro, con millesimi;
- velocità massima del singolo giro, in km/h;
- velocità media del singolo giro, in km/h.

Il miglior tempo positivo fra i giri conservati della sessione è evidenziato
con la scritta BEST. In caso di parità sono evidenziati tutti i giri migliori.
Guition usa una riga verde; RLCD usa una riga invertita con indicatore BEST.
Il cursore RLCD mantiene il prefisso > per distinguerlo dal best lap.

Su Guition sono rimossi dal riepilogo i dettagli S1/S2/S3, le righe vuote per
i settori e il pannello delle statistiche aggregate di sessione. Rimane il
contesto data/ora e circuito. I dati dei settori non vengono cancellati:
registrazione, protocollo Manager e schermata racing restano disponibili.
La lista scorre verticalmente; cambiando sessione riparte dall'inizio.

Su RLCD vengono mostrate tre righe doppie alla volta, navigabili con i tasti;
la pagina del singolo giro riporta gli stessi tre valori e l'eventuale BEST.
La massima è acquisita in RAM dai campioni validi del giro e salvata insieme
al giro, fuori dal consumatore GPS. Un record NVS ausiliario, legato a
sessione/numero/durata del giro, mantiene la compatibilità del Record storico.
La cache dei dati ausiliari evita letture NVS ripetute durante il disegno.
Cancellazione e rotazione dell'archivio mantengono l'associazione corretta.

Gli archivi storici RLCD privi della massima restano leggibili e mostrano
MAX --. Il valore non viene sostituito con la massima della sessione e non
viene ricostruito bloccando la schermata con una scansione completa del CSV.
Restano i limiti di conservazione esistenti: 80 giri nel journal RLCD e
80 giri per sessione Guition. Non vengono recuperati giri già eliminati.

## Validazione

La suite `python tests/rc2/run.py` include prove di:

- massima distinta per giro e gestione di campioni non validi;
- persistenza e ricarica dei record ausiliari RLCD dopo riavvio;
- vecchi archivi, metadati mancanti/troncati o relativi a un altro giro;
- cancellazione della sessione e oltre una rotazione completa dei 80 slot;
- valori per giro Guition, rimozione delle righe dei settori, evidenziazione
  delle parità e pulizia della vecchia evidenziazione al cambio di sessione;
- regressioni RC2 già esistenti, compresi clock, CSV e ripartenze.

Le configurazioni e le compilazioni ESPHome sono verificate separatamente.
Nessun flash o collaudo sui display reali è eseguito durante lo sviluppo.
Prima dell'uso in pista: controllare più giri con velocità diverse, scorrimento,
parità, riavvio e cancellazione su entrambi i dispositivi, inclusi vecchi dati.

I file e le cartelle conservano il nome RC2; progetto e informazioni firmware
identificano questa revisione come RC2.2. RC1 resta invariata. La modalità
schermata DELTA/LAP TIME introdotta in RC2.1 resta disponibile.

Esito software della revisione: suite RC2 PASS, prova del renderer Guition
PASS, invarianti e integrazione della versione Guition V1.0.22 storica PASS.
Compilazioni complete RLCD e Guition con ESPHome 2026.7.3 / ESP-IDF 5.5.5:
PASS. Nessun collaudo hardware; i due ZIP consegnati contengono i sorgenti.
