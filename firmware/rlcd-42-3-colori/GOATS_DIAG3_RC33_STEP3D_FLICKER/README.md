# RC3.3 STEP3D — prova isolata dello sfarfallio

Riscontro hardware dell'utente: STEP3C HPM continua a sfarfallare e riduce
l'intensita' dei colori; tornando a `lcd_high_power: false` i caratteri sono
nuovamente leggibili ma lo sfarfallio rimane. Il profilo HPM non viene proposto
come soluzione. Questa versione e' una **prova diagnostica**, non una correzione
hardware gia' confermata.

## Prova da eseguire

Estrarre tutto, mantenendo gli YAML accanto a `GOATS_DIAG3_RC33_STEP3D_FLICKER/`.
Compilare e installare **`goats_42_diag3_rc33_step3d_flicker.yaml`** in ESPHome USB.
Il factory incluso in `bin/firmware.factory.bin` e' compilato da questo YAML
ed e' l'immagine USB completa (offset 0x0 se richiesto). `firmware.ota.bin`
e' soltanto l'applicazione.

Dopo l'avvio la schermata alterna automaticamente:

- **A: FERMO — 10 SECONDI**: invia una sola immagine e poi non invia piu'
  comandi o dati LCD fino al cambio fase. Il pannello continua la scansione
  autonoma; non viene spento, resettato o messo in sleep.
- **B: INVIO — 10 SECONDI**: riscrive la stessa immagine ogni 125 ms nominali.
  Nessun orologio, contatore o campione GPS cambia i pixel di questa fase.
  Cambia soltanto il traffico SPI rispetto alla fase A; all'inizio della fase
  cambia anche il testo che la identifica.

Il ciclo si ripete da solo, senza tasti, fix GPS o circuito. Osservare almeno
un ciclo completo di 20 s e indicare **solo A, solo B oppure entrambe** per
lo sfarfallio; sono utili anche differenze di intensita'. Il cambio della
scritta fra le fasi e' previsto e non va confuso con lo sfarfallio persistente.
Durante la prova non premere BOOT e mantenere alimentazione e illuminazione
uguali. Il confronto a occhio e' utile: una videocamera puo' aggiungere battimenti.

BOOT breve apre la DIAG3 per controllare PVT e `C` crescente; il titolo indica
STEP3D LPM. La diagnostica aggiorna i valori ogni secondo e scrive immagini:
non va usata per valutare la fase senza traffico. Tornando col BOOT si riapre
il test, mentre il suo tempo continua a scorrere. Per la **Racing normale**
compilare/installare `goats_42_diag3_rc33_step3d_flicker_racing.yaml` incluso;
`_diag.yaml` parte direttamente in diagnostica. Questi due YAML sono validati,
il binario incluso e' quello del test A/B.

## Cosa permette di distinguere

- Se lo sfarfallio si riduce molto in A e compare in B, e' associato alle
  scritture/attivita' di invio o al carico elettrico che ne deriva. La prova
  da sola non distingue integrita' dei segnali, gestione RAM e alimentazione.
- Se rimane anche in A, l'invio continuo di immagini non e' necessario per
  farlo comparire: restano da verificare scansione autonoma, alimentazione e
  pilotaggio del pannello. Non dimostra da solo un guasto del display.

Il PDF YDP420H003-V3 p.7 rimanda al driver ST7306 e p.8 non specifica il tempo
di risposta ottico: non certifica una frequenza ottica massima per il tricolore.
[Specifiche pannello](https://admin.osptek.com/uploads/YDP_420_H003_V3_d136efd0a8.pdf).

## Impostazioni conservate

Tutti gli YAML inclusi usano `lcd_high_power: false`, `fast_display: true` e
`lcd_data_swap: true`: stessa sequenza LCD LPM 8 Hz nominali della STEP3B e
STEP3C con HPM disabilitato. Nessuna variazione di frequenza, tensioni, waveform,
VCOM, pixel packing o SPI a 4 MHz fra A e B. Il selettore HPM rimane disponibile
per compatibilita', ma non e' attivo e non va riabilitato in questo confronto.

GPS, UART/pin, configurazione M9N a 25 Hz, calcoli RC3.3, AUTO circuito, flash
interna, CSV e USB Manager restano quelli STEP3B. Il loop continua a leggere
GPS e gestire USB/store prima di ogni eventuale blocco SPI anche durante A.
La sola schermata di test non mostra contatori GPS per tenere fermi i pixel.
La Racing originale rimane invariata e selezionabile col suo YAML. L'opzione
`flicker_test` appartiene ai nuovi componenti STEP3D: non basta aggiungerla agli
YAML delle versioni precedenti senza sostituire anche la cartella componenti.

Nessuna SD o misura ADC batteria introdotta. BOOT 1,2..3s e >=3s conservano le
funzioni STEP3; non premere BOOT al reset. Per cataloghi/registrazione/download
vedere `ISTRUZIONI_MANAGER_STEP3.md`. La prova non modifica il formato dei dati.

Compilazione e prove software in `VERIFICA.md`; resta necessario il riscontro
fisico A/B. Non e' dichiarato risolto lo sfarfallio.
