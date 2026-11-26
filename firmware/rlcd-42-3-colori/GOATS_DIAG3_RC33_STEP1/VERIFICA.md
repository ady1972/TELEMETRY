# Verifica DIAG3 + RC3.3 STEP1 — 26/11/2026

```sh
python tests/diag3_rc33_step1/run.py
esphome compile firmware/rlcd-42-3-colori/goats_42_diag3_rc33_step1.yaml
python tests/diag3_rc33_step1/check_build.py
```

Esiti software:

- Configuratore, parser, osservatore stabilita', UART/logger/framework/partizioni,
  schema componente, pin, setup e funzioni LCD/SPI confrontati con DIAG3: invariati.
- Metodo della pagina DIAG3 identico salvo titolo e riga CORE; velocita' 60px,
  freschezza dei dati e indicatori di fix conservati.
- Motore e tipi RC3.3, session state, massima velocita' e bridge Racing conservati;
  negli include privati cambiano solo guardie e nomi/percorso degli header.
  Nel consumatore RC3.3 l'include esphome.h e' sostituito dal solo HAL per
  evitare inclusioni ricorsive; i corpi delle funzioni restano quelli RC3.3.
- C++ ASan/UBSan: vera funzione gps_poll_ della variante, catalogo copiato in RAM,
  traguardo/giro/settore, LAST/BEST/passo/velocita' media rispetto a un'istanza
  diretta del motore, massimo per giro e stato sessione: PASS.
- Duplicati iTOW e checksum errati esclusi dal core, differenza fix 2D/3D,
  100 PVT in burst elaborati una sola volta, coda legacy svuotata senza
  duplicazione, guardia prima della configurazione e UART nulla: PASS.
- Nessuna chiamata USB, nuova lettura/scrittura NVS o comando UART aggiuntivo
  durante attach/consumo dei campioni nel test. La NVS originale DIAG3 di avvio
  resta parte della base e non viene descritta come assente.
- Preprocessore reale: un solo motore RC3.3 nel componente, assente in main;
  clock originale e unico poll DIAG3. Nel binario non sono collegati setup/tick
  USB della RC3.3, mount SD o TinyUSB: PASS.
- ESPHome 2026.7.3 / Arduino 3.3.10 / ESP-IDF 5.5.5: compilazione PASS.
  App 379903 byte, RAM statica 88151 byte.
- ZIP controllato per CRC, SHA256 e configurazione ESPHome dopo estrazione.

La DIAG3 di riferimento ha conferma positiva dell'utente. STEP1 richiede
il nuovo riscontro hardware: i test software non dimostrano da soli la
continuita' GPS o il cronometraggio sul dispositivo.
