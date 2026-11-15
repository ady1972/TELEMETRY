GOATS RT Manager V5.4.10.3

NUOVA STRATEGIA DOWNLOAD SESSIONI
- GSES2_GET scarica solo i metadati compatti della sessione.
- Dopo la selezione, il Manager scarica per ogni sessione il file
  Sxxxxxx.CSV direttamente dalla microSD tramite GSD_GET.
- GSD_GET è streaming a blocchi e non richiede al laptimer di costruire in RAM
  l'intera traccia GSA3.
- Il Manager ricostruisce localmente i trace per giro.
- REGISTRAZIONE LIBERA: lap SD=0 viene associato al giro 1.
- elapsed_ms session-relative viene convertito in tempo relativo al giro.
- HDOP/satelliti e velocità possono essere derivati dalla traccia quando i
  metadati risultano a zero.

Questa versione è progettata per GOATS RT Firmware V11.0.1.38.

Obiettivo: eliminare definitivamente il reset del laptimer durante
"SCARICA SESSIONI", mantenendo la traccia completa anche oltre RAM:3000 MAX.
