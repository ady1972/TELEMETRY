# GOATS Windows — versioni Manager

Ogni versione è conservata in una cartella con il progetto completo.

| Versione | Progetto |
|---|---|
| V5.4.15.17 BURST4 — changelog e confronto del firmware prima della scrittura USB | [v5.4.15.17-burst4](v5.4.15.17-burst4/README.md) |
| V5.4.15.16 BURST4 — riconoscimento dello slot di avvio USB | [v5.4.15.16-burst4](v5.4.15.16-burst4/README.md) |
| V5.4.15.15 BURST4 — accesso al bootloader dalla porta USB nativa | [v5.4.15.15-burst4](v5.4.15.15-burst4/README.md) |
| V5.4.15.14 BURST4 — correzione rilevamento USB Guition e RLCD | [v5.4.15.14-burst4](v5.4.15.14-burst4/README.md) |
| V5.4.15.13 BURST4 — aggiornamento USB RC3.1 per Guition e RLCD | [v5.4.15.13-burst4](v5.4.15.13-burst4/README.md) |
| V5.4.15.12 BURST4 — aggiornamento firmware RC3 via USB | [v5.4.15.12-burst4](v5.4.15.12-burst4/README.md) |
| V5.4.15.11 BURST4 — NAV-SAT circa 1 Hz e NAV-DOP per HDOP | [v5.4.15.11-burst4](v5.4.15.11-burst4/README.md) |
| V5.4.15.10 BURST4 — replay 2x, 5x e 10x | [v5.4.15.10-burst4](v5.4.15.10-burst4/README.md) |
| V5.4.15.9 BURST4 — frequenza GNSS anche nel log | [v5.4.15.9-burst4](v5.4.15.9-burst4/README.md) |
| V5.4.15.8 BURST4 — GNSS permanente in flash e lettura frequenza | [v5.4.15.8-burst4](v5.4.15.8-burst4/README.md) |
| V5.4.15.7 — copia file, controllo all’avvio e cancellazioni condivise | [v5.4.15.7-burst4](v5.4.15.7-burst4/README.md) |
| V5.4.15.6 BURST4 — cloud sessioni/circuiti e profili GNSS USB-UART | [v5.4.15.6-burst4](v5.4.15.6-burst4/README.md) |
| V5.4.15.5 BURST4 — scelta analisi fullscreen, mappa senza descrizione | [v5.4.15.5-burst4](v5.4.15.5-burst4/README.md) |
| V5.4.15.4 BURST4 | [v5.4.15.4-burst4](v5.4.15.4-burst4/README.md) |

Per avviare la nuova versione del Manager, aprire `windows/v5.4.15.17-burst4/` ed eseguire
`AVVIA_GOATS_RT_MANAGER_V5.bat`. Launcher, moduli, dipendenze, risorse e
manuali rimangono insieme al progetto a cui appartengono.

Il pacchetto ricevuto comprende anche script Python e note di versioni
precedenti, conservati nella stessa cartella. Da soli non costituiscono
progetti completi separati delle rispettive versioni.

Conservare ogni nuova versione completa in una nuova sottocartella e mantenere
le precedenti. Dalle release successive alla V5.4.15.5, tutti i file `.txt`
descrittivi e le note di versione saranno in `documentazione/`. Nella radice
resteranno i file funzionali richiesti da avvio/installazione/verifica,
come `requirements.txt` e `SHA256SUMS.txt`. I pacchetti già pubblicati mantengono
la propria struttura.

Per provenienza, funzionalità e verifiche, consultare il
[rapporto di migrazione](../docs/MIGRATION_MOBILE_WINDOWS_REPORT.md).
