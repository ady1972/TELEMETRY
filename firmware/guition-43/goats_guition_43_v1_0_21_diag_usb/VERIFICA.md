# Verifica V1.0.21 DIAG USB - 12/11/2026

- PASS: `python tests/guition_diag/check_invariants.py`.
- PASS: nessuna modifica ai file V1.0.20 o RLCD rispetto al commit base.
- PASS: `goats_laptimer.h` identico byte per byte.
- PASS: configurazioni UART/ESP32/logger, globals e struttura LVGL invariati
  (sole stringhe versione/build aggiornate); dipendenze GNSS identiche.
- PASS: codice SD e sessioni identico dopo rimozione degli hook diagnostici;
  implementazione USB identica dopo rimozione del solo accessor read-only busy.
- PASS: `python -m esphome config ...yaml`, ESPHome 2026.7.3.
- PASS: generazione C++ ESPHome, eseguita all'avvio di `compile`.
- NON COMPLETATA: compilazione ESP32. Dopo aver spostato la cache nella cartella
  di lavoro per superare un errore di accesso, ESP-IDF 5.5.5 si scarica ma
  l'installazione della toolchain si interrompe: il compilatore
  xtensa-esp-elf esp-14.2.0_20260121 non si avvia con WinError 623
  (rilocazione DLL del sistema non valida). Nessun firmware binario validato.
- NON ESEGUITI: test C++ host. I test sono presenti in tests/guition_diag;
  il tentativo con Zig/Clang 0.17.1 si e' fermato nella costruzione delle
  librerie runtime per errori di rename della cache nell'ambiente Windows.
  Non si dichiara superato un test compilato o eseguito.
- NON ESEGUITE: prove hardware, monitoraggio reale a 25 Hz, misura dell'overhead
  diagnostico, compatibilita' Manager e resa visiva su display.

Warning osservati: `board_build.flash_mode` ignorato dal backend ESP-IDF nativo;
avviso ESPHome su redazione legacy del campo `transparency_key` durante `config`.
Non sono state cambiate opzioni per aggirare questi warning.

Il riepilogo usa il logger esistente, il cui baud_rate resta 0: non c'e'
un'uscita seriale USB visibile in questa configurazione. Contatori e snapshot
restano in RAM; UART_OVF=NA indica assenza di una misura disponibile.
