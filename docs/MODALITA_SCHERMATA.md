# Modalità schermata — RLCD e Guition RC2.1

Richiesta confermata dall'utente: nei menu impostazioni dei due dispositivi,
voce **Modalità schermata** con due opzioni esplicite:

| Scelta | Riquadro principale | Posizione precedente del delta |
|---|---|---|
| LAP TIME (predefinita) | Tempo giro | Delta |
| DELTA | Delta | Tempo giro |

I due valori restano entrambi visibili. Le etichette seguono i valori;
formati numerici, segno, evidenziazione del delta e avvisi post-giro restano
associati al dato corrispondente. La scelta non cambia i calcoli o i dati GPS.

RLCD: Menu → Opzioni gara → Modalità schermata; KEY seleziona, BOOT conferma,
BOOT lungo torna indietro senza cambiare la preferenza.
Guition: Impostazioni → Modalità schermata (scorrere la pagina se necessario);
toccare DELTA o LAP TIME. Indietro annulla senza modifiche.

Il valore è salvato subito nella NVS, in uno spazio separato dagli archivi,
e ricaricato all'avvio. Senza preferenza, o con valore non valido, viene
usata LAP TIME. Se il salvataggio fallisce non viene applicata la nuova scelta:
il menu resta aperto. Non si scrive su flash durante il rendering o per campione.

Le configurazioni conservano i percorsi RC2 ma identificano la nuova revisione
come RC2.1, comprese le informazioni firmware. RC1 resta invariata.

## Verifica

La prova host verifica default, selezione in entrambe le direzioni, ricarica
simulando il riavvio, valore non valido, errori di apertura/scrittura/commit
senza applicare una preferenza non salvata. Le configurazioni sono validate
con ESPHome 2026.7.3; compilazione e prova visiva hardware hanno esito separato.

Prima dell'accettazione sui dispositivi:

1. Verificare LAP TIME al primo avvio, entrambi i valori e le etichette.
2. Selezionare DELTA e verificare scambio, segni, delta non disponibile,
   best lap, settori e avvisi post-giro.
3. Spegnere e riaccendere: deve riapparire DELTA.
4. Tornare a LAP TIME e ripetere il riavvio.
5. Verificare menu, scorrimento Guition e tasti RLCD senza sovrapposizioni.
6. Controllare avvio/chiusura di sessioni e integrità dei file esistenti.

Nessun flash o collaudo hardware è stato eseguito nella preparazione.
Il riepilogo essenziale dei giri richiesto nella PR #12 resta una modifica
separata; questo intervento riguarda la schermata racing.

## Esito dei controlli della revisione

Sul commit `af03d359b9f987054a96473f837623946c1f7eec`, GitHub Actions ha completato con
SUCCESS il test host e le compilazioni di entrambi i firmware con ESPHome
2026.7.3. Verifica consultabile nella [PR #13](https://github.com/ady1972/TELEMETRY/pull/13/checks).
Validazione delle configurazioni e generazione sorgenti eseguite anche nel
workspace. Il collaudo visivo e la persistenza su NVS reale restano da
verificare sui dispositivi; nessun flash effettuato.
