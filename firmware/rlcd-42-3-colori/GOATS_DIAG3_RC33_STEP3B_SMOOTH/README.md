# RC3.3 STEP3B SMOOTH — velocita' e cronometro

La STEP3A invia immagini aggiornate ma configura il pannello in LPM a 1 Hz
(FRCTRL B2=0x12). Inoltre la trasmissione di 30000 byte e' divisa in 13
iterazioni, ognuna soggetta alla pausa standard ESPHome di 16 ms. Questi due
limiti spiegano perche' il dato sullo schermo puo' arrivare a scatti anche se
il GPS produce NAV-PVT a 25 Hz.

## Modifica

- FRCTRL passa a **0x15**, cioe' LFRA=5: LPM **8 Hz nominali**. La modalita'
  resta LPM; le tensioni LCD, i waveform e i clock SPI non cambiano.
  Riferimento: [ST7306, sezione 8.2.3 p.77](https://admin.osptek.com/uploads/ST_7306_V0_1_c30c3541a3.pdf).
- Il componente richiede il ciclo rapido nativo ESPHome soltanto durante
  l'invio di un'immagine. In questo modo spariscono le attese da 16 ms tra
  i blocchi. A immagine terminata, annullata o invariata rilascia la propria
  richiesta; non modifica l'intervallo globale dell'applicazione.
- La Racing compone una nuova immagine al massimo ogni **125 ms**, coerente
  con il pannello a 8 Hz. Sono sempre inviati 13 blocchi fino a 2400 byte,
  con lettura GPS, stabilita', telemetria/Manager e input prima di ogni blocco.
  A 4 MHz il solo payload richiede 60 ms totali, fino a 4,8 ms per blocco.
- La diagnostica aggiunge `UI ...ms`: durata software dell'ultimo invio
  completo Racing/test, comprese le pause fra blocchi. Non misura il refresh
  fisico del pannello. E' 0 se non e' ancora stata inviata una pagina Racing/test.

Non si generano velocita' interpolate e non cambiano i calcoli di giro:
GPS, core RC3.3, cataloghi, memorizzazione e USB Manager sono identici.
La velocita' conserva i valori interi e la soglia di 3 km/h della RC3.3.
Le misure restano basate sui NAV-PVT distinti a 25 Hz. Solo la visualizzazione
ha il nuovo ritmo; la precisione dei tempi registrati non viene ridotta a 8 Hz.

## Installazione e prova

Estrarre tutto, tenendo i tre YAML accanto a `GOATS_DIAG3_RC33_STEP3B_SMOOTH/`.

1. Compilare/installare `goats_42_diag3_rc33_step3b_smooth.yaml` in ESPHome USB:
   parte nella Racing normale. Il factory USB incluso e' compilato da questo
   YAML: `bin/firmware.factory.bin`, immagine completa (offset 0x0 se richiesto).
   `firmware.ota.bin` e' solo l'applicazione, non l'immagine completa.
2. Valutare la velocita' nella **Racing**. La DIAG3 resta intenzionalmente alla
   cadenza di 1 s del riferimento per i suoi valori diagnostici.
3. Per una verifica da fermo compilare `_test.yaml`: visualizza linee/cifre e
   un **OROLOGIO DI PROVA** che avanza anche senza fix o circuito. E' il tempo
   UI di prova, non un giro e non un campione registrato. GPS e Manager restano
   attivi sullo sfondo. Dopo il test tornare allo YAML principale.
4. Da Racing/test BOOT breve passa a DIAG3: controllare PVT stabile, C crescente
   e, durante una vera registrazione, PT crescente e D=0. `UI ...ms` permette
   di osservare il tempo di invio; lo YAML `_diag.yaml` parte direttamente in
   diagnostica ma non esegue prima un trasferimento Racing/test.

BOOT 1,2..3 s e REC/STOP >=3 s conservano le funzioni STEP3. Non premere BOOT
all'accensione. Nessun tasto esterno o collegamento aggiuntivo necessario.

La base e' STEP3A; `lcd_data_swap` rimane configurabile come nella versione
precedente. Questa versione non dichiara risolto il precedente problema di
allineamento sul pannello: la sua conferma hardware e' ancora necessaria.
Font, dimensioni, spaziatura e layout Racing sono invariati.

`fast_display: true` abilita il profilo nuovo. Per confronto A/B, false
ripristina LPM 1 Hz, cadenza richiesta di 100 ms e assenza della richiesta
rapida, come STEP3A. Cambiare lo YAML richiede ricompilazione/installazione.

## Limiti e funzioni conservate

L'obiettivo fisico e' 8 aggiornamenti/s, non 25 o 60. L'effettiva fluidita'
dipende da pannello, disegno, carico e tempi flash; serve il collaudo. Il ciclo
piu' rapido e il refresh LCD piu' frequente possono aumentare l'assorbimento.
Non ci sono commutazioni periodiche di modalita', blank/reset del pannello o
nuove finestre parziali: il flusso RAMWR completo e' quello STEP2A/STEP3.

Telemetria nella flash interna, AUTO circuito e comandi Manager rimangono
STEP3. Capacita' circa 43 minuti totali a 25Hz e 64 sessioni incluse quelle
cancellate; nessuna sovrascrittura automatica. SD, ADC batteria, Wi-Fi/OTA e
TinyUSB/MSC restano esclusi. Vedere `ISTRUZIONI_MANAGER_STEP3.md` incluso per
la procedura completa di cataloghi, registrazione libera e download CSV.

Compilazione e prove software passate; nuovi tempi effettivi di invio,
continuita' GPS e risposta LCD devono essere verificati sulla scheda.
