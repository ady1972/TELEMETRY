# RC3.3 STEP3G — meno calcoli ripetuti nel core

Riscontri: GPS_ONLY stabile dopo il fix; CORE_ONLY STEP3F sfarfalla meno ma
sfarfalla; anche STORE_ONLY e USB_ONLY riproducono il difetto. Non e' quindi
attribuibile soltanto a un servizio del backend. TE e' confermato scollegato:
il datasheet ST7306 p.31 consente di lasciarlo aperto quando non usato. Questa
versione mantiene il cablaggio e non aggiunge la gestione TE.

Si riduce ora un lavoro ripetuto del core: i coseni degli stessi argomenti
vengono ricalcolati nel riconoscimento AUTO, nelle proiezioni delle linee e
nelle ricerche delle tracce di riferimento. Questa e' un'ottimizzazione con
confronto numerico, **non una correzione dello sfarfallio gia' confermata**.

## Prima prova

Estrarre tutto tenendo gli YAML accanto a `GOATS_DIAG3_RC33_STEP3G_CORELOAD/`.
Compilare/installare **`goats_42_diag3_rc33_step3g_coreload.yaml`** in ESPHome USB.
Parte in Info GPS, titolo **STEP3G - FULL CACHE**. Core, flash e Manager sono
attivi; ricevitore, LCD LPM, font e cadenze sono quelli della STEP3F.

Da fermo attendere il fix e verificare se cambia lo sfarfallio. Annotare:

- **CORE media/massimo us**: tempo di elaborazione del consumatore PVT RC3.3
  nella finestra di circa un secondo appena completata. Non e' il carico CPU
  totale, non comprende il tick esterno flash/USB, ne' misura il refresh LCD.
  Rimane zero finche' la finestra non e' completata; con flusso interrotto
  conserva l'ultima misura, mentre la pagina mostra lo stato PVT scaduto.
- **COS ...%**: percentuale delle richieste di coseno soddisfatte riutilizzando
  un risultato identico dall'avvio. Non e' una percentuale di tempo CPU risparmiato.
  Con catalogo vuoto o nessun calcolo geometrico puo' restare zero.
- **UI ...ms**, **REC**, **W** e **ID** mantengono i significati STEP3F.

## Confronto gia' pronto

`goats_42_diag3_rc33_step3g_coreload_reference.yaml` usa FULL con
`core_cache: false`: titolo **STEP3G - FULL REF**, stessi parametri e stessa
strumentazione, ma ogni coseno viene calcolato come prima. Installare e
confrontare alle stesse condizioni, senza aprire il Manager o avviare REC
nel primo test. Non servono nuovi collegamenti e TE resta scollegato.

Sono inclusi anche `_core.yaml` (CORE_ONLY con cache) e `_racing.yaml` (FULL
con cache, Racing normale). I profili di isolamento STEP3F rimangono supportati.
Il nuovo parametro richiede i componenti STEP3G: aggiungerlo soltanto a un
vecchio YAML non aggiorna il codice.

## Cosa cambia nel calcolo

La cache contiene solo risultati `double` di `std::cos` per argomenti con la
stessa rappresentazione a 64 bit. Se cambia un solo bit dell'argomento viene
ricalcolato il coseno. Non ci sono arrotondamenti, quantizzazioni, polinomi
approssimati, riduzioni dei campioni o cambi delle soglie/geometrie.

Sono usate 50 voci indicizzate per i centri dei circuiti e una voce per
ciascuno dei due percorsi di proiezione. Se il catalogo viene modificato o
riordinato, il confronto dell'argomento impedisce il riuso di valori diversi;
oltre 50 indici si usa direttamente il calcolo originale. La memoria e' fissa,
senza allocazioni nella cache: RAM statica aggiuntiva circa 1,3 kB.

L'AUTO continua a esaminare il catalogo su ogni campione valido e conserva le
tre conferme consecutive. Giri/settori, matching delle tracce, delta, medie e
regole di sessione non vengono cambiati. Il parser/configuratore GNSS resta
identico: stesso unico lettore, pin, baud, UBX NAV-PVT e frequenza 25 Hz.
L'osservatore misura solo il tempo di elaborazione con micros per la diagnostica;
non cambia i timestamp usati dal laptimer.

## Risultati software e limiti

Replay contro la STEP3F originale e contro STEP3G con cache disabilitata:
stati osservabili del core, giri/settori/delta e CSV risultano identici byte
per byte nei tre scenari provati. Nel replay con piu' giri le valutazioni cos
passano da 1039503 a 9896, su altrettante richieste; nell'AUTO da fermo da
64933 a 449. Sono conteggi di chiamate software, non misure di accelerazione
sull'ESP32 o di riduzione del consumo/sfarfallio. Dettagli in `VERIFICA.md`.

Il firmware include il sistema FULL: store/CSV/protocollo Manager non cambiano.
Istruzioni in `ISTRUZIONI_MANAGER_STEP3.md`. HPM e' escluso, SPI 4 MHz e LPM
8 Hz nominali invariati; nessuna SD, misura batteria, Wi-Fi/OTA o MSC aggiunti.
BOOT breve Info GPS/test A-B; BOOT lungo conserva REC/STOP nei profili con store.

`bin/firmware.factory.bin` e' compilato dal primo YAML FULL CACHE / Info GPS:
immagine USB completa, offset 0x0 se richiesto. `firmware.ota.bin` e' solo app.
Gli altri tre YAML sono validati, senza binari separati inclusi.
Serve il riscontro reale sul display: il ruolo del carico elettrico rimane da
verificare e l'ottimizzazione non prova quale sia la causa dello sfarfallio.
