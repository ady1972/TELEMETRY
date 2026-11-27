# RC3.3 STEP3F — separazione flash / USB Manager

Riscontri dell'utente: GPS_ONLY STEP3E non sfarfalla dopo il fix; con FULL
inizia uno sfarfallio leggero. Si separano ora i due servizi aggiunti dal
backend completo. Non viene ancora dichiarata individuata la causa o risolto
il difetto. Il carico elettrico cambia insieme ai servizi abilitati.

## Prima prova: CORE+FLASH, Manager escluso

Estrarre tutto mantenendo gli YAML accanto a `GOATS_DIAG3_RC33_STEP3F_BACKEND/`.
Compilare/installare **`goats_42_diag3_rc33_step3f_backend.yaml`** in ESPHome USB.
Parte in Info GPS, titolo **STEP3F - CORE+FLASH**:

- GNSS originale a 25 Hz e core RC3.3 attivi.
- Archivio/registrazione nella flash interna attivi.
- Driver e servizio USB Manager non vengono avviati o interrogati.
- `USB:0` e' atteso. `REC:0` significa nessuna sessione attiva.

Da fermo attendere il fix e verificare se compare lo sfarfallio. Non aprire
il Manager o avviare REC durante il primo confronto. Annotare anche `REC`,
`PT` e i nuovi contatori `W` / `ID`. Non serve cambiare collegamenti.

## Contatori visibili

`MEM ... W:... ID:...` mostra:

- **W**: chiamate di scrittura riuscite nel journal telemetria dall'avvio,
  non punti GPS, refresh LCD o letture dell'archivio.
- **ID**: commit NVS riusciti per prenotare blocchi di identificativi delle
  sessioni. Di norma una prenotazione all'avvio, non una per campione GPS.
  Non conta eventuali commit di cataloghi eseguiti dal Manager.

`PT` puo' mostrare i punti dell'ultima sessione gia' archiviata: un valore
maggiore di zero e stabile non dimostra che si stia registrando ora. Verificare
insieme `REC` e `W`. Dopo la scansione e la prenotazione ID, a fermo senza REC
ci si aspetta `W:0` anche dopo il fix, salvo comandi espliciti di scrittura.
`MEM SCANSIONE` all'avvio indica lettura dei record esistenti, non una
registrazione. I contatori sono in RAM e non aggiungono scritture persistenti.

## Altri confronti inclusi

| YAML | post_fix_mode | Telemetria flash | USB Manager |
|---|---|---|---|
| `goats_42_diag3_rc33_step3f_backend.yaml` | STORE_ONLY | Attiva | Escluso |
| `goats_42_diag3_rc33_step3f_backend_usb.yaml` | USB_ONLY | Esclusa | Attivo |
| `goats_42_diag3_rc33_step3f_backend_full.yaml` | FULL | Attiva | Attivo |

Tutti includono lo stesso core RC3.3 e partono nella stessa Info GPS; cambia
solo il profilo di avvio e la sua identificazione. Nomi, GPS, LPM, font,
packing, SPI e cadenze sono uguali. Nessuna commutazione durante una sessione.

Dopo la prima prova, `_usb.yaml` permette di confrontare **CORE+USB** senza
inizializzare/scansionare/scrivere il journal di telemetria o prenotare ID.
I cataloghi Manager restano disponibili e possono scrivere la propria NVS
su comando esplicito: per il primo confronto lasciare il Manager chiuso.
La registrazione, l'elenco e il download delle sessioni non sono disponibili
in USB_ONLY. `USB:1` significa driver pronto, non prova che un host o Manager
sia collegato. `_full.yaml` mantiene il sistema completo per il riferimento.

Se il difetto segue uno dei profili, si restringe il gruppo di attivita'
associato al fenomeno; non si prova da solo un errore del codice. Se si vede
soltanto quando entrambi sono attivi, si considera anche l'interazione/carico
combinato. Il risultato va confrontato con CORE_ONLY STEP3E alle stesse
condizioni, se quel profilo non e' gia' stato verificato.

## Funzioni e installazione

BOOT breve apre il test A/B STEP3D (10 s senza ulteriori scritture LCD, poi
10 s di reinvio identico); un altro BOOT torna in Info GPS. Le regole di
questa prova restano quelle documentate nelle versioni precedenti.
BOOT >=3s REC/STOP e' attivo in STORE_ONLY e FULL; e' escluso in USB_ONLY.
I profili rimangono selezionabili anche per GPS_ONLY/CORE_ONLY tramite schema.

`goats_42_diag3_rc33_step3f_backend_racing.yaml` e' la Racing normale FULL.
Renderer/font/geometria, calcoli RC3.3, cataloghi, formato dei record/CSV e
protocollo Manager non vengono cambiati. Per la Racing senza Manager si puo'
impostare `post_fix_mode: STORE_ONLY` in questo YAML e ricompilare.
Istruzioni Manager incluse in `ISTRUZIONI_MANAGER_STEP3.md`, applicabili ai
servizi attivi nel profilo scelto. Nessuna SD o misura batteria introdotta.

`bin/firmware.factory.bin` e' compilato dal primo YAML, **CORE+FLASH / Info GPS**:
immagine USB completa, offset 0x0 se richiesto. `firmware.ota.bin` e' solo app.
Gli altri tre YAML sono validati e compilabili, senza binari separati inclusi.
Serve la cartella componenti STEP3F: aggiungere il nuovo valore soltanto a uno
YAML vecchio non aggiorna il codice.

LPM 8 Hz nominali, SPI 4 MHz, XDE e tensioni/waveform restano STEP3E. HPM non
abilitato. Nessuna cancellazione/formattazione automatica dei dati esistenti.
GPS/pin/baud/protocollo/configurazione e core rimangono invariati; il backend
ora accetta due flag all'avvio, entrambi veri per il comportamento FULL.

Compilazione e verifiche in `VERIFICA.md`; serve il riscontro sul display.
