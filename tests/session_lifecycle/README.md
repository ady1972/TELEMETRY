# File sessione — Windows V5.4.15.7 / Android V0.2.3

Test con file temporanei e telemetria sintetica, senza account cloud o hardware.
Eseguire separatamente dalla radice:

```sh
python tests/session_lifecycle/test_session_files.py
python tests/session_lifecycle/test_mobile_deletions.py
QT_QPA_PLATFORM=offscreen python tests/session_lifecycle/test_windows_flow.py
```

- 12 test file/database: copia byte identica, originali removibili, deduplica tra
  percorsi diversi, ID/note conservati, migrazione dello schema SQLite precedente,
  sorgenti mancanti, cancellazione di alias condivisi, copie offline e tardive,
  ricevute corrotte, rimozioni ritentate, file con più sessioni e import interrotti.
- 2 test bridge Android/SQLite: ricezione di una cancellazione Windows e ricevuta
  arrivata prima del file, senza ricomparsa al sync successivo.
- 4 test Qt: controllo all'avvio e pubblicazione import con sync periodico spento,
  cancellazione confermata e annullamento senza perdita di file.

I 29 test precedenti in `tests/cloud_gnss` e `tests/windows_fullscreen` vengono
rieseguiti sulle nuove versioni con `GOATS_WINDOWS_VERSION=5.4.15.7` e
`GOATS_MOBILE_VERSION=0.2.3`. La build APK verifica il codice Kotlin e il pacchetto
Python. Il comportamento dei provider SAF e dei client cloud reali va collaudato
sui dispositivi; i test non simulano l'intero provider Android.
