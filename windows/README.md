# GOATS Windows — versioni Manager

Ogni versione è conservata in una cartella con il progetto completo.

| Versione | Progetto |
|---|---|
| V5.4.15.7 — copia file, controllo all’avvio e cancellazioni condivise | [v5.4.15.7-burst4](v5.4.15.7-burst4/README.md) |
| V5.4.15.6 BURST4 — cloud sessioni/circuiti e profili GNSS USB-UART | [v5.4.15.6-burst4](v5.4.15.6-burst4/README.md) |
| V5.4.15.5 BURST4 — scelta analisi fullscreen, mappa senza descrizione | [v5.4.15.5-burst4](v5.4.15.5-burst4/README.md) |
| V5.4.15.4 BURST4 | [v5.4.15.4-burst4](v5.4.15.4-burst4/README.md) |

Per avviare la nuova versione del Manager, aprire `windows/v5.4.15.7-burst4/` ed eseguire
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
