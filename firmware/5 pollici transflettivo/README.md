# GOATS RT - 5 pollici transflettivo

Nuovo progetto autonomo ESP32-S3/ESPHome, creato da zero esclusivamente in questa
cartella. Il display previsto e' **non touch**. RLCD TEST26 e' il riferimento
funzionale e grafico, non una libreria inclusa dallo scaffold.

**Versione 0.1.0: acquisizione e schermata GPS, non firmware completo di cronometraggio.**
Non vengono ancora prodotti tempi giro, settori, delta, sessioni o file CSV.
Non sono stati copiati i firmware RLCD o Guition, ne' modificati file esterni.

## Cosa e' presente

- Configurazione ESPHome ESP32-S3, flash 16 MB e PSRAM octal 8 MB prevista dalla scheda.
- Profilo di base per PLCM-UEDX80480050E-WB-B e pannello UEED050WV-RB40-L001.
- Componente C++ locale `goats_core`, scritto da zero.
- Acquisizione passiva UBX NAV-PVT: checksum, posizione, velocita', fix, satelliti,
  timestamp iTOW, istante ESP e conteggio dei duplicati consecutivi.
- Diagnostica RLCD: NAV-SAT per satelliti visti e costellazioni, NAV-DOP per HDOP,
  frequenza NAV-PVT misurata su finestre di 2 secondi.
- Poll UART con budget limitato; nessuna scrittura UART o operazione SD nel parser.
- Contratti iniziali per timing e geometria UI, separati dal codice di acquisizione.
- Schermata GPS 800x480 con stato fix, satelliti, velocita', coordinate e diagnostica.
- Retroilluminazione al 50% all'avvio, tramite PWM su GPIO2.
- Variante opzionale per la sola test card del display RGB 800x480.
- Nessun Wi-Fi, OTA, touchscreen, GT911, bus I2C o protocollo Manager attivo.

## Struttura

```text
goats_5_transflettivo.yaml
goats_5_transflettivo_display_test.yaml
GOATS_5_TRANSFLETTIVO_V010/
  config/
  components/goats_core/
  src/timing/
  src/ui/
  src/storage/
  docs/
  tests/
  requirements-dev.txt
```

## Apertura in ESPHome Builder su Windows

Copiare nel workspace ESPHome Builder i due YAML e l'intera cartella
`GOATS_5_TRANSFLETTIVO_V010`, mantenendoli affiancati. Aprire
`goats_5_transflettivo.yaml` per la schermata GPS. Tutti i componenti e gli
include puntano alla cartella dedicata; non serve una cartella `components`
comune agli altri dispositivi. È possibile anche usare direttamente questa
cartella del repository come workspace.

Per la sola test card del pannello aprire invece
`goats_5_transflettivo_display_test.yaml`. Il test non contiene un'interfaccia Racing.
Anche questa variante usa la retroilluminazione al 50%.

## Schermata dati GPS

Il firmware principale inizializza il pannello con gli stessi pin e timing della
test card che ha mostrato RGB. La schermata si aggiorna ogni 250 ms e distingue
attesa dei messaggi, ricezione senza fix, fix valido e dati non aggiornati da almeno
3 secondi. Velocita' e coordinate compaiono solo con un fix valido e recente;
senza dati recenti i valori sono sostituiti da trattini. I satelliti restano visibili
anche durante la ricerca del fix, se i messaggi continuano ad arrivare.

Il riquadro **SATELLITI VISTI / USATI** distingue i satelliti con C/N0 maggiore di
zero nei messaggi NAV-SAT (stessa regola RLCD) dal numero usato nella soluzione,
riportato da NAV-PVT. Il fondo mostra anche GPS, Galileo, BeiDou, GLONASS e SBAS.
Gli altri sistemi contribuiscono al totale dei visti senza un contatore dedicato.
La ricezione NAV-SAT puo' quindi mostrare satelliti visti anche senza fix.
Senza NAV-SAT, oppure dopo 5 secondi senza nuovi dati, il campo visti mostra `--`,
non uno zero inventato. Anche HDOP da NAV-DOP scade dopo 5 secondi.

Il fondo mostra numero di messaggi NAV-PVT, duplicati ed errori checksum, utili per
verificare la ricezione. In alto compaiono HDOP e frequenza PVT effettiva, misurata
ogni 2 secondi come nella diagnostica RLCD. Non viene inviata alcuna configurazione al ricevitore.
La luminosita' iniziale e' 50%, con PWM a 1 kHz e correzione gamma 1.0.

```powershell
Set-Location 'C:\percorso\TELEMETRY\firmware\5 pollici transflettivo'
python -m esphome config goats_5_transflettivo.yaml
python -m esphome compile --only-generate goats_5_transflettivo.yaml
python -m esphome compile goats_5_transflettivo.yaml
```

Versione ESPHome usata per i controlli: 2026.7.3. Nessun caricamento sul dispositivo
viene eseguito automaticamente. Stato delle verifiche in `GOATS_5_TRANSFLETTIVO_V010/docs/verifica.md`.
I contratti in `GOATS_5_TRANSFLETTIVO_V010/src/` documentano i moduli futuri e non vengono ancora compilati
nel firmware; il componente attivo e' quello locale in `GOATS_5_TRANSFLETTIVO_V010/components/goats_core`.

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
Per visualizzare i visti deve trasmettere anche **UBX NAV-SAT** (tipicamente 1 Hz);
per HDOP deve trasmettere **UBX NAV-DOP**. Il solo NAV-PVT non contiene il numero
dei satelliti visti. Il criterio di fix resta quello RLCD: tipo >=3, gnssFixOK,
almeno 4 satelliti usati e coordinate nei limiti geografici.

## Riferimento RLCD e sviluppo successivo

Layout Racing, rilevamento traguardo, intermedi, interpolazione eventualmente
prevista dal riferimento, tempi giro, BEST, delta e sessioni vanno sviluppati
rispettando il contratto in `GOATS_5_TRANSFLETTIVO_V010/docs/riferimento_rlcd.md`. Lo stato di ogni ambito
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
