GOATS RT Manager V5.4.10.6 - LAUNCHER FIX
==========================================

Correzione avvio Windows:
- evita il falso rilevamento dell'alias Microsoft Store di python.exe che termina con codice 9009;
- verifica che python.exe/py siano interpreti reali prima di usarli;
- cerca Python anche nei percorsi standard di installazione Windows;
- se la nuova cartella non contiene ancora .goats_venv, cerca automaticamente una cartella sorella di una versione precedente del Manager e ne riutilizza l'ambiente Python/PySide6 senza modificarla;
- mantiene integralmente la modifica V5.4.10.5: selezione multipla circuiti + merge non distruttivo dei circuiti presenti sul laptimer.

Uso consigliato:
1. Estrarre la cartella V5.4.10.6 accanto alla cartella della precedente versione funzionante.
2. Avviare AVVIA_GOATS_RT_MANAGER_V5.bat.
3. Se esiste un vecchio .goats_venv funzionante, verra' riutilizzato automaticamente.
