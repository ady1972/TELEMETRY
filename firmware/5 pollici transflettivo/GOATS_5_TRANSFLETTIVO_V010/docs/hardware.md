# Profilo hardware iniziale

Scheda prevista: PLCM-UEDX80480050E-WB-B, ESP32-S3 con 16 MB flash/8 MB PSRAM.
Pannello previsto: UEED050WV-RB40-L001, 5.0 pollici transflettivo, RGB 800x480.
La scelta dell'utente e' NON TOUCH: nessun GT911 o I2C viene inizializzato.

| Funzione | GPIO |
|---|---|
| GNSS RX | 17 (libero nella spec WB-B) |
| GNSS TX ESP32 | Assente |
| Backlight enable | 2, PWM a 1 kHz, 50% all'avvio |
| LCD R0..R4 (RGB565) | 45, 48, 47, 21, 14 |
| LCD G0..G5 | 5, 6, 7, 15, 16, 4 |
| LCD B0..B4 | 8, 3, 46, 9, 1 |
| HSYNC / DE / VSYNC / PCLK | 39 / 40 / 41 / 42 |
| SD CS / MOSI / CLK / MISO | 10 / 11 / 12 / 13, riservati e non attivi |
| UART0 scheda | 43/44, non usata per GNSS |
| Pin touch della scheda | 18/19/20/38, non configurati da questo progetto |

Il PDF del modulo completo riporta anche un allestimento touch e controller
ST7262/ST72611; il pannello transflettivo riporta ST7282A nella tabella p.4 e
JD9165 nel disegno p.6. Queste discrepanze non sono risolte dal firmware.
Il profilo opzionale usa il solo flusso RGB, senza sequenze SPI inventate.

## Bring-up display

La variante display_test usa la test card ESPHome. I timing sono una prima
interpretazione della tabella p.10 del pannello: 32.4 MHz, totale 1000x540,
60 Hz nominali, pixel clock invertito. HBP/VBP sono interpretati inclusivi
degli impulsi HS/VS (160-24 e 23-2). Verificare questa lettura al banco o con
il produttore prima di considerare definitivo il profilo.

Il firmware principale attiva la schermata dati GPS; la variante display_test
mostra la test card RGB. Entrambi usano lo stesso profilo del pannello e la
retroilluminazione al 50% (LEDC, gamma 1.0). Nessuna interfaccia touch viene
configurata. L'utente ha osservato la scritta RGB con la precedente variante di
test; la nuova schermata GPS e la regolazione PWM richiedono collaudo sul dispositivo.

## GPS

TX GNSS -> GPIO17; GND comune; RX del ricevitore non collegato all'ESP32.
Alimentare il modulo secondo la propria scheda tecnica. Non alimentarlo da un GPIO.
Il TX deve essere compatibile con i livelli di ingresso ESP32-S3.

Come RLCD: ricezione passiva, UBX NAV-PVT, 230400 baud, 25 Hz gia' impostati
esternamente. Il progetto non invia comandi di inizializzazione o cambio frequenza.
La diagnostica legge anche NAV-SAT (visti con C/N0 >0 e costellazioni) e NAV-DOP
(HDOP): questi messaggi devono essere gia' abilitati sul ricevitore. In loro
assenza la schermata indica `--`. Non viene aggiunto un collegamento TX ESP32.

## USB

La USB Type-C della scheda usa CH340C/UART, non equivale alla USB serial/JTAG
del RLCD. Non vengono abilitati Manager, USB MSC o protocolli alternativi nello
scaffold. L'eventuale uso dei pin 19/20 per USB nativa richiede un progetto
hardware esplicito; non deriva automaticamente dall'assenza del touch.
