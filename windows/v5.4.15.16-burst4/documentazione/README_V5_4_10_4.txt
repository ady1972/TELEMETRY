GOATS RT Manager V5.4.10.4

- Usa GSD_SESSION <id> per scaricare la traccia direttamente dal file FatFS
  Sxxxxxx.CSV del laptimer.
- Non dipende più dal nome file costruito lato Manager né dal VFS stdio.
- Se la traccia non arriva o contiene 0 punti, BLOCCA l'importazione e mostra
  l'errore preciso: non inserisce più nel database sessioni apparentemente
  valide ma con 0 punti.
- Compatibile con Firmware V11.0.1.39.


PATCH COMPATIBILITA SD REMOUNT (stessa V5.4.10.4)
- GSDT_WAIT REMOUNT viene trattato come stato intermedio.
- Il Manager continua ad attendere GSDT_BEGIN fino a 25 secondi.
- GSDT_ERR resta un errore definitivo e viene mostrato integralmente.
- Nessuna modifica al formato sessioni o al parsing CSV.
