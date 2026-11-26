# Diagnostica GPS RC3.3 senza tasti — 26 novembre 2026

L'utente segnala GPS assente nell'ultimo firmware già all'accensione e non può
aprire Info GPS perché i pulsanti non sono ancora saldati. La foto della barra
GPS da sola non permette di distinguere assenza di traffico UART, mancata
ricezione NAV-PVT o ricezione senza fix. La causa non è ancora identificata.

La variante `goats_42_color_rc3_3_gps_diag.yaml` mostra automaticamente una
pagina diagnostica e la mantiene visibile. È un overlay dello YAML normale:
stessi GNSS, configuratore V0.40.5, UART RX1/TX2, intervalli e motore RC3.3.
Cambia soltanto il rendering e il nome descrittivo. I contatori ACK/NAK aggiunti
all'adattatore osservano le risposte del ricevitore, senza inviare comandi
aggiuntivi né cambiare baud o configurazione.

[Firmware USB diagnostico](download/GOATS_RLCD_COLOR_RC3.3_GPS_DIAG_SENZA_TASTI_USB.zip) ·
[Sorgenti diagnostici](download/GOATS_RLCD_COLOR_RC3.3_GPS_DIAG_SENZA_TASTI_SORGENTI.zip).
I pacchetti normali RC3.3_GNSS_V0405 restano conservati.

## Uso

1. Caricare il pacchetto **GPS_DIAG_SENZA_TASTI**, per ESP32-S3 da **16 MB**.
   La factory completa si scrive a **0x0** con la stessa procedura del firmware
   normale. Esportare le sessioni importanti prima del flash.
2. Togliere completamente alimentazione a ESP e GPS, poi riaccendere il
   dispositivo con l'antenna in condizioni di ricezione, preferibilmente all'aperto.
3. Attendere circa 30 secondi e fotografare **tutta la pagina DIAG GPS**.
   Per valutare il fix a freddo attendere anche qualche minuto. Nessun tasto richiesto.
4. Per tornare alla Racing caricare il pacchetto normale RC3.3_GNSS_V0405.
   Questo firmware diagnostico mantiene sempre la pagina di controllo.

Non serve modificare il cablaggio per leggere la diagnosi. Le linee previste
restano TX GPS → GPIO1 e RX GPS → GPIO2, con GND comune.

## Significato dei dati

| Campo | Cosa misura |
|---|---|
| UART | Baud impostato sull'ESP, non una conferma del baud del ricevitore |
| RX / UBX | Byte letti / pacchetti con checksum UBX valido |
| NAV-PVT | Frequenza dei messaggi di navigazione, anche senza fix |
| SAT / FIX / OK | Satelliti usati/visibili; fixType e gnssFixOK del NAV-PVT |
| HDOP / CKERR | Ultimo HDOP ricevuto / pacchetti UBX con checksum errato |
| ACK CFG / NAK | Risposte di accettazione/rifiuto comandi CFG osservate dopo il bootstrap |
| ULTIMO PVT | Tempo dall'ultimo NAV-PVT o indicazione che non è mai arrivato |

- RX fermo a zero: nessun byte disponibile dal GPS sulla UART; il firmware
  non può dedurre da solo se la causa sia collegamento, alimentazione o ricevitore.
- RX cresce, UBX resta zero: arrivano byte, ma non pacchetti UBX validi.
- UBX cresce, PVT assente: comunicazione UBX presente, senza navigazione NAV-PVT.
- PVT presente, attesa fix: dati di navigazione ricevuti, ma il criterio RC3.3
  di fix 3D valido con almeno quattro satelliti non è soddisfatto.
- FIX 3D presente: criterio di navigazione RC3.3 soddisfatto con PVT recente.

I contatori sono cumulativi dall'avvio. ACK/NAK non coprono necessariamente
ogni comando: i cambi baud ricaricano la UART e possono perdere risposte già
in coda. ACK zero da solo non dimostra un rifiuto. Non sono introdotti retry,
reset GNSS o modifiche sperimentali ai parametri del ricevitore.

## Verifiche

Configurazione ESPHome risolta: identici UART, on_boot, header GNSS, intervalli,
core, font, SPI e pulsanti rispetto allo YAML normale. I test di ricezione
confermano anche il conteggio dei soli ACK/NAK CFG validi e nessuna consegna
aggiuntiva di NAV-PVT al laptimer. Compilazione ESPHome 2026.7.3 / ESP-IDF 5.5.5: **PASS**, app 603.399 byte,
RAM statica 164.491 byte. Configurazione ESPHome e test della ricezione con
ASan/UBSan: **PASS**. Integrità ZIP, SHA-256 e app nell'immagine factory verificati.
Nessuna prova hardware; questa variante serve a raccogliere i dati necessari
alla correzione.

```sh
# Con Python dell'ambiente ESPHome:
python tests/rlcd_color_gnss_config/check_diagnostics.py
python tests/rlcd_color_gnss_config/run_reception.py
python tests/rlcd_color_gnss_config/run.py
esphome config firmware/rlcd-42-3-colori/goats_42_color_rc3_3_gps_diag.yaml
esphome compile firmware/rlcd-42-3-colori/goats_42_color_rc3_3_gps_diag.yaml
```
