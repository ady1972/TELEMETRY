GOATS RT Manager V5.4.10.1

FIX AVVIO PYTHON

Problema V5.4.10.0:
il launcher provava direttamente "py -3.13". Se Python 3.13 non era
installato, il launcher Windows restituiva un proprio codice di errore
("[ERROR] No runtime installed that matches 3.13") diverso da 9009.
Il BAT interpretava quel codice come se Python fosse stato avviato e si fermava.

V5.4.10.1:
- prima interroga "py -0p" per sapere quali runtime sono realmente installati;
- prova solo le versioni effettivamente presenti;
- fallback a python.exe nel PATH;
- ulteriore fallback alle normali cartelle Python sotto LocalAppData;
- mantiene il bootstrap Python che crea .goats_venv e installa automaticamente
  PySide6, pyserial e requests.

Per il test:
1. estrarre lo ZIP in una NUOVA cartella;
2. eseguire AVVIA_GOATS_RT_MANAGER_V5.bat.
