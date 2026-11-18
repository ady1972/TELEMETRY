# RC3 — Wi-Fi, aggiornamento firmware e sessioni sull'app mobile

## Obiettivo concordato per il prossimo sviluppo

Per entrambi i laptimer, RLCD 4.2 e Guition 4.3:

1. Gestire gli aggiornamenti firmware tramite Wi-Fi, attivandoli dal menu.
2. Trasferire le sessioni salvate all'app Android GOATS Mobile tramite Wi-Fi.

Questo documento definisce il lavoro RC3. Nessuna funzione RC3 è già
implementata o collaudata con questa modifica documentale. I firmware RC2
restano invariati. Il prossimo sviluppo parte dalla baseline RC2 verificata,
con cartelle e configurazioni RC3 separate.

## Punto di partenza verificato

L'app `mobile/v0.2.1` contiene già il client Wi-Fi in
`fullapp/src/main/java/com/goatsrt/manager/LapTimerTransferManager.kt`.
La schermata di importazione in `ManagerActivity.kt` permette ricerca,
selezione multipla, download, archivio locale e importazione nel database.
L'indirizzo predefinito è `http://192.168.4.1`, modificabile nell'app.
Il client non dimostra che i laptimer RC2 offrano già quel servizio:
nei relativi YAML non sono attivi Wi-Fi, server per le sessioni o OTA.

L'OTA non è implementata da quel client Android. Occorre predisporre anche
il percorso di aggiornamento dal browser o da un client compatibile,
oltre al servizio firmware. L'importazione delle sessioni e l'OTA sono due
funzioni distinte che possono condividere la connessione Wi-Fi.

## Uso proposto

Nelle impostazioni di entrambi i dispositivi, voce **Wi-Fi** con:

- **Trasferisci sessioni**: il laptimer attiva la rete, il telefono si collega,
  nell'app si cercano e si importano le sessioni desiderate.
- **Aggiorna firmware**: il laptimer attiva il servizio di aggiornamento,
  mostra le istruzioni e l'avanzamento, poi riavvia sulla nuova versione.
- **Disattiva Wi-Fi / Indietro**: chiude i servizi e torna all'uso ordinario.

La proposta di prima implementazione è una rete locale creata dal laptimer
(access point), coerente con l'indirizzo già previsto nell'app. Deve funzionare
anche ai box senza router o Internet. Connessione a una rete esistente o hotspot
del telefono resta un'estensione da valutare, non una dipendenza della RC3.

La radio resta spenta all'avvio e durante cronometraggio/registrazione. Le due
funzioni si attivano solo su richiesta e a sessione terminata; entrando nel menu
Wi-Fi non si termina o scarta automaticamente una sessione. Uscita manuale e
inattività spengono la radio; dopo riavvio non si riattiva automaticamente.
Aggiornamento firmware, trasferimento dei file e USB Mass Storage devono avere
stati coordinati per evitare accessi concorrenti alla scheda.

## Trasferimento delle sessioni: compatibilità con l'app esistente

La prima versione deve offrire almeno:

| Richiesta dell'app | Risposta del laptimer |
|---|---|
| `GET /api/sessions` | Elenco JSON delle sessioni salvate |
| `GET /api/sessions/{id}/download` | File della sessione richiesta, in un formato verificato con l'importatore Android |

L'app riconosce un array JSON oppure un oggetto con campo `sessions`.
I metadati già letti dal client sono `id`, `name`, `track`, `date`, `time`,
`format`, `size` e `download_url`; esistono alias, ma il firmware deve usare
un contratto comune ai due modelli, senza affidarsi ai tentativi alternativi.
Non si aggiungono endpoint ad hoc diversi per RLCD e Guition.

Requisiti del trasferimento:

- Elencare solo registrazioni chiuse e conservare gli originali sul laptimer.
- Trasferire i dati necessari per giri, settori, velocità e traiettoria; non
  equiparare un solo riepilogo compatto alla sessione completa a 25 Hz.
- Verificare l'importazione effettiva del formato scelto (GSA/CSV o altro già
  supportato) con i parser reali dell'app prima di dichiarare compatibilità.
- Usare identificativi stabili e distinguere le sessioni dei due dispositivi.
- Non cancellare sessioni in conseguenza di download, errore o interruzione.
- Misurare anche una sessione da un'ora: trasferimento a blocchi lato firmware,
  UI reattiva, file completo e integrità verificabile sul telefono.
- Gestire riconnessione e nuova importazione senza dati parziali o duplicati
  non segnalati. Il client attuale legge il file interamente e non implementa
  ripresa a blocchi o confronto esplicito dell'hash: tali capacità non vanno
  considerate già presenti e possono richiedere un incremento dell'app.

Il flusso esistente è richiesto dal telefono: per l'utente le sessioni arrivano
nell'app, ma il laptimer non invia dati a un'app non collegata. Il cloud resta
una funzione facoltativa separata dell'app, non un requisito del trasferimento.

## Aggiornamento firmware Wi-Fi

- Avvio esplicito dal menu e accesso protetto; credenziali configurate o generate
  per dispositivo, senza password comuni o segreti nei sorgenti pubblici.
- Individuazione chiara del modello e della versione: entrambi usano ESP32-S3,
  quindi riconoscere soltanto il chip non basta a distinguere RLCD da Guition.
- Verifica di destinazione, integrità e dimensione dell'immagine prima di
  accettare l'aggiornamento; conservazione delle sessioni e delle preferenze.
- Controllo del layout flash e degli slot OTA sulle schede reali. Nei YAML
  attuali RLCD dichiara 16 MB, Guition 4 MB: non assumere lo stesso margine
  disponibile né aumentare la flash dichiarata per far entrare l'immagine.
- Verifica dell'esito dopo riavvio e qualifica del recupero per upload interrotto
  o nuova immagine non avviabile. Il rollback non va dichiarato disponibile
  prima di aver verificato bootloader, partizioni e impostazioni effettive.

Il primo caricamento della RC3 partirà ancora da USB, perché RC2 non dispone
oggi del servizio OTA. USB deve rimanere disponibile anche come recupero.

## Ordine di implementazione e prove

1. **Base Wi-Fi comune**: rete locale su richiesta, stato nel menu, spegnimento
   all'uscita/inattività e blocco durante registrazione o possesso SD via USB.
2. **Sessioni sull'app**: API comuni, file reali da entrambi i modelli, importazione
   Android end-to-end con più sessioni e una registrazione da un'ora.
3. **Aggiornamento Wi-Fi**: percorso di caricamento e verifica immagine per
   ciascun modello, persistenza dei dati e recupero dagli errori.
4. **Collaudo combinato**: tornare a Racing dopo trasferimento/aggiornamento,
   effettuare più sessioni, controllare tempi, delta, settori e registrazione
   a 25 Hz rispetto alla baseline RC2.

Le fasi 2 e 3 possono essere sviluppate separatamente dopo la base comune;
l'ordine indicato è operativo, non una promessa di funzioni già disponibili.
I criteri di uscita richiedono compilazioni separate, test software e prove
reali su RLCD, Guition e telefono Android. Un server simulato non certifica
il trasferimento dal dispositivo o il successo dell'OTA.

Le consegne conterranno due ZIP distinti. Nella radice di ciascuno ci saranno
lo YAML RC3 e la propria cartella di riferimento, affiancati e pronti da copiare
nella cartella ESPHome. Nessun flash, attivazione radio o rilascio è eseguito
con questo documento.
