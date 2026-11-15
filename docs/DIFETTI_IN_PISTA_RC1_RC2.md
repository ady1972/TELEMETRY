# Difetti rilevati in pista — RC1 e stato delle correzioni RC2

Questa nota raccoglie le segnalazioni dell'utente e le verifiche software effettuate nella discussione successiva alle prove. Per RLCD l'utente ha confermato esplicitamente RC1; il confronto Guition è riferito alla stessa discussione, senza identificativo completo del firmware installato.

**Aggiornamento RC2.1:** le correzioni descritte sotto e la diagnostica sono ora incluse nel ramo `feat/rc2-1-screen-mode`, insieme alla modalità schermata persistente. L’esito della compilazione è registrato in `docs/MODALITA_SCHERMATA.md`; non sono ancora provate sui dispositivi. RC1 rimane invariata. I PASS software non equivalgono a un collaudo in pista.

Baseline della repository verificata: `d61e8a62f1cc4f4322e215147eba2fe86e88d49f`.

## Riepilogo delle nuove segnalazioni

| ID | Dispositivo | Difetto osservato | Esito dell'analisi | Stato |
|---|---|---|---|---|
| PISTA-01 | RLCD RC1 | Circa un minuto di attesa dopo conferma di «SALVA E TERMINA», per una sessione da un'ora | Timeout automatico escluso; fase lenta non ancora identificata | Aperto; diagnostica locale preparata |
| PISTA-02 | RLCD RC1 | Dopo il primo salvataggio il traguardo non viene più riconosciuto; necessario riavviare | Pausa permanente lasciata dalla chiusura, riprodotta nel codice | Correzione locale RC2 e test software PASS; build e prova hardware pendenti |
| PISTA-03 | Guition | Delta meno preciso di RLCD, con oscillazioni anche lontano dai settori | Riprodotto un difetto del filtro con campioni aventi lo stesso timestamp software; incidenza sul dispositivo ancora da verificare | Correzione locale Guition RC2 e test software PASS; build e prova hardware pendenti |

## PISTA-01 — RLCD: salvataggio lento

**Osservazione:** la conferma manuale di «SALVA E TERMINA» è seguita da circa un minuto di attesa. La sessione dura circa un'ora.

**Verifiche:** il ritardo non è l'attesa automatica di 60 secondi dall'ultimo movimento. Il CSV viene scritto durante la registrazione, con sincronizzazione ogni 25 punti. Alla chiusura non vengono riscritti tutti i 90.000 campioni di un'ora: si svuota una coda limitata a 511 punti, poi si chiude e rinomina il file e si aggiorna la sessione NVS. RC2 aggiunge anche mappa ID e timestamp.

**Intervento locale:** aggiunti log INFO `SAVE_DIAG` in RC2 per misurare separatamente coda residua, chiusura CSV, ricerca del nome, rinomina, mappa ID, timestamp, aggiornamento NVS e durata totale del comando. Il log preesistente `GPS_TRACE` escludeva lo svuotamento della coda.

**Non ancora risolto:** nessuna misura su SD reale identifica l'operazione che occupa il minuto. Non attribuire il ritardo a SD, NVS o coda senza log. Il precedente test host Guition da 90.000 punti non misura la latenza RLCD.

**Verifica necessaria:** predisporre una build verificata e l'accesso ai log UART0, quindi acquisire una chiusura lenta e confrontare le durate delle fasi. Controllare integrità e completezza del CSV.

## PISTA-02 — RLCD: mancata ripartenza dopo salvataggio

**Osservazione:** dopo il primo salvataggio la telemetria non riconosce più il traguardo; riparte soltanto dopo riavvio.

**Causa riprodotta:** `goats_menu::finish()` chiama `goats_session_ctl::stop()`, impostando `paused=true`. Nessun percorso della baseline richiamava `resume()`. Il ponte al cronometro ignora quindi i campioni successivi. Il difetto è presente anche nella baseline RC2.

**Correzione locale RC2:** richiamo di `resume()` dopo chiusura, reset e passaggio alla sessione successiva. L'acquisizione torna disponibile, ma il giro non parte automaticamente: serve un nuovo attraversamento del traguardo.

**Verifica software:** prova host con finalizzatore del menu, ponte racing e motore reali. Fallimento prima della correzione, PASS dopo: due salvataggi consecutivi e uno scarto, ciascuno seguito da nuovo attraversamento e giro cronometrato senza reboot. Uno scarto rifiutato conserva la sessione attiva. SD e NVS sono simulate in questa prova.

**File locali interessati:** `firmware/rlcd-42/GOATS_RLCD_RC2/goats_legacy_menu_ui.h`; prova `tests/rc2/test_rlcd_restart.py`.

**Verifica necessaria:** compilazione ESP32 e più sessioni consecutive sullo stesso circuito senza riavvio; controllare tempi giro, nuovi file e integrità delle sessioni precedenti. Non considerare questa correzione una soluzione alla lentezza di PISTA-01.

## PISTA-03 — Guition: delta oscillante

**Osservazione:** il delta oscilla anche lontano dai passaggi di settore, risultando meno preciso di RLCD.

**Confronto:** nella baseline RC1 i due dispositivi condividono il motore di calcolo, inclusi matching sul punto più vicino del Best Lap e filtro temporale da 1 secondo. Guition visualizza anche il delta settore per 5 secondi e aggiorna il riquadro ogni 200 ms, contro i 100 ms del display RLCD. Queste differenze da sole non spiegano la segnalazione lontano dai settori.

**Difetto riprodotto:** i campioni Guition ricevono `millis()` alla decodifica. Se più epoche vengono elaborate nello stesso millisecondo, il ramo `dt <= 0` del filtro assegna il delta spaziale non filtrato, provocando salti. Il comportamento esiste nel motore comune; la frequenza effettiva di questa condizione sui due dispositivi non è stata misurata.

**Esperimento software, non misura in pista:** una traiettoria circolare identica ripetuta a 25 Hz, senza rumore GPS, produce circa 0,00158 s di escursione con letture regolari. Raggruppando artificialmente la decodifica ogni 200 o 400 ms, l'escursione sale rispettivamente a 0,2 o 0,4 s.

**Correzione locale nel solo Guition RC2:** a timestamp uguale mantenere il valore filtrato; applicare il filtro al successivo avanzamento del tempo. Non modifica configurazione GNSS, epoche, tempi giro/settore, formato CSV, matching spaziale o costante del filtro. Il motore RLCD resta invariato.

**Verifica software:** prova che fallisce prima e passa dopo la modifica. Sulla traiettoria identica raggruppata i salti scompaiono. Una prova con giro rallentato da 60 a 66 secondi verifica che il delta continui a reagire a una perdita reale, senza congelarsi.

**File locali interessati:** `firmware/guition-43/goats_guition_43_rc2/goats_laptimer.h`; prova `tests/rc2/test_guition_delta.cpp`.

**Verifica necessaria:** compilazione ESP32 e confronto in pista; misurare intervalli di decodifica, continuità iTOW e stato della coda. Il difetto riprodotto è una possibile componente delle oscillazioni, non prova che ogni oscillazione reale sia eliminata.

## Anomalie precedenti già affrontate nella baseline RC2

Queste voci provengono dalla [roadmap esistente](../ROADMAP.md), non sono nuove segnalazioni hardware RC2:

| Anomalia | Intervento già presente nella baseline RC2 | Verifica ancora richiesta |
|---|---|---|
| Orario RLCD indietro di un'ora | Conversione UTC → Europe/Rome con CET/CEST e gestione del cambio data | Confronto su dispositivo fra ora locale e riferimento noto |
| Nomi delle registrazioni senza giorno corretto | Formato comune `PPDDMMNN.CSV`, per esempio `TA06NO01.CSV`, progressivo e protezione dalle sovrascritture | Più sessioni, cambio giorno, riavvio, collisioni e date mancanti |
| Data nei dettagli/proprietà non rappresentativa dell'inizio registrazione | Data iniziale conservata nei metadati; gestione esplicita dei dati mancanti e timestamp FAT | Confronto fra dettagli, CSV, Manager e PC; la data di creazione sul PC può dipendere dalla copia |

Dettagli della baseline: [note RLCD RC2](../firmware/rlcd-42/GOATS_RLCD_RC2/RC2.md) e [note Guition RC2](../firmware/guition-43/goats_guition_43_rc2/RC2.md).

## Richiesta per le versioni da testare — riepilogo giri per sessione

Per **RLCD e Guition**, predisporre un riepilogo consultabile dei giri di ciascuna sessione. Ogni giro deve riportare:

| Giro | Tempo giro | Velocità media | Velocità massima |
|---|---|---|---|
| Numero del giro | Minuti, secondi e millesimi | km/h, riferiti al singolo giro | km/h, riferiti al singolo giro |

Nel riepilogo mostrare solo queste tre misure, oltre al numero del giro per identificare la riga; gli altri indicatori e riferimenti statistici sono esclusi da questa vista. Le tre misure richieste sono tempo giro, velocità media e velocità massima; non usare media o massima dell'intera sessione come sostituti dei valori del singolo giro.

**Ambito della richiesta:** il riepilogo delle sessioni archiviate nelle versioni candidate al prossimo test di entrambi i dispositivi. Questa nota registra un requisito da implementare, non una funzione già completata.

**Situazione attuale verificata:** Guition dispone già dei tre valori per giro, con ulteriori informazioni e riferimenti nel riepilogo. RLCD visualizza tempo e media; il record archivio dei giri non conserva la velocità massima, che va quindi acquisita e persistita in modo compatibile.

**Criteri di verifica:**

- Consultare tutti i giri conservati della sessione, con scorrimento quando necessario e ritorno all'elenco delle sessioni.
- Verificare i tre valori su più giri con velocità diverse, evitando che dati del giro successivo alterino quello appena concluso.
- Conservare i dati dopo salvataggio e riavvio; mantenere leggibili le registrazioni esistenti.
- Per vecchi archivi privi della massima, mostrare “—” senza inventare valori o usare la massima di sessione.
- Preservare tempi giro, acquisizione a 25 Hz, CSV e protocollo Manager. Eventuali estensioni della persistenza richiedono compatibilità con gli archivi precedenti.
- Verificare leggibilità sui due display mantenendo lo stile di ciascun dispositivo.

La semplificazione richiesta riguarda la presentazione del riepilogo; non implica la cancellazione dei dati storici.

## Validazione complessiva e lavoro residuo

La suite locale `python tests/rc2/run.py` passa anche con le nuove prove di ripartenza RLCD e filtro Guition. Le prove host usano adattatori per le dipendenze hardware e non misurano i tempi elettrici della microSD.

Prima di dichiarare risolti i difetti in pista:

1. Pubblicare e revisionare separatamente le modifiche locali al firmware e i relativi test.
2. Compilare le revisioni aggiornate per entrambi i dispositivi; le build PASS della baseline non qualificano queste modifiche.
3. Identificare la fase lenta di PISTA-01 con misure hardware e intervenire sulla causa.
4. Collaudare salvataggi e ripartenze consecutive RLCD e verificare stabilità/risposta del delta Guition.
5. Aggiornare questa nota con versione esatta, risultati e problemi residui.

Nessun flash, rilascio firmware o collaudo hardware delle nuove modifiche è stato eseguito durante questa analisi.
