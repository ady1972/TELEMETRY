# RC3.3 UART0 — allineamento al logger della COLOR funzionante

Il 26 novembre 2026 l'utente ha ricaricato tramite ESPHome la V0.40.5 originale,
sugli stessi collegamenti, e ha confermato che il GPS funziona. Sulla RC3.3 e
su GPS TEST2 RX/UBX/PVT/SAT restano a zero anche dopo l'attesa; POLL e UPTIME
invece aumentano. Il solo cambio baud senza reinstallare il driver non ha
risolto il difetto osservato. Non è un lettore mai eseguito: la prima foto
TEST2 mostrava i suoi valori iniziali.

## Differenza isolata

La V0.40.5 usa `logger: {level: INFO, baud_rate: 0}`. La RC3.3 riserva invece
UART0 al logger seriale a 115200, spostando il GPS su UART1 (U1 nella foto).
Il backend ESPHome assegna la prima UART disponibile saltando quella occupata
dal logger, se la velocità di logging è maggiore di zero.

Questa variante disattiva soltanto il log seriale, come la COLOR. Con un solo
bus UART, il GPS riceve quindi UART0 e conserva **RX GPIO1 / TX GPIO2**. Non si
spostano fili. È una differenza verificata nel codice e nella configurazione,
non ancora una causa dimostrata del guasto sul dispositivo: resta da provare.

Il framework rimane ESP-IDF per preservare l'integrazione RC3.3 di SD e USB.
GNSS, configuratore e parser COLOR, comandi inviati, baud finale 230400,
NAV-PVT richiesto 25 Hz, timer e motore laptimer restano quelli della variante
precedente. Le schermate Racing/menu/font non cambiano. Lo splash resta assente.
Il protocollo USB del Manager e MSC non vengono modificati; l'installazione
richiesta dall'utente continua tramite **ESPHome via USB**.

## Sorgenti e caricamento

Scaricare [RC3.3 UART0 per ESPHome](download/GOATS_RLCD_COLOR_RC3.3_UART0_SORGENTI.zip).
Estrarre e mantenere affiancati:

```text
goats_42_color_rc3_3.yaml
goats_42_color_rc3_3_uart0.yaml
goats_42_color_rc3_3_uart0_diag.yaml
GOATS_RLCD_COLOR_RC3_3/
```

Per la prova senza tasti aprire **`goats_42_color_rc3_3_uart0_diag.yaml`**,
compilare e installare con ESPHome, su ESP32-S3 da **16 MB**. Spegnere
completamente ESP e GPS, poi riaccendere. Il titolo sarà **RC3.3 - GPS UART0**
e la prima riga dovrà indicare **U0**, con baud SET/HW prossimo a 230400.
Dopo circa 60 secondi verificare se RX e UBX aumentano e fotografare la pagina.
Per il fix a freddo possono servire alcuni minuti in condizioni di ricezione.

Il firmware completo con Racing RC3.3 è **`goats_42_color_rc3_3_uart0.yaml`**:
usa lo stesso GNSS e lo stesso logger disattivato della diagnostica, con il
rendering operativo RC3.3. Può essere caricato dopo la verifica del GPS.
Lo YAML base e tutti i pacchetti precedenti restano conservati.

## Verifiche

`check_uart0.py` confronta le configurazioni ESPHome risolte delle varianti:
solo baud del logger, nomi descrittivi e rendering diagnostico possono variare.
Il renderer Racing coincide integralmente con il base; boot, UART/pin, core,
intervalli, font, display SPI, tasti, SD e USB coincidono.

Il test estrae ed esegue anche la funzione `IDFUARTComponent::setup()` reale
installata con ESPHome: logger seriale a 115200 assegna UART1 al GPS, mentre
logger a zero assegna UART0. ASan/UBSan abilitati. Questo prova la selezione
della periferica nel software, non la ricezione elettrica sul dispositivo.
Configurazione e compilazione ESPHome 2026.7.3 / ESP-IDF 5.5.5: **PASS** per
entrambe le varianti. Diagnostica: app 598.375 byte, RAM statica 164.323 byte;
Racing: app 606.699 byte, RAM statica 164.331 byte. I test del configuratore
passano anche sul ramo ESP-IDF, con frame e attese originali invariati.
Entrambi gli YAML dello ZIP sono estratti e validati separatamente; integrità
ZIP e SHA-256 verificati. Nessun collaudo hardware eseguito sulla variante UART0.
