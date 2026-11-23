GOATS RT Manager V5.4.9.3

Modifiche principali:
- menu principale separato in Circuiti, Sessioni USB e AssistNow;
- ogni voce apre una finestra dedicata con i soli comandi pertinenti;
- non è più necessario entrare nell'Editor Piste per scaricare sessioni
  o aggiornare AssistNow;
- corretto download sessioni: il campo interno 'trace' non viene passato
  al CSV dei giri;
- eventuali punti GPS presenti nel campo trace vengono esportati in un
  file separato *_trace.csv;
- JSON completo della sessione resta invariato;
- mantiene tutte le funzioni della V5.4.9.2.

Modalità strumenti:
  python goats_track_editor.py --mode tracks
  python goats_track_editor.py --mode sessions
  python goats_track_editor.py --mode assistnow
