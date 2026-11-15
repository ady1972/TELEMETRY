# Test report Android V0.1

Data test: 2026-09-18.

## Verifiche eseguite

- Sintassi Python: OK per `android_bridge.py`, `goats_formats.py`, `goats_store.py`, `goats_exporters.py`.
- Import della sessione `sample_test.grt` del Manager PC: OK.
  - formato rilevato: GRT8
  - sessioni importate: 1
  - punti: 50
  - giri: 1
  - best rilevato: 00:01.960
- `analysis_json`: OK, restituisce sessione, giro, 50 punti e dati velocità.
- Catalogo circuito GTC3: encode/decode OK.
- Merge catalogo: OK; reinviando lo stesso circuito viene aggiornato e non duplicato.
- XML Android: parsing OK per Manifest e resources.
- Kotlin: smoke test sintattico senza Android SDK, nessun errore di parsing `expecting`; i riferimenti Android/Compose risultano naturalmente non risolvibili senza le librerie SDK.

## Non verificabile in questo ambiente

La compilazione finale dell'APK non è stata eseguita qui perché l'ambiente non dispone dell'Android SDK/Gradle e non consente il download diretto delle dipendenze. È incluso un workflow GitHub Actions che esegue la build completa in ambiente Android.

## Test hardware da fare sul telefono

- enumerazione USB OTG del laptimer;
- `GTRK_GET` e `GTRK_BEGIN` sul dispositivo reale;
- invio `GANO_*` di un file [rimosso V0.1.8];
- import di una sessione reale lunga;
- resa grafica su smartphone.
