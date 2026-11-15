GOATS RT Manager V5.4.13.2 - Local Runtime Fix
================================================

Problema corretto
-----------------
Il Manager puo' essere conservato in Google Drive / OneDrive, ma un virtual
environment Python/Qt non deve essere sincronizzato. I client cloud possono
bloccare DLL, file __pycache__ o file temporanei durante la sincronizzazione.
Questo puo' produrre, anche dopo un giorno di funzionamento normale:

- DLL Load failed while importing QtWidgets
- qwindows.dll non avviabile
- WinError 5 / Accesso negato durante la cancellazione di .goats_venv

Modifica V5.4.13.2
------------------
- La .goats_venv nella cartella del Manager viene ignorata.
- Python/PySide6/Qt vengono installati nel profilo locale Windows:
  %LOCALAPPDATA%\GOATS_RT_Manager\runtime_pyXXX
- Google Drive/OneDrive non sincronizzano quindi piu' DLL e cache Qt.
- Se un runtime locale si guasta, non viene cancellato mentre e' bloccato:
  il bootstrap crea un runtime recovery separato e lo usa automaticamente.
- Nessuna modifica al database, alle sessioni, ai circuiti o ai profili AssistNow.

Uso
---
Estrarre il pacchetto anche dentro Google Drive e avviare:
AVVIA_GOATS_RT_MANAGER_V5.bat

Al primo avvio puo' essere necessario scaricare nuovamente PySide6 e le altre
dipendenze nel runtime locale.

La vecchia cartella .goats_venv puo' essere lasciata dov'e': V5.4.13.2 non la
usa e non prova a cancellarla. Quando Google Drive non la sta piu' usando, puo'
essere eliminata manualmente per recuperare spazio.
