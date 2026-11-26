# Verifica STEP2 — 26/11/2026

```sh
python tests/diag3_rc33_step2/run.py
esphome compile firmware/rlcd-42-3-colori/goats_42_diag3_rc33_step2.yaml
python tests/diag3_rc33_step2/check_build.py
```

- Confronto con DIAG3/STEP1: UART, configuratore/parser/stabilita', unico poll,
  setup originale, funzioni controller LCD/pixel packing/trasferimento invariati.
  Cambia il disegno successivo alla configurazione, non l'avvio GNSS.
- Motore/consumer/circuiti RC3.3 dello STEP1 identici. Test precedente riusato
  sullo STEP2, con vero metodo gps_poll_: traguardo/settori/LAST/BEST/passo,
  velocita' media/massima, stato sessione, iTOW duplicati, checksum errato,
  differenza 2D/3D, burst 100 PVT senza duplicazione: PASS con ASan/UBSan.
- Nello stesso test C++: ulteriori 250 NAV-PVT a passo simulato di 40 ms,
  motore reale e renderer reale attivi insieme; disegno con glyph ESPHome
  ogni cinque campioni, contatori corretti e nessuna scrittura UART/NVS/USB.
  La simulazione non misura il tempo CPU o il jitter del dispositivo.
- Corpo Racing confrontato con YAML RC3.3. Sole sostituzioni: font generati
  passati come parametri, lettura stato DIAG3, scelta modalita' in RAM,
  menu sempre assente, indicatore batteria senza lettura ADC.
- Header post-giro RC3.3 identico dentro guardia privata. Capture nel loop
  dopo il poll; LAST LAP e NEW BEST LAP, lampeggio testo e durata originali.
- Renderer eseguito con i bitmap glyph realmente prodotti dalla compilazione
  ESPHome. Modalita' LAP TIME/DELTA, GPS fresco/scaduto, LAST LAP/NEW BEST,
  packing 400x300, ritorno diagnostica/Racing, BOOT breve/lungo: PASS.
- Funzione di flush reale: nessun invio se invariato; immagine completa in
  massimo 13 blocchi; singolo blocco <=2400 byte; nessun residuo di pagina
  nella simulazione del pannello. Non e' una misura del ghosting fisico LCD.
- Preprocessore e simboli del binario: un solo motore privato nel componente,
  assente dal main; Canvas non registrato; un solo UART e controller hardware;
  setup/tick USB RC3.3, mount SD e TinyUSB assenti: PASS.
- ESPHome 2026.7.3, Arduino 3.3.10, ESP-IDF 5.5.5: compilazione PASS.
  App 552135 byte, RAM statica 118847 byte; config_hash 0xd93c263d.
- YAML diagnostico validato; cambia solo nome/avvio pagina, stesso componente.
- ZIP: CRC, SHA256 e validazione dei due YAML dopo estrazione.

DIAG3 e STEP1 hanno riscontro hardware positivo dell'utente. STEP2 non e'
ancora stato provato sul dispositivo; continuita' GPS, refresh e leggibilita'
sono da confermare con la nuova prova. Nessun archivio/sessione persistente
RC3.3, nessuna SD, nessun trasporto Manager e nessun ADC introdotti.
