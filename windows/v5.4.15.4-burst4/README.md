# GOATS Windows — Manager V5.4.15.4 BURST4

Importazione di `GOATS_RT_Manager_V5.4.15.4_BURST4.zip`: 100 file originali
conservati senza modifiche al contenuto; escluso un file `__pycache__/*.pyc`.
Sono presenti 17 sorgenti Python, launcher/diagnostica Windows, logo, manuali,
note storiche e due esempi sintetici (`sample_test.grt`, `tracks/esempio.json`).

## Avvio Windows

Installare Python 3.10–3.14 (il launcher consiglia 3.13) ed eseguire:

```bat
AVVIA_GOATS_RT_MANAGER_V5.bat
```

Il bootstrap installa PySide6 `>=6.10,<6.12`, pyserial `>=3.5` e requests
`>=2.31` nel runtime per utente `%LOCALAPPDATA%\GOATS_RT_Manager`.
Il punto di ingresso reale è `goats_rt_manager_v5_4_13_11.py`, che mostra
V5.4.15.4 nell'interfaccia. I nomi e le etichette storiche sono conservati.
Per problemi di avvio: `DIAGNOSTICA_GOATS_RT_MANAGER.bat`.

## Funzionalità presenti nei sorgenti

- Import GRT8, GSA2, GSA3, CSV e JSON; database SQLite, ricerca, note e cancellazione.
- Analisi giri/settori, giro potenziale, confronto sessioni, replay e stima frenate.
- Mappe, grafici velocità, export CSV/JSON/GPX.
- Editor circuiti JSON/GTC3 e trasferimenti USB; sessioni microSD via GSD con
  CRC32, negoziazione BURST4 e fallback al trasferimento singolo.
- Cartelle sessioni/circuiti configurabili, fallback locale e Cloud Sync dei file.
- AssistNow multi-dispositivo e strumenti GNSS già inclusi nel pacchetto.

I protocolli e gli strumenti GNSS sono importati intatti. Nessuna operazione
hardware o registrazione a servizi esterni è stata eseguita durante la migrazione.
Mappe e servizi AssistNow richiedono rete; la compatibilità USB dipende dal firmware.

Da questa cartella, `sha256sum -c IMPORTED_SOURCE_SHA256SUMS.txt` verifica
l'identità dei file importati. `SHA256SUMS.txt` è il manifest storico originale:
è già incoerente nello ZIP e viene conservato come documento di provenienza.

Consultare il [rapporto di migrazione](../../docs/MIGRATION_MOBILE_WINDOWS_REPORT.md)
per le prove svolte e le incompatibilità già presenti rilevate nei sorgenti.
