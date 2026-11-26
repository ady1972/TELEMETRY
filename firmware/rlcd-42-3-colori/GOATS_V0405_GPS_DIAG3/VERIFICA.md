# Verifica GPS DIAG3 — 26/11/2026

- `python tests/gnss_diag3/run.py`: PASS.
- Confronto con la DIAG2: configuratore e parser byte per byte identici;
  UART/logger/framework/partizioni e funzione gps_poll_ originali conservati.
- C++ ASan/UBSan: stessi 17 frame UBX, cambi baud e ritardi; stesso stato
  navigazione e coda campioni; singola lettura, corruzioni/lunghezze/frame
  frammentati/burst e time-out; regressione clock Arduino/ESPHome: PASS.
- Osservatore reale: primo periodo senza fix, fix 2D/3D/GNSS+DR, esclusione
  tempo-only e DR-only, flag di validita', perdite di fix e di flusso una sola
  volta, scadenza DOP/SAT, frequenza effettiva lenta, duplicati/iTOW retrogrado,
  rollover settimana GNSS e timer a 32 bit: PASS.
- Metodo reale gps_diag_draw_ eseguito su host con font bitmap originali:
  valori freschi, campi mai ricevuti/scaduti, aggiornamenti indipendenti,
  velocita' nascosta senza fix, orologi con epoche differenti e limiti 400x300:
  PASS. Velocita' nativa a 60 px e punto decimale alla base verificati.
  L'anteprima usa valori simulati, non misure hardware.
- Compilazione ESPHome 2026.7.3 / Arduino 3.3.10 / ESP-IDF 5.5.5: PASS.
  App 375747 byte; RAM statica 87991 byte.
- Archivio consegnato verificato per CRC ZIP, SHA256 e validazione ESPHome
  dei sorgenti dopo estrazione.

Queste prove non confermano che la DIAG3 comunichi sul dispositivo dell'utente:
la DIAG2 di riferimento ha comunicazione/fix confermati, la DIAG3 richiede
la nuova prova. L'esito dei porting RC3.3 resta separato da questo diagnostico.
