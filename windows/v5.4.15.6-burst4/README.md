# GOATS Windows — Manager V5.4.15.6 BURST4

Progetto completo derivato dalla [V5.4.15.5](../v5.4.15.5-burst4/README.md).
Le versioni precedenti sono conservate nelle rispettive cartelle.

## Sessioni e circuiti con Android

Con Android **V0.2.2**, selezionare su entrambi i dispositivi la stessa cartella
cloud. Sul PC: **Importa Sessioni → Cloud Sync → SINCRONIZZA ORA**.
L'opzione automatica controlla la cartella ogni 15 secondi mentre il Manager è
aperto. Usare una cartella locale gestita dal client cloud; non condividere il
file SQLite. Nel telefono è richiesto un provider con accesso alle cartelle.

I file originali delle sessioni sono deduplicati per SHA-256; i circuiti usano
revisioni JSON nella sottocartella `circuiti/`. Le modifiche concorrenti sono
conservate come varianti. Note, database, impostazioni e credenziali rimangono
locali; le eliminazioni non si propagano. Vedere la
[guida operativa](../../docs/CLOUD_SYNC_MOBILE_WINDOWS.md).

## Configurazione GNSS diretta USB-UART

Collegare direttamente il ricevitore MG-902/u-blox M9N tramite USB-UART.
In **GNSS**, scegliere la COM e il baud attuale; leggere la configurazione,
selezionare GPS, Galileo, GLONASS, BeiDou, SBAS e/o QZSS e il protocollo di uscita:

| Uscita UART1 | Messaggi essenziali automatici |
|---|---|
| UBX | NAV-PVT |
| NMEA | GGA + RMC |
| UBX + NMEA | NAV-PVT + GGA + RMC |

Almeno una costellazione principale è richiesta; SBAS/QZSS richiedono GPS in
questo profilo. Il pulsante applica solo dopo conferma, verifica ACK e rilettura
CFG-VALGET e segnala NAK, timeout o discrepanze. La persistenza BBR/Flash è
opzionale; per default si modifica la RAM. Non cambia frequenza o baud.
L'ingresso UBX rimane abilitato per i comandi di configurazione.

Il profilo disabilita NAV-DOP/SAT/STATUS e i messaggi NMEA standard elencati nel
modulo; eventuali ulteriori messaggi UBX già abilitati restano invariati.
NMEA da solo non è compatibile con il firmware GOATS che legge NAV-PVT.
Questa funzione non passa attraverso la USB del laptimer e non modifica firmware,
pin o protocolli di trasferimento GOATS. Il collaudo su ricevitore reale resta da
eseguire. Dettagli in [documentazione/GNSS.md](documentazione/GNSS.md).

## Funzionalità conservate e avvio

Sessioni GRT8/GSA2/GSA3/CSV/JSON, archivio SQLite, editor circuiti, note,
confronto multi-sessione, replay, export JSON/CSV/GPX, AssistNow e USB/BURST4.
La mappa fullscreen conserva le caselle indipendenti per frenata, velocità in
curva e grafico velocità; il riquadro descrittivo sulla mappa resta rimosso.

Installare Python 3.10–3.14 (consigliato 3.13) ed eseguire
`AVVIA_GOATS_RT_MANAGER_V5.bat`. Entrypoint `goats_rt_manager_v5_4_15_6.py`.
Dipendenze invariate: PySide6 >=6.10,<6.12, pyserial >=3.5, requests >=2.31.
Il bootstrap usa `%LOCALAPPDATA%/GOATS_RT_Manager`.
Nelle Impostazioni selezionare gli archivi esistenti se collocati altrove;
le credenziali e i dati non sono inclusi nel pacchetto.

I `.txt` descrittivi sono raccolti in `documentazione/`. Nella radice restano
`requirements.txt` e `SHA256SUMS.txt` (file funzionali). I manuali storici
inclusi descrivono le rispettive versioni. Verifica: `sha256sum -c SHA256SUMS.txt`.
Test software in `tests/cloud_gnss/` e `tests/windows_fullscreen/`.
