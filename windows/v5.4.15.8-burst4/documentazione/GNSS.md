# Configurazione GNSS V5.4.15.8

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

Profilo, messaggi essenziali e chiavi CFG-SIGNAL/CFG-MSGOUT conservano la logica
della V5.4.15.7. Il profilo non modifica rate o baud; solo i pulsanti dedicati
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
