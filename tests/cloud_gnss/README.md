# Cloud sync e GNSS — test con dati sintetici

Dalla radice, con Python e le dipendenze del Manager Windows:

```sh
python tests/cloud_gnss/test_cloud_sync.py
python tests/cloud_gnss/test_mobile_bridge.py
python tests/cloud_gnss/test_gnss.py
QT_QPA_PLATFORM=offscreen python tests/cloud_gnss/test_windows_ui.py
GOATS_WINDOWS_VERSION=5.4.15.6 python tests/windows_fullscreen/test_fullscreen.py
```

L'ultimo comando richiede Playwright e Chromium (`python -m playwright install chromium`).
Su Windows usare le variabili d'ambiente PowerShell equivalenti.

- 10 test del motore comune: sessioni originali, deduplicazione, retry, copie
  incomplete, aggiornamenti, conflitti, idempotenza, integrità e non eliminazione.
- 2 test del bridge Android con SQLite reale e roundtrip circuito verso PC.
- 8 test GNSS: profili e segnali, frame UBX, ACK/NAK, readback, timeout,
  persistenza e assenza di modifiche a frequenza/baud.
- 3 test Qt: controlli GNSS, conferma NMEA e worker cloud Windows con import
  sessione/circuito e secondo passaggio senza duplicati.
- 6 test fullscreen preesistenti eseguiti sulla nuova versione: controlli Qt,
  mappa Leaflet in Chromium, otto combinazioni visibilità e replay.

Eseguire i file separatamente per isolare i moduli Python Android e Windows.
Nessun ricevitore, account cloud o tracciato personale viene usato. I test non
collaudano i provider Android SAF né la configurazione di un ricevitore reale.
La compilazione APK è nel workflow `mobile-android.yml`; le verifiche e il
pacchetto Windows sono nel workflow `windows-manager.yml` su Windows.
