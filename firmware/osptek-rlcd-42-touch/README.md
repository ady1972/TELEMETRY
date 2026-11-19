# GOATS RT · Osptek RLCD 4,2″ touch

Progetto ESPHome per il lap timer ESP32-S3 con pannello monocromatico riflettivo YDP420HT004-V3, 300 × 400 pixel, display ST7305 via SPI e touch FT3269 via I²C. Questa cartella ospiterà gli YAML e i sorgenti per versione. Stato iniziale: pianificazione, collaudo hardware da eseguire.

## Riferimenti per Codex

- [Repository Osptek su Gitee](https://gitee.com/osptek/display-rlcd-4.2inch-300x400)
- [Demo ESP32-S3 con ST7305 e FT3269](https://gitee.com/osptek/display-rlcd-4.2inch-300x400/tree/main/examples/esp32s3-4.2-st7305-bringup)
- [Documentazione della variante touch e schema dell’adattatore](https://github.com/osptek/display-rlcd-4.2inch-300x400/tree/main/versions/YDP420HT004-V3)
- [Firmware RLCD GOATS](../rlcd-42/README.md), [firmware Guition](../guition-43/README.md), [roadmap ufficiale](../../ROADMAP.md) e [istruzioni di sviluppo](../../AGENTS.md).

## Roadmap di allineamento

- [ ] **Identificare l’hardware.** Annotare modello della scheda ESP32-S3, revisione adattatore e orientamento del flat. Risolvere la discrepanza 2,8/3,3 V verificando alimentazione e livelli logici sullo schema della revisione ricevuta. Documentare i GPIO disponibili per display, touch, GNSS, SD e USB.
- [ ] **Collaudare il pannello al banco.** Partire dalla demo Osptek, registrando la revisione usata. Verificare nero, bianco, orientamento orizzontale 400 × 300, bordi e leggibilità. Controllare tocco e rilascio al centro e ai quattro angoli. Salvare pinout, configurazione e risultati.
- [ ] **Preparare il target ESPHome.** Creare nella cartella progetto uno YAML di ingresso e una cartella GOATS dedicata alla versione con driver e risorse. Verificare compilazione, avvio dopo spegnimento e ripetibilità dei test display/touch.
- [ ] **Portare il cronometraggio.** Identificare il commit RLCD ufficiale collaudato al momento del porting e annotarlo. Usare TEST26 come riferimento per traguardo e settori. Conservare MG902/M9N, UBX NAV-PVT a 25 Hz e 230400 baud. Confrontare sugli stessi punti GNSS circuito rilevato, attraversamenti, tempi giro, settori, delta e best lap.
- [ ] **Allineare schermate e comandi.** Riprendere layout monocromatico, modalità DELTA/LAP TIME, sessione libera, menu e riepiloghi della versione ufficiale scelta. Usare il Guition come riferimento per navigazione touch e conferme. Verificare che un singolo tocco generi una sola azione e che gli aggiornamenti grafici consentano l’acquisizione a 25 Hz.
- [ ] **Allineare sessioni e trasferimenti.** Verificare microSD, nomi file, data/ora, formato CSV e flusso USB con i Manager ufficiali. Provare salvataggio, riapertura dopo riavvio e importazione di una sessione. Confrontare numero di punti e intervalli temporali con il riferimento.
- [ ] **Validare in pista.** Affiancare il prototipo a un RLCD ufficiale, confrontare giri e settori con il timing pista e verificare la registrazione durante uno stint. Annotare versioni, durata, scarti osservati, eventuali riavvii e punti mancanti. Preparare lo ZIP completo di YAML, sorgenti e dipendenze dopo il collaudo.

Per ogni fase aggiornare qui il commit di riferimento, le prove eseguite e le anomalie aperte. La promozione a firmware ufficiale richiede un confronto hardware documentato.
