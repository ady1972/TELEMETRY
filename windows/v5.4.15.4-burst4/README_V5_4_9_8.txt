GOATS RT Manager V5.4.9.8

FIX DEFINITIVO DEL LAUNCHER
La schermata della V5.4.9.7 mostrava errori dentro Python 3.13 / _pyrepl:
il controllo del launcher arrivava ad aprire Python in modalità interattiva
a causa della gestione/quoting dei comandi Windows.

La V5.4.9.8 elimina quella strada:
- nessun PowerShell per il bootstrap;
- nessun test Python eseguito tramite comando -c dal file BAT;
- il BAT avvia un normale file goats_bootstrap.py;
- tutto il controllo dipendenze avviene dentro Python con subprocess;
- non può quindi cadere nel REPL interattivo _pyrepl;
- crea .goats_venv;
- installa automaticamente PySide6, pyserial e requests se mancanti;
- avvia il Manager dall'ambiente dedicato.

PER IL TEST:
1. estrarre lo ZIP in una nuova cartella;
2. eseguire AVVIA_GOATS_RT_MANAGER_V5.bat;
3. al primo avvio attendere l'eventuale installazione di PySide6.

Mantiene tutte le funzioni V5.4.9.5/5.4.9.4:
- import circuiti dal laptimer;
- UI compatta AssistNow e Sessioni USB;
- fix esportazione sessioni.
