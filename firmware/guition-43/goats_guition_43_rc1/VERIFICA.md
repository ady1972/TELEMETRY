# Promozione RC1 — 13/11/2026

Base: Guition V1.0.22 RLCD26 USB. L’utente conferma l’allineamento di tempi
e funzionamento con RLCD TEST26 nell’ultimo test comparativo.
Aggiornati solo identificativi RC1 e percorsi del pacchetto; logiche invariate.
Il rapporto seguente riguarda la base V1.0.22 e non una nuova prova hardware RC1.

# Verifica V1.0.22 - 12/11/2026

PR: https://github.com/ady1972/TELEMETRY/pull/2
Branch: porting/guition-v1.0.22-rlcd26

Revisione del codice verificata: 6070b97904a08d964ec55ffc8ec10b65625b293c.
Esito finale: SUCCESS, test C++ e compilazione ESPHome 2026.7.3 su Linux.
https://github.com/ady1972/TELEMETRY/actions/runs/43252047337

- PASS: invarianti (motore, GNSS/UART, Racing, GSA3/CSV/protocollo).
- PASS: FIFO, rollover iTOW, duplicati e controllo CRC GSE.
- PASS: 250 punti distinti con passo di 40 ms, attribuzione al giro corretto
  e assenza di I/O nel consumatore NAV.
- PASS: lettura con il codice GSA3 originale V1.0.20, riapertura con settori,
  recupero NVS senza SD e protezione dei metadati legacy in conflitto.
- PASS: scarto senza perdita di giri storici, chiusura libera, fix invalidi,
  scrittura CSV fallita e indisponibilita' simultanea di SD/NVS.
- PASS: adattatore delle due API dropdown e richiesta di chiusura differita.
- PASS: config, compilazione/link ESP32-S3 e generazione firmware.factory.bin.
- RAM statica: 169139 / 341760 byte (49,5%).
- Immagine applicazione: 1206767 / 1835008 byte (65,8%).
- Artifact: GOATS-Guition-V1.0.22-USB, ID 13961290339.
  SHA256 dello ZIP CI: dd4502bcadaef4fbcd9f9997ae5792d66ee40f4a39aa6e2745b55cdfb5d84f14.

Gli aggiornamenti successivi del solo rapporto non cambiano il codice compilato.

Verificato staticamente: goats_laptimer.h identico byte per byte alla V1.0.20;
dipendenze GNSS, UART/pin/230400/25 Hz, logger e layout Racing preservati.
GSA3 e GSA2 vengono letti dal parser originale; il serializer GSA3 e lo schema
CSV sono invariati. USB cambia solo per accessor busy read-only e adattatore
GUI set_options compatibile con le API ESPHome; nessun messaggio modificato.

I test host includono il lettore originale V1.0.20 e la logica reale del nuovo
gestore, con I/O simulato. Non costituiscono un test del dispositivo.
Nessuna verifica hardware di display, GNSS, SD, USB MSC o Manager eseguita.
Nessuna verifica in pista, di consumo RAM dinamico o latenza SD reale.

Su questo host Windows, la compilazione Xtensa e' bloccata da WinError 623;
il compilatore host Zig termina con 0xC0000005. La verifica Linux evita tali
problemi dell'ambiente. Sono stati corretti gli header ESPHome mancanti,
l'argomento stage del writer GSE e l'incompatibilita' set_options della base.

Limiti conservati dal riferimento: iTOW non usato dal motore, attraversamenti
non interpolati temporalmente, validazione giri limitata alle regole originali.
FatFS e NVS sono differiti ma possono bloccare il task; il diario non sostituisce
la traccia CSV quando la SD manca. Inserire la scheda prima dell'avvio;
l'inserimento a caldo e le riconnessioni durante la sessione non sono gestiti.
