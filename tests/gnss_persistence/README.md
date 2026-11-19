# GNSS flash e frequenza — V5.4.15.8

Dalla radice con Python e le dipendenze del Manager:

```sh
python tests/gnss_persistence/test_storage.py
QT_QPA_PLATFORM=offscreen python tests/gnss_persistence/test_ui.py
```

13 test backend usano un modello seriale con frame UBX, livelli RAM/BBR/flash
separati e riavvio che perde la BBR ma conserva la flash. Verificano profilo
permanente di default, errori/NAK/mancata flash, MEAS/NAV e Hz frazionari, range
ufficiali, baud salvato senza cambio o verificato dopo cambio con ACK perso,
parser U2/U4 e rifiuto di una risposta da un layer diverso.

7 test Qt verificano policy automatica, selezione degli Hz letti (anche con
divisore non unitario), salvataggio del profilo e della frequenza senza opzioni
aggiuntive, salvataggio del baud attuale ed errori senza messaggi di successo.

I 48 test precedenti restano eseguiti sulle versioni correnti dove pertinenti:
`GOATS_WINDOWS_VERSION=5.4.15.8`, `GOATS_MOBILE_VERSION=0.2.3`. Totale 68.
Il modello non sostituisce il collaudo del ricevitore reale dopo spegnimento.
