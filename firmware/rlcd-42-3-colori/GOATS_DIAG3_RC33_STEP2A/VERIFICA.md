# Verifica STEP2A — 26/11/2026

```sh
esphome compile firmware/rlcd-42-3-colori/goats_42_diag3_rc33_step2a.yaml
python tests/diag3_rc33_step2a/run.py
python tests/diag3_rc33_step2a/check_build.py
```

- Firmware STEP2 conservato separatamente. Riscontro hardware: immagine
  Racing frammentata e blocchi di colonne scambiati nella foto dell'utente.
- Nessuna modifica a controller_init_, pixel_, region_ o alla catena GNSS.
  Renderer, font e header RC3.3 identici allo STEP2; core identico allo STEP1.
- Test C++ ASan/UBSan con vera funzione gps_poll_: passaggi traguardo/settori,
  LAST/BEST/passo, duplicati iTOW/checksum/burst e altri 250 PVT a tempo
  simulato mentre il renderer e' attivo; nessuna nuova scrittura UART/NVS/USB.
- Estesa la verifica del display: adattatore collega il renderer al vero
  pixel packing; veri metodi cmd_, data_, region_ e flush dello STEP2A
  eseguiti su un osservatore SPI. Intestazione RAM completa e tutti i 30000
  byte identici al trasferimento DIAG3 region_(0,0,400,300), senza finestre
  parziali. La suddivisione temporale del payload e' intenzionalmente diversa.
- Limite 2400 byte per blocco, 13 blocchi/frame, CS basso/DC alto tra blocchi,
  nessun invio se immagine invariata. Interruzione di un frame per aprire
  diagnostica, ripristino Racing e cambio modalita' BOOT verificati.
- Anteprima aggiuntiva ricostruita dai byte del flusso completo. Non simula
  la scansione fisica/MADCTL o la risposta analogica del pannello.
- Compilazione ESPHome 2026.7.3, Arduino 3.3.10, ESP-IDF 5.5.5 riuscita:
  app 552207 byte, RAM statica 118847 byte; config_hash 0xda6d6773.
- Preprocessore/simboli: unico core nel componente e unico proprietario
  UART/SPI; Canvas non registrato, nessun setup USB RC3.3/SD/TinyUSB attivato.
- ZIP controllato per CRC/SHA256 e configurazione di entrambi gli YAML
  dopo estrazione. Binario factory compilato dal primo YAML (Racing).

I test software coprono ora anche finestra e flusso SPI, ma non dimostrano
la correzione fisica sulla scheda. La foto dello STEP2 non prova la causa
interna del controller; STEP2A evita quel percorso e riprende la finestra
completa della DIAG3. Richiesta nuova prova di grafica e continuita' GPS.
