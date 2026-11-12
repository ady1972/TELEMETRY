# GOATS RT - 5 pollici transflettivo

Nuovo progetto autonomo ESP32-S3/ESPHome, creato da zero esclusivamente in questa
cartella. Il display previsto e' **non touch**. RLCD TEST26 e' il riferimento
funzionale e grafico, non una libreria inclusa dallo scaffold.

**Versione 0.1.0: struttura iniziale, non firmware completo di cronometraggio.**
Non vengono ancora prodotti tempi giro, settori, delta, sessioni o file CSV.
Non sono stati copiati i firmware RLCD o Guition, ne' modificati file esterni.

## Cosa e' presente

- Configurazione ESPHome ESP32-S3, flash 16 MB e PSRAM octal 8 MB prevista dalla scheda.
- Profilo di base per PLCM-UEDX80480050E-WB-B e pannello UEED050WV-RB40-L001.
- Componente C++ locale `goats_core`, scritto da zero.
- Acquisizione passiva UBX NAV-PVT: checksum, posizione, velocita', fix, satelliti,
  timestamp iTOW, istante ESP e conteggio dei duplicati consecutivi.
- Poll UART con budget limitato; nessuna scrittura UART o operazione SD nel parser.
- Contratti iniziali per timing e geometria UI, separati dal codice di acquisizione.
- Variante opzionale per la sola test card del display RGB 800x480.
- Nessun Wi-Fi, OTA, touchscreen, GT911, bus I2C o protocollo Manager attivo.

## Struttura

```text
5 pollici transflettivo/
  goats_5_transflettivo.yaml               # Base GNSS, display spento
  goats_5_transflettivo_display_test.yaml  # Bring-up RGB opzionale
  config/
    board_viewe_b.yaml
    gnss_passivo.yaml
    display_800x480_test.yaml
  components/goats_core/                  # Componente locale ESPHome Python/C++
  src/timing/timing_contract.h            # Interfaccia, senza motore fittizio
  src/ui/layout_reference.h               # Geometria di riferimento
  src/storage/                           # Area per lo sviluppo storage
  docs/
    riferimento_rlcd.md
    hardware.md
    verifica.md
  tests/
    check_contracts.py
    test_nav_pvt.cpp
  requirements-dev.txt
```

## Apertura in ESPHome Builder su Windows

Selezionare **questa cartella**, non la root della repository e non `firmware/`.
Aprire `goats_5_transflettivo.yaml` per il progetto base. Mantenere accanto al YAML
le cartelle `config` e `components`: non copiare il solo file YAML.

Per la sola test card del pannello aprire invece
`goats_5_transflettivo_display_test.yaml`. Il test non contiene un'interfaccia Racing.

```powershell
Set-Location 'C:\percorso\TELEMETRY\5 pollici transflettivo'
python -m esphome config goats_5_transflettivo.yaml
python -m esphome compile --only-generate goats_5_transflettivo.yaml
python -m esphome compile goats_5_transflettivo.yaml
```

Versione ESPHome usata per i controlli: 2026.7.3. Nessun caricamento sul dispositivo
viene eseguito automaticamente. Stato delle verifiche in `docs/verifica.md`.
I contratti in `src/` documentano i moduli futuri e non vengono ancora compilati
nel firmware; il componente attivo e' quello locale in `components/goats_core`.

## GPS: collegamenti previsti

| Segnale | Collegamento |
|---|---|
| TX del GNSS | GPIO17 della scheda VIEWE, ingresso UART ESP32 |
| GND GNSS | GND comune della scheda |
| RX del GNSS | Lasciato scollegato dall'ESP32 |
| Alimentazione GNSS | Alimentazione richiesta dal modulo effettivo, non da GPIO17 |

GPIO17 e' indicato libero nella tabella della scheda WB-B, p.9. Non si puo'
conservare RX GPIO1 del RLCD: sulla VIEWE GPIO1 e' un dato blu del display.
L'ingresso deve ricevere livelli logici compatibili con ESP32-S3; alimentazione
del modulo e livello del suo TX sono due verifiche distinte.

Come nel riferimento RLCD, il ricevitore deve essere **gia' configurato** per
UBX NAV-PVT a **25 Hz, 230400 baud, 8N1**. Il firmware non imposta la frequenza,
non modifica costellazioni e non trasmette configurazioni al GNSS.

## Riferimento RLCD e sviluppo successivo

Layout Racing, rilevamento traguardo, intermedi, interpolazione eventualmente
prevista dal riferimento, tempi giro, BEST, delta e sessioni vanno sviluppati
rispettando il contratto in `docs/riferimento_rlcd.md`. Lo stato di ogni ambito
e' esplicito: l'interfaccia timing non e' un motore implementato.

Sviluppi successivi: motore e tracce di test, renderer Racing, due comandi fisici
con pressione breve/lunga, coda GPS, SD e sessioni, trasporto Manager. Nessun GPIO
per i pulsanti e' abilitato automaticamente in questa versione.

Il connettore USB di bordo usa CH340C/UART: non abilita da solo USB MSC nativo.
Il progetto non implementa ancora trasferimenti Manager o modalita' disco.

## Fonti hardware

- `PLCM-UEDX80480050E-WB-B V1.0 SPEC.pdf`: p.5/7/9 per CPU, memoria e GPIO.
- `UEED050WV-RB40-L001 V1.0 SPEC.pdf`: p.4/7/10 per pannello e timing.
- [Repository ufficiale VIEWE](https://github.com/VIEWESMART/UEDX80480050ESP32-5inch-Touch-Display),
  revisione consultata `f97ece951d035a859573727c264993b9fe28fef6`.

I PDF sono fonti tecniche, non istruzioni operative impartite dall'utente.
Le indicazioni sul touch nei documenti non prevalgono sulla scelta esplicita
di usare un pannello non touch. Nessun PDF e' stato aggiunto alla repository.
