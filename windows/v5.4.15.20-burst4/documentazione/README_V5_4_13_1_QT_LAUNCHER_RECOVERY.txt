GOATS RT Manager V5.4.13.2 - Qt Launcher Recovery
=================================================

Correzione avvio Windows dopo errore "ERRORE Qt persistente / codice 21".

Modifiche:
- il launcher non considera piu' valido un ambiente solo perche' `import PySide6` funziona;
  verifica realmente QApplication + plugin Windows qwindows.dll;
- se la .goats_venv locale ha Qt non funzionante, viene ignorata e si cerca automaticamente
  una .goats_venv di una versione GOATS precedente che superi il test reale Qt;
- Python 3.13 e 3.12 vengono preferiti a Python 3.14 per la creazione di un nuovo ambiente;
- il test Qt mantiene vivi gli handle restituiti da os.add_dll_directory(), evitando un falso
  fallimento del caricamento DLL;
- il Manager viene avviato tramite goats_run_manager.py, che pulisce eventuali variabili Qt
  ereditate da Anaconda/QGIS/PyQt/IDE e configura i percorsi PySide6 in modo controllato;
- se serve ricreare l'ambiente locale, viene fatta una ricostruzione completa una sola volta,
  invece di reinstallare ripetutamente PySide6 sopra un ambiente gia' corrotto.

Le funzioni Multi Device AssistNow e il manuale V5.4.13.0 restano invariate.
