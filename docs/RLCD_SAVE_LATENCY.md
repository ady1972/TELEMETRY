# RLCD: diagnosi lentezza salvataggio

Segnalazione utente: circa un minuto dopo la conferma di SALVA E TERMINA
per una sessione da un'ora. Versione installata: RC1, confermata dall’utente.
Il timeout automatico di 60 secondi non spiega l'attesa dopo conferma manuale.

Analisi del codice RC2: il CSV viene scritto durante la sessione, con sync
ogni 25 punti. Alla chiusura si svuota una coda di massimo 511 punti,
poi si chiude/rinomina il file, si salva la mappa ID, si imposta il timestamp
e si aggiorna l'ID NVS. Non viene riscritta l'intera traccia.
Il tempo reale delle operazioni SD e NVS non è determinabile con adapter RAM.
Il log GPS_TRACE preesistente esclude lo svuotamento della coda.

Il ramo locale diagnose/rlcd-session-save-latency aggiunge log INFO SAVE_DIAG:
menu begin/done, trace begin/done, drain done, CSV close, name, rename,
map, timestamp, next session. Le durate sono in millisecondi; trace begin
riporta punti e coda residua. Le fasi completate riportano la durata;
in caso di blocco l'ultima riga begin individua l'operazione in corso.
I log non sono emessi per campione, non modificano CSV o protocollo Manager.
Sono diagnostica, non una correzione della causa ancora ignota.

Validazione: python tests/rc2/run.py PASS dopo le modifiche.
Compilazione ESP32 non eseguita: ESPHome non disponibile nel workspace.
Nessun flash, caricamento GitHub o test hardware eseguito.

Prossima verifica: identificare la versione firmware installata e acquisire
il log UART0 durante una chiusura lenta. RC2 riserva USB_SERIAL_JTAG al
Manager: i log INFO sono configurati su UART0. Prima di richiedere una prova
occorre predisporre build verificata e accesso al canale di log sul dispositivo.

## Confronto RC1/RC2

Svuotamento della coda (massimo 511 punti), sync ogni 25 punti, chiusura
FatFS e chiamante del menu sono condivisi dalle due versioni nella baseline.
RC2 cambia naming, date, recupero e aggiunge mappa ID/timestamp, ma non
introduce una correzione dimostrata della latenza segnalata su RC1.
Non attribuire l’attesa di RC1 alle nuove operazioni di RC2.
La durata della registrazione non implica 90.000 punti ancora da scrivere:
la coda è limitata e il resto è scritto durante l’acquisizione.
Restano da misurare coda residua, latenze FatFS/SD, ricerca nomi e NVS.

## Ripartenza dopo chiusura

Seconda segnalazione RC1: il traguardo non è più riconosciuto dopo il primo
salvataggio fino al reboot. Causa riprodotta anche sulla baseline RC2:
`goats_menu::finish` chiama `stop()` lasciando `paused=true`; nessun chiamante
richiamava `resume()`. Il ponte racing ignora quindi i campioni successivi.
Correzione locale RC2: `resume()` dopo reset e passaggio all'ID successivo.
Prova host del menu/ponte/motore reale RED prima, GREEN dopo la correzione.
La prova verifica nuovi attraversamenti e giri dopo save/save/discard.
Questo risolve il blocco logico in host, non dimostra la causa della latenza.

Aggiornamento RC2.1: test host e compilazioni complete di entrambi i firmware
PASS nei controlli GitHub sul commit af03d359b9f987054a96473f837623946c1f7eec.
Questa verifica supera lo stato di compilazione pendente riportato nelle
annotazioni iniziali. Collaudo hardware ancora da eseguire; nessun flash.
Dettagli: docs/MODALITA_SCHERMATA.md.
