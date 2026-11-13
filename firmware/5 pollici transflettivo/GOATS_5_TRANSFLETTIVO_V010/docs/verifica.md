# Verifica dello scaffold 0.1.0

Data: 12/11/2026. ESPHome disponibile: 2026.7.3.

| Controllo | Esito |
|---|---|
| check_contracts.py | PASS |
| Config firmware base | PASS |
| Config variante display_test | PASS |
| Generazione C++ base --only-generate | PASS |
| Generazione C++ display_test --only-generate | PASS |
| Compilazione/link ESP32 | Non completati: toolchain Windows non disponibile in modo funzionante |
| Esecuzione test C++ parser | Non eseguita su questo host |
| Hardware GNSS/display | Non eseguita |
| Motore cronometraggio/Racing/sessioni/SD | Non implementati nello scaffold |

L'ambiente di questo host ha gia' mostrato WinError 623 all'avvio della toolchain
Xtensa e 0xC0000005 nel compilatore host. La generazione C++ non viene presentata
come compilazione riuscita o prova di funzionamento hardware. Nessun binario
viene distribuito per questo progetto iniziale.

I file generati da ESPHome rimangono nella cartella del progetto e sono ignorati
da Git. Non e' stato aggiunto un workflow nella .github principale, per rispettare
il vincolo che tutti i nuovi file siano esclusivamente in questa cartella.

## Controlli ripetibili

Dalla cartella `5 pollici transflettivo`:

```powershell
python GOATS_5_TRANSFLETTIVO_V010/tests/check_contracts.py
python -m esphome config goats_5_transflettivo.yaml
python -m esphome config goats_5_transflettivo_display_test.yaml
python -m esphome compile --only-generate goats_5_transflettivo.yaml
python -m esphome compile --only-generate goats_5_transflettivo_display_test.yaml
```

Test C++ puro, con G++/Clang funzionante, senza dipendenze ESPHome:

```text
c++ -std=c++17 -Wall -Wextra -I GOATS_5_TRANSFLETTIVO_V010/components/goats_core GOATS_5_TRANSFLETTIVO_V010/tests/test_nav_pvt.cpp GOATS_5_TRANSFLETTIVO_V010/components/goats_core/nav_pvt.cpp -o test_nav_pvt
```

Eseguire l'eseguibile risultante. Controlla checksum, campi PVT, duplicati,
fix non valido e risincronizzazione dopo un frame corrotto. Test presente come
base per la futura CI, non dichiarato superato su questo host.

## Layout ESPHome Builder — 13/11/2026

Gli YAML di ingresso restano nella radice del workspace; config, componenti,
sorgenti, documentazione e test sono in `GOATS_5_TRANSFLETTIVO_V010`.
La variante display include lo YAML base affiancato. Conservare i due YAML
insieme alla cartella dedicata. La struttura delle verifiche storiche sopra
rimane riferita alla versione 0.1.0; i percorsi dei comandi sono aggiornati.
