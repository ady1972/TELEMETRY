# Profilo GNSS V5.4.15.6

Riferimento: u-blox M9 SPG 4.04 Interface Description **UBX-21022436**, sezioni
CFG-SIGNAL, CFG-UART1INPROT, CFG-UART1OUTPROT, CFG-MSGOUT, CFG-VALSET e CFG-VALGET.
[Manuale ufficiale](https://content.u-blox.com/sites/default/files/u-blox-M9-SPG-4.04_InterfaceDescription_UBX-21022436.pdf).

Il codice `goats_gnss.py` include le chiavi documentate per UART1 e i segnali L1
GPS, Galileo E1, GLONASS L1, BeiDou B1, SBAS L1 e QZSS L1 C/A. Imposta insieme
abilitazione gruppo e segnale. L'uscita selezionata abilita NAV-PVT e/o GGA/RMC
ogni soluzione di navigazione. Disabilita NAV-DOP/SAT/STATUS e NMEA
DTM/GBS/GLL/GNS/GRS/GSA/GST/GSV/VTG/ZDA; non altera altre chiavi messaggio.

La configurazione è un singolo CFG-VALSET, layer RAM (1) oppure RAM+BBR+Flash
(7) se richiesto. Dopo ACK rilegge tutti i parametri RAM, confrontandoli con il
profilo. Un errore non implica rollback: leggere nuovamente la configurazione
prima di riprovare. Non viene inviato reset, né cambiato baud/frequenza.
USB, SPI e I2C del ricevitore non vengono configurati.

Sono verificati frame UBX, ACK/NAK, timeout, readback, selezioni e controlli Qt
con seriale simulata. Queste verifiche non sostituiscono il collaudo del modulo
M9N e del suo specifico firmware, in particolare passando a NMEA soltanto.
