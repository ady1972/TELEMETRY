# GOATS Windows — Manager V5.4.15.5 BURST4

Progetto completo derivato dalla
[V5.4.15.4 ricevuta e confermata funzionante dall'utente](../v5.4.15.4-burst4/README.md).
La versione precedente è conservata nella propria cartella.

## Mappa a schermo intero

Nella pagina **Analisi**, aprire **MAPPA SCHERMO INTERO**. La barra **MOSTRA**
offre tre caselle indipendenti:

- **Analisi frenata**: dati del punto di frenata e confronto dei delta.
- **Velocità in curva**: velocità di ingresso, minima e uscita nelle tabelle.
- **Grafico velocità**: curva velocità/tempo nella parte inferiore della mappa.

È possibile mostrare entrambe le analisi, una sola oppure nasconderle tutte.
Le tabelle e i punti delle zone scompaiono quando entrambe le analisi sono
disattivate. Il grafico può restare visibile indipendentemente dalle tabelle.
Le scelte si applicano subito, mantengono zoom e posizione della mappa e sono
ricordate quando si riapre il fullscreen nella stessa sessione del Manager.

Play/Pausa, velocità replay, Reset e le scorciatoie SPAZIO/S/R/ESC restano
disponibili. Il riquadro descrittivo sovrapposto alla mappa è stato rimosso
sia nella vista normale sia nel fullscreen.

## Avvio e archivi esistenti

Installare Python 3.10–3.14 (consigliato 3.13) ed eseguire da questa cartella:

```bat
AVVIA_GOATS_RT_MANAGER_V5.bat
```

Il punto di ingresso aggiornato è `goats_rt_manager_v5_4_15_5.py`.
Dipendenze invariate: PySide6 `>=6.10,<6.12`, pyserial `>=3.5`, requests
`>=2.31`. Il bootstrap mantiene il runtime per utente
`%LOCALAPPDATA%/GOATS_RT_Manager`.

Per usare archivi già esistenti, selezionare nelle **Impostazioni** le stesse
cartelle sessioni e circuiti della versione precedente. Ogni versione conserva
le proprie impostazioni locali: non vengono spostati automaticamente database,
tracciati o credenziali. Conservare una copia di sicurezza degli archivi.

Tutte le funzionalità della base restano incluse: sessioni e formati storici,
SQLite, editor circuiti, replay, export, Cloud Sync, AssistNow e trasferimenti
USB/BURST4. I relativi moduli dati e protocolli sono identici alla V5.4.15.4.
I manuali e le note storiche copiati dalla base descrivono le rispettive versioni.

## Verifiche

Test automatici dei controlli Qt e della mappa in Chromium: tutte le otto
combinazioni di visibilità, caricamento web ritardato, chiusura/riapertura,
replay e sessione senza dati. Vedere
[`tests/windows_fullscreen`](../../tests/windows_fullscreen/README.md).
Il collaudo con telemetria e hardware reali resta da eseguire sulla nuova versione.

`SHA256SUMS.txt` elenca i file di questa versione. Per verificarli dalla cartella:

```sh
sha256sum -c SHA256SUMS.txt
```
