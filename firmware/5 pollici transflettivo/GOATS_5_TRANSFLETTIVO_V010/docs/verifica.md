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

## Schermata GPS e retroilluminazione — 19/11/2026

Versione firmware invariata: 0.1.0. Ambiente Linux, ESPHome 2026.7.3,
ESP-IDF 5.5.5. I risultati storici Windows sopra restano riferiti al 12/11.

| Controllo | Esito |
|---|---|
| Config firmware GPS e variante test card | PASS |
| Config risolta: un solo display, test card senza renderer GPS | PASS |
| PWM GPIO2, gamma 1.0, luminosita' iniziale 50% in entrambe le varianti | PASS software |
| Pin/timing RGB e sorgenti GNSS confrontati con la base | Invariati |
| check_contracts.py | PASS |
| Test C++ parser NAV-PVT con G++ e warning come errori | PASS |
| Callback effettivo della schermata: attesa, senza fix, fix valido, scadenza a 3 s, ripresa e rollover millis | PASS host |
| Ingombro dei testi con il font previsto | PASS |
| Compilazione/link ESP32, firmware GPS | PASS |
| Compilazione/link ESP32, variante test card | PASS |
| Schermata e luminosita' sul dispositivo | Da collaudare |

La ricezione GPS resta passiva su GPIO17, 230400 baud; il firmware non configura
il ricevitore. La nuova schermata non implementa cronometraggio o sessioni.

## Diagnostica GPS con logica RLCD — 19/11/2026

La successiva estensione del parser aggiunge NAV-SAT e NAV-DOP. La regola RLCD
conta come visti solo i satelliti con C/N0 >0; i satelliti usati restano quelli
di NAV-PVT. Criterio di fix, epoche iTOW, duplicati e percorso dei campioni PVT
non cambiano. Buffer UBX limitato a 1200 byte come RLCD; nessuna allocazione
dinamica nel parser o trasmissione al ricevitore.

- Test C++ estesi: conteggi per costellazione, messaggi SAT oltre 92 byte,
  distinzione visti/usati, zero reale, checksum errato, payload troncato,
  versione SAT non supportata, HDOP, frame sovradimensionati e ripresa PVT.
- Frequenza misurata: 25 Hz su traffico sintetico, ritorno a zero dopo silenzio,
  rollover millis. Test eseguiti con AddressSanitizer e UndefinedBehaviorSanitizer: PASS.
- Callback grafico: distinzione dato assente/zero, scadenza SAT/DOP a 5 s,
  PVT a 3 s e stati fix: PASS host.
- Configurazione UART, pin e timing del pannello, versione 0.1.0 e PWM 50%: invariati.
- Compilazione completa ESPHome del firmware GPS: PASS.
- Compilazione della variante test card: PASS.
- Ricezione NAV-SAT/DOP, conteggi reali e fix sul dispositivo: da collaudare.
