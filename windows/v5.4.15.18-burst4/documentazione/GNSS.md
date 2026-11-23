# Configurazione GNSS V5.4.15.11

Il 19/11/2026 l'utente ha confermato che l'applicazione dei parametri sul
ricevitore funziona, ma i valori si perdono al riavvio. Nella precedente pagina
il salvataggio non volatile era una casella opzionale disattivata per default;
la verifica riguardava solo la RAM. Il comando di lettura ometteva la frequenza.

## Scrittura e verifica permanente

I tre comandi della pagina (profilo, frequenza, baud) usano CFG-VALSET versione
0 con maschera layer **7**: RAM (bit 0), BBR (bit 1), flash (bit 2).
Dopo ACK, CFG-VALGET rilegge e confronta tutte le chiavi del relativo comando
nei livelli RAM (0), flash (2), BBR (1). I numeri di layer per lettura sono
indici, diversi dalla maschera bit per la scrittura.

Il successo viene mostrato soltanto dopo le verifiche. NAK, timeout, chiavi
mancanti o valori diversi interrompono la conferma del salvataggio. Non è
previsto fallback automatico RAM-only. Non si presume che tutti i ricevitori
abbiano flash scrivibile: un ricevitore che non la supporta deve generare un
errore visibile. Un errore non implica rollback; parte della configurazione
potrebbe già essere stata applicata. Leggere nuovamente i parametri prima di
riprovare. Nessun reset viene inviato e la lettura non scrive memoria.

Nel cambio baud, l'ACK può essere trasmesso alla nuova velocità: un timeout a
quella vecchia è tollerato solo se la rilettura completa alla nuova velocità
conferma i valori in tutti i livelli. Un NAK non viene ignorato.

## Frequenza configurata

- `CFG-RATE-MEAS = 0x30210001`, U2: intervallo misure in millisecondi.
- `CFG-RATE-NAV = 0x30210002`, U2: numero di misure per soluzione di navigazione.
- Hz misure = `1000 / MEAS`; Hz navigazione = `1000 / (MEAS * NAV)`.

La lettura include anche il baud UART1 e visualizza i valori configurati,
compresi quelli non corrispondenti ai preset. Non misura la cadenza effettiva
sul filo seriale. Un preset scrive insieme MEAS e NAV=1; valori letti non standard
mantengono la coppia originale se riapplicati. La scrittura valida i limiti
M9 documentati: MEAS da 25 a 65535 ms; NAV da 1 a 127.

Il profilo conserva la selezione delle costellazioni e i messaggi NMEA della
V5.4.15.7; la V5.4.15.11 aggiunge NAV-SAT e NAV-DOP al profilo UBX. Il profilo non modifica rate o baud; solo i pulsanti dedicati
lo fanno. Connessione diretta UART1 via adattatore USB-UART, nessun ponte GOATS.

## Riferimento e verifica

u-blox M9 SPG 4.04 Interface Description **UBX-21022436 R02**, sezioni CFG-VALSET,
CFG-VALGET e CFG-RATE (5.9.18, pagina 223), CFG-UART1/CFG-SIGNAL/CFG-MSGOUT.
[Manuale ufficiale](https://content.u-blox.com/sites/default/files/u-blox-M9-SPG-4.04_InterfaceDescription_UBX-21022436.pdf).

I test usano seriale simulata con RAM, BBR e flash distinte, riavvio con perdita
della BBR, frame UBX reali, errori di flash, frequenze e cambio baud. I controlli
Qt verificano la lettura e il salvataggio automatico. Non costituiscono un test
fisico del ricevitore: applicare i parametri, togliere alimentazione, riaccendere
e usare LEGGI CONFIGURAZIONE GNSS per il collaudo della nuova versione.

## Riepilogo nel log (V5.4.15.9)

La lettura riporta nel log anche il testo della frequenza già visualizzato
accanto al selettore: Hz di navigazione e misure, periodo in ms e divisore NAV.
Include inoltre il baud UART1. I dati provengono dalla stessa lettura del
ricevitore; non vengono inviate nuove scritture o richieste seriali aggiuntive.

## Messaggi usati dalle telemetrie (V5.4.15.11)

Per UBX e UBX+NMEA il Manager imposta su UART1:

- NAV-PVT (0x20910007) = 1, ogni soluzione di navigazione.
- NAV-DOP (0x20910039) = 1, ogni soluzione, per l'HDOP.
- NAV-SAT (0x20910016) = divisore `ceil(Hz navigazione)`, limitato a 1..255.
- NAV-STATUS rimane disabilitato. In NMEA-only i messaggi UBX restano disabilitati.

I divisori CFG-MSGOUT contano soluzioni di navigazione. Per 25 Hz il valore è
25, quindi NAV-SAT a 1 Hz; per 12,5 Hz il valore è 13 (circa 0,962 Hz); sotto
1 Hz si usa 1. PVT/DOP non vengono rallentati. Il profilo legge MEAS/NAV prima
di scrivere, senza cambiare frequenza o baud. Il pulsante frequenza aggiorna
anche il divisore SAT se UART1 UBX e NAV-SAT erano già attivi. Salva e verifica
anche questo valore in RAM, BBR e flash. La lettura mostra nel log lo stato
NAV-SAT e la sua frequenza nominale, senza scrivere.

Riferimenti firmware verificati nel repository, non un'ispezione dell'hardware:

- `firmware/guition-43/goats_guition_43_rc2.yaml` dichiara GNSS passivo e decodifica
  NAV-PVT, NAV-DOP e NAV-SAT. NAV-SAT alimenta `gps_visible_satellites`.
- `firmware/guition-43/goats_guition_43_rc2/goats_ubx_m9n_v11.h` contiene una
  funzione di configurazione 25/25/1 Hz, ma la RC2 non la richiama all'avvio.
- `firmware/rlcd-42/GOATS_RLCD_RC2/m9n_passive.h` e la base TEST26 sono RX-only.
  NAV-SAT viene decodificato per satelliti visti (C/N0 > 0) e conteggi GPS,
  Galileo, BeiDou, GLONASS, SBAS; NAV-DOP fornisce HDOP.

Quindi il solo decoder presente non garantisce che il ricevitore stia emettendo
il messaggio: conta la sua configurazione persistente. Nessun firmware viene
modificato da questa release. Il Manager configura l'emissione e ne mostra
il rate; non introduce una nuova tabella o skyplot dei satelliti nel PC.
