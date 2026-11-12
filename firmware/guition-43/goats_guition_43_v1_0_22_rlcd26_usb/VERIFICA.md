# Verifica V1.0.22 - 12/11/2026

PR: https://github.com/ady1972/TELEMETRY/pull/2
Branch: porting/guition-v1.0.22-rlcd26

La revisione 567943375d758775040009b592c49ebd0d29a44e ha superato test C++,
invarianti, config e compilazione ESPHome 2026.7.3 su Linux:
https://github.com/ady1972/TELEMETRY/actions/runs/43251108462
RAM statica 169123 / 341760 byte (49,5%); immagine 1206519 / 1835008 byte (65,8%).

La protezione finale sul cambio pista/catalogo e' sottoposta a una nuova
esecuzione CI; aggiornare questo rapporto con il risultato prima di distribuire.

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
