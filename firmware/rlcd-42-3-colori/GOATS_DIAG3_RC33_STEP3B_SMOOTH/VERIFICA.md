# Verifica STEP3B SMOOTH — 27/11/2026

```sh
esphome compile firmware/rlcd-42-3-colori/goats_42_diag3_rc33_step3b_smooth.yaml
python tests/diag3_rc33_step3b_smooth/run.py
python tests/diag3_rc33_step3b_smooth/check_build.py
```

- Header GPS/configuratore/stabilita'/core/catalogo/store/USB e font uguali a
  STEP3/STEP3A. Layout Racing, geometria, parser, setup e pixel packing uguali.
- Trace reale di controller_init_ su SPI simulato con fast_display false/true:
  solo B2:12 -> B2:15 cambia; HPM/LPM e le altre impostazioni restano identiche.
- Test C++ ASan/UBSan su veri disegno/flush/cancel/input. Copiati dichiarazione
  e metodi HighFrequencyLoopRequester dalla versione ESPHome usata nella build:
  avvio su immagine modificata, arresto al completamento/cancel/nessun dato,
  idempotenza, rispetto della richiesta di un altro componente verificati.
- Finestra e 30000 byte identici alla DIAG3; 13 blocchi, ciascuno <=2400 byte.
  Il modello di scheduler usa 16 ms fra invocazioni senza richiesta rapida
  e arrotonda il payload dei blocchi al millisecondo: 255 ms nel profilo
  precedente contro 63 ms con richiesta rapida. E' una simulazione, non un
  benchmark della scheda e non una misura di frame rate/refresh fisico.
- Il GPS e' chiamato prima del blocco nel loop reale; nessun ritardo esplicito
  nuovo o ciclo monolitico che invii tutti i 30000 byte in una singola chiamata.
- Test dei font compilati, entrambe le modalita' Racing, avvisi, pagina di
  prova con orologio UI, packing, ritorno dalla diagnostica e BOOT passati.
- Preprocessore/ELF: un solo core/UART/controller, requester nativo collegato,
  fast_display attivo nel main, nessun setup USB legacy o SD/TinyUSB/MSC.
- ESPHome 2026.7.3 / Arduino 3.3.10 / IDF 5.5.5: compilazione riuscita.
  App 616415 byte, RAM statica 150575 byte, config_hash 0xe39dd177.
- Tre YAML validati dopo estrazione dello ZIP; CRC/SHA256 controllati.

Non e' stato fatto un nuovo test fisico del pannello o del GPS. La frequenza
8 Hz e' il valore nominale da datasheet della configurazione, non una misura.
La DIAG3 mantiene la propria pagina a 1 s; per valutare la fluidita' usare
Racing oppure lo YAML di prova. I tempi giro restano calcolati dal core originale.
