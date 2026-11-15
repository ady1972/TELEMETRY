GOATS RT Manager V5.4.9.9

MODIFICHE SESSIONI USB
- Le sessioni scaricate non finiscono più in una cartella generica con timestamp.
- Ogni sessione viene archiviata in:
    <nome_circuito>_<data>
  ad esempio:
    monza_25-08-2026
    registrazione_libera_25-08-2026
- Più sessioni dello stesso circuito e della stessa data condividono la stessa
  cartella; i file restano distinti tramite session_id.
- Dentro ogni cartella vengono creati:
    session_XXX_<circuito>.json
    session_XXX_<circuito>_laps.csv
    session_XXX_<circuito>_trace.csv (quando disponibile)
    sessions_summary.csv
    goats_sessions_archive.json

IMPORT AUTOMATICO NEL MANAGER
- Al termine del download USB, le sessioni selezionate vengono importate
  automaticamente nel database SQLite del Manager.
- La finestra principale aggiorna l'elenco ogni 1,5 secondi, quindi le sessioni
  compaiono direttamente nella pagina Sessioni senza doverle importare a mano
  o riavviare il Manager.

Mantiene:
- bootstrap V5.4.9.8;
- import circuiti dal laptimer;
- UI compatta Sessioni USB / AssistNow;
- fix trace CSV.
