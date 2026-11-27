# RC3.3 STEP3C HPM — prova contro lo sfarfallio

L'utente segnala sfarfallio sul pannello con STEP3B SMOOTH, anche nella Racing
con velocita' ferma a zero. La modalita' STEP3B e' LPM a 8 Hz nominali: il
ciclo rapido dell'invio SPI non aumenta la frequenza interna di scansione LCD.
Il filmato e il riscontro dell'utente documentano il difetto, ma non permettono
di identificarne con certezza la causa o misurare il refresh fisico.

Questa versione isola una prova sul pilotaggio: **HPM a 51 Hz nominali**,
selezionata una sola volta all'avvio. Non e' dichiarata una correzione gia'
collaudata sul pannello.

## Cosa cambia

Dopo sleep-out e l'attesa gia' presente viene configurato `OSCSET D8:80,E9`;
`FRCTRL B2:15` conserva HFRA=1; `HPM 38` sostituisce `LPM 39`.
La combinazione e' descritta dal datasheet ST7306 nelle sezioni 8.1.22 p.67,
8.2.3 p.77 e 8.2.23 p.93:
[ST7306 V0.1](https://admin.osptek.com/uploads/ST_7306_V0_1_c30c3541a3.pdf).

51 Hz e' la scansione interna nominale, **non il numero di immagini inviate**.
La Racing continua a richiedere un'immagine al massimo ogni 125 ms, come STEP3B.
Il flusso completo da 30000 byte mantiene i 13 blocchi, il ciclo rapido limitato
al trasferimento e la lettura GPS/USB/telemetria prima di ogni blocco.

Nessuna variazione di tensioni LCD, waveform B3/B4, VCOM, packing, font,
colori o geometria Racing. Il modo non viene cambiato all'aggiornamento o al
passaggio in diagnostica. Non vengono aggiunti blank/reset periodici.
Il consumo puo' aumentare rispetto a LPM; non e' stato misurato.

GPS a 25 Hz, UART/pin, calcoli RC3.3, AUTO circuito, flash interna, CSV e
protocollo USB Manager sono identici a STEP3B. SD e ADC batteria restano esclusi.
La precedente compensazione `lcd_data_swap` viene conservata.

## Installazione e confronto

1. Estrarre tutto e tenere gli YAML accanto a `GOATS_DIAG3_RC33_STEP3C_HPM/`.
2. Compilare/installare **`goats_42_diag3_rc33_step3c_hpm.yaml`** in ESPHome USB:
   parte nella Racing normale. Nessun nuovo collegamento necessario.
3. Da fermo osservare soprattutto lo zero della velocita', le scritte e le
   zone bianche: confrontare lo sfarfallio con STEP3B, a parita' di alimentazione.
   Il giudizio a occhio e' utile: la videocamera puo' introdurre battimenti.
4. BOOT breve apre la DIAG3, il cui titolo deve indicare **STEP3C HPM**.
   Controllare continuita' dei PVT e `C` crescente; durante la registrazione
   `PT` deve aumentare e `D` restare zero. La pagina diagnostica conserva
   l'aggiornamento dei valori ogni secondo, mentre il pannello resta in HPM.
5. Lo YAML `_test.yaml` mostra pattern e orologio UI in movimento senza fix o
   circuito, per confrontare anche la fluidita'. Dopo la prova tornare al main.
   `_diag.yaml` parte invece direttamente in diagnostica.

Per un confronto controllato, cambiare **solo `lcd_high_power: false`** e
ricompilare/installare: viene ripristinata esattamente la sequenza LCD LPM
STEP3B (nessun comando D8, comando 39 al posto di 38). Tenere `fast_display`
e `lcd_data_swap` ai valori inclusi. Nelle pagine di prova/diagnostica il titolo
indica LPM. Il ritorno alla vecchia versione completa resta disponibile.

Lo ZIP include `bin/firmware.factory.bin` compilato dal main: immagine USB
completa, offset 0x0 se richiesto. `firmware.ota.bin` e' solo l'applicazione.

## Funzioni conservate e limiti

BOOT breve Racing/DIAG3; 1,2..3s LAP TIME/DELTA; >=3s REC/STOP da fermo.
Non premere BOOT al reset. Per registrazione/cataloghi/download vedere
`ISTRUZIONI_MANAGER_STEP3.md`, incluso nello ZIP. Flash interna circa 43 minuti
totali a 25 Hz, massimo 64 sessioni incluse quelle cancellate.

Compilazione e prove software documentate in `VERIFICA.md`. Servono il collaudo
sulla scheda e il riscontro sul pannello per stabilire se HPM riduce lo
sfarfallio senza peggiorare contrasto, colori o stabilita' GPS. Se il difetto
rimane, il solo aumento della scansione non ne dimostra la causa; l'alimentazione
e il pilotaggio specifico del pannello richiederanno ulteriori verifiche.
