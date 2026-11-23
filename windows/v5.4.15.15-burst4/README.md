# GOATS Windows — Manager V5.4.15.15 BURST4

Progetto completo derivato dalla [V5.4.15.10](../v5.4.15.10-burst4/README.md).
Le versioni precedenti sono conservate nelle rispettive cartelle.

## Animazione dei giri

In **Analisi**, accanto ad **ANIMA GIRI**, il selettore Velocità offre **0,5x,
1x, 2x, 5x e 10x**. Le stesse opzioni sono disponibili nella mappa a schermo
intero, che riprende la velocità scelta nella pagina Analisi.

Si può cambiare velocità durante la riproduzione mantenendo il punto raggiunto.
Nel fullscreen **S** passa ciclicamente alla velocità successiva; dopo 10x torna
a 0,5x. Play/Pausa, Reset e le altre scorciatoie mantengono il funzionamento.
La velocità iniziale rimane 1x.

## Sessioni e circuiti con Android

Con Android **V0.2.3**, selezionare su entrambi i dispositivi la stessa cartella
cloud. Sul PC: **Importa Sessioni → Cloud Sync → SINCRONIZZA ORA**.
L'opzione automatica controlla la cartella ogni 15 secondi mentre il Manager è
aperto. Usare una cartella locale gestita dal client cloud; non condividere il
file SQLite. Nel telefono è richiesto un provider con accesso alle cartelle.

I file originali delle sessioni sono deduplicati per SHA-256; i circuiti usano
revisioni JSON nella sottocartella `circuiti/`. Le modifiche concorrenti sono
conservate come varianti. Note, database, impostazioni e credenziali rimangono
locali. Le eliminazioni delle sessioni dal Manager rimuovono i relativi file
e vengono ricevute anche dal Mobile V0.2.3 al sync successivo. Vedere la
[guida operativa](../../docs/CLOUD_SYNC_MOBILE_WINDOWS.md).

## Importazione, avvio e cancellazione dei file

- Ogni importazione copia gli originali in `session_files/` nell'archivio sessioni
  configurato. Il database punta alla copia gestita, disponibile anche dopo aver
  scollegato la microSD. Con Cloud Sync configurato, i file vengono pubblicati
  dopo l'importazione anche se il controllo periodico è disattivato.
- Ad ogni apertura il Manager controlla la cartella condivisa, importa i nuovi
  file nel proprio database e mantiene gli ID e le note delle sessioni già note.
  L'opzione ogni 15 secondi serve per ricevere altri aggiornamenti mentre è aperto.
- Le sessioni storiche vengono collegate a copie gestite quando gli originali
  indicati nel database sono ancora disponibili. Le sorgenti mancanti sono
  segnalate; le sessioni nel database non vengono cancellate né ricostruite.
- **Elimina** chiede conferma e rimuove le voci dal database e i file con lo stesso
  contenuto nell'archivio e nella cartella condivisa. Se un file contiene più
  sessioni, la conferma indica che saranno eliminate tutte quelle del file.
  Non vengono rimossi sorgenti esterni a queste cartelle o file sulla microSD.
- Una ricevuta in `sessioni_eliminate/` evita che un telefono offline ripubblichi
  la vecchia copia. Android V0.2.3 rimuove le sessioni e le sue copie al sync.
  Usare entrambe le nuove versioni: la V0.2.2 non gestisce queste ricevute.
  I circuiti mantengono la gestione dei conflitti e non propagano eliminazioni.
- Errori cloud o file bloccati vengono segnalati; il sync successivo ritenta le
  rimozioni. Non cancellare `sessioni_eliminate/`: contiene lo storico necessario
  a impedire la ricomparsa di file eliminati. Non è implementato il ripristino
  automatico di sessioni cancellate.

## Configurazione GNSS diretta USB-UART

Collegare direttamente il ricevitore MG-902/u-blox M9N tramite USB-UART.
In **GNSS**, scegliere la COM e il baud attuale; leggere la configurazione,
selezionare GPS, Galileo, GLONASS, BeiDou, SBAS e/o QZSS e il protocollo di uscita:

| Uscita UART1 | Messaggi essenziali automatici |
|---|---|
| UBX | NAV-PVT + NAV-DOP a ogni soluzione; NAV-SAT circa 1 Hz |
| NMEA | GGA + RMC |
| UBX + NMEA | NAV-PVT + NAV-DOP; NAV-SAT circa 1 Hz; GGA + RMC |

**NAV-SAT** rende disponibili i dettagli dei satelliti e **NAV-DOP** l'HDOP,
consumati dai firmware Guition/RLCD attuali. Le RC2 sono in ricezione passiva:
leggono questi messaggi ma non li abilitano all'avvio. La routine di setup nel
file header Guition contiene il profilo 25/25/1 Hz, ma non è richiamata dalla RC2.
Per verificare i riferimenti vedere `documentazione/GNSS.md`.

Il Manager legge la frequenza di navigazione prima di applicare il profilo:
a 25 Hz imposta NAV-SAT ogni 25 soluzioni; a 10 Hz ogni 10. Con frequenze
frazionarie arrotonda il divisore verso l'alto. Se la navigazione è più lenta di
1 Hz, NAV-SAT segue quella cadenza. Il log di lettura mostra stato, Hz e divisore.
Cambiare frequenza dal Manager ricalcola il divisore di NAV-SAT se era già attivo;
non lo attiva quando è disabilitato e non abilita UBX in un'uscita NMEA-only.
Il profilo UBX attiva invece automaticamente PVT, DOP e SAT.

Almeno una costellazione principale è richiesta; SBAS/QZSS richiedono GPS in
questo profilo. **APPLICA COSTELLAZIONI E PROTOCOLLO**, **IMPOSTA E SALVA
FREQUENZA** e **IMPOSTA E SALVA BAUD UART1** salvano automaticamente i parametri
in **RAM, BBR e FLASH**. La precedente casella opzionale non è più presente.
Il Manager verifica i valori nei tre livelli, inclusa la flash: NAK, timeout,
valori mancanti o diversi generano un errore e non un messaggio di successo.
Non ripiega silenziosamente su un salvataggio soltanto in RAM.

**LEGGI CONFIGURAZIONE GNSS** legge anche `CFG-RATE-MEAS` e `CFG-RATE-NAV`,
aggiorna la selezione della frequenza e riporta anche nel log intervallo misure, divisore NAV e
Hz di navigazione configurati, insieme al baud UART1. Esempi: 40 ms e divisore 1 = 25 Hz; 40 ms e
divisore 2 = 12,5 Hz. Sono valori di configurazione nominali, non una misura del
numero di messaggi ricevuti al secondo. Periodi/divisori non presenti tra i
preset rimangono rappresentati senza arrotondamenti.

Impostando un preset di frequenza si salvano insieme intervallo misure e
divisore 1. Applicare il solo profilo costellazioni/protocollo non cambia
frequenza o baud. Leggere la configurazione non scrive la flash. È possibile
salvare il baud attuale anche senza cambiarlo; cambiandolo il Manager ricollega
la seriale al nuovo valore e verifica i parametri salvati. Nessun reset viene
inviato automaticamente.

Il profilo disabilita NAV-STATUS e i messaggi NMEA standard elencati nel
modulo; eventuali ulteriori messaggi UBX già abilitati restano invariati.
NMEA da solo non è compatibile con il firmware GOATS che legge NAV-PVT.
Questa funzione non passa attraverso la USB del laptimer e non modifica firmware,
pin o protocolli di trasferimento GOATS. La configurazione della V5.4.15.11 deve
ancora essere verificata spegnendo e riaccendendo il ricevitore reale.
Dettagli in [documentazione/GNSS.md](documentazione/GNSS.md).

## Funzionalità conservate e avvio

Sessioni GRT8/GSA2/GSA3/CSV/JSON, archivio SQLite, editor circuiti, note,
confronto multi-sessione, replay, export JSON/CSV/GPX, AssistNow e USB/BURST4.
La mappa fullscreen conserva le caselle indipendenti per frenata, velocità in
curva e grafico velocità; il riquadro descrittivo sulla mappa resta rimosso.

Installare Python 3.10–3.14 (consigliato 3.13) ed eseguire
`AVVIA_GOATS_RT_MANAGER_V5.bat`. Entrypoint `goats_rt_manager_v5_4_15_15.py`.
Dipendenze in `requirements.txt`. L'aggiornamento firmware usa esptool 4.14.0.
Il bootstrap usa `%LOCALAPPDATA%/GOATS_RT_Manager`.
Nelle Impostazioni selezionare gli archivi esistenti se collocati altrove;
le credenziali e i dati non sono inclusi nel pacchetto.

I `.txt` descrittivi sono raccolti in `documentazione/`. Nella radice restano
`requirements.txt` e `SHA256SUMS.txt` (file funzionali). I manuali storici
inclusi descrivono le rispettive versioni. Verifica: `sha256sum -c SHA256SUMS.txt`.
Test software in `tests/cloud_gnss/` e `tests/windows_fullscreen/`.

Le note aggiunte nel database non vengono sincronizzate. I file sessione originali
conservano tutti i campi già presenti all’origine, incluse eventuali note in un
JSON esportato e poi importato come file.

## V5.4.15.15 — Firmware USB RC3.1

La pagina **Firmware USB** rileva Guition 4.3 e RLCD 4.2 monocromatico in modalità BOOT
e scarica RC3.1 per il modello rilevato. Si può anche selezionare il pacchetto
ufficiale RC3 o RC3.1 da disco. Il numero di versione compare prima della conferma.
Consultare la [procedura RC3](../../docs/RC3_USB.md).

**Entra in BOOT e rileva** può riavviare il laptimer in modalità BOOT sulla
sua porta USB Serial/JTAG nativa dopo conferma. Sulle altre porte, entrare
in modalità BOOT con i pulsanti e usare **Rileva laptimer**.
