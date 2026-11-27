# RC3.3 STEP3E — isolamento delle attivita' dopo il fix

L'utente riferisce che lo sfarfallio compare **dopo il fix GPS**; prima non
compare. In STEP3D persiste sia in A (nessuna scrittura LCD dopo l'immagine)
sia in B (riscrittura identica). HPM STEP3C ha peggiorato i colori; tornando
LPM i caratteri sono tornati leggibili. Questi riscontri non identificano
ancora la causa e non costituiscono una conferma di guasto hardware.

Si lavora ora sulle attivita' software successive al fix, mantenendo invariati
ricevitore, baud, pin, protocollo, frequenza 25 Hz e pilotaggio LCD LPM.
Non e' necessario cambiare collegamenti per eseguire questa prova.

## Prima prova: GPS ONLY

1. Estrarre tutto e tenere gli YAML accanto a `GOATS_DIAG3_RC33_STEP3E_POSTFIX/`.
2. Compilare/installare **`goats_42_diag3_rc33_step3e_postfix.yaml`** con ESPHome USB.
3. La pagina iniziale deve indicare **STEP3E - GPS ONLY**. Attendere un fix
   valido, visibile sulla riga `DATI OK - FIX 3D` o sul tipo di fix disponibile.
   Controllare anche PVT circa 25 Hz, satelliti, HDOP e continuita' fix.
4. Verificare se lo sfarfallio compare prima/dopo il fix. `CORE:OFF C:0` e
   `FLASH E USB MANAGER ESCLUSI DAL TEST` confermano il profilo scelto.
5. BOOT breve apre la stessa prova A/B STEP3D: 10 s di immagine ferma senza
   altre scritture LCD, poi 10 s di reinvio della stessa immagine ogni 125 ms.
   Un altro BOOT breve torna a Info GPS. Non confondere il cambio di scritta
   fra le fasi con lo sfarfallio persistente.

**GPS ONLY mantiene la ricezione e decodifica originali**, incluso il fix reale;
non maschera i dati del ricevitore. Non collega l'osservatore al core RC3.3 e
non avvia store/registrazione/Manager. Il catalogo esistente viene ancora letto
in NVS all'avvio, come negli altri profili; non e' cancellato o riscritto.
Non viene avviata l'applicazione RC3.3 dopo il fix in questo profilo.

## Confronti gia' pronti nello ZIP

Il profilo si seleziona all'avvio, senza passaggi automatici durante una sessione.
Tra i tre confronti cambiano solo `post_fix_mode`, nome del nodo e identificazione
visiva; ricevitore, SPI, LPM, font, schermata iniziale e cadenze restano uguali.

| YAML | post_fix_mode | Core/circuito | Flash telemetria e Manager |
|---|---|---|---|
| `goats_42_diag3_rc33_step3e_postfix.yaml` | GPS_ONLY | Escluso | Esclusi |
| `goats_42_diag3_rc33_step3e_postfix_core.yaml` | CORE_ONLY | Attivo | Esclusi |
| `goats_42_diag3_rc33_step3e_postfix_full.yaml` | FULL | Attivo | Attivi, come STEP3D |

Partire solo da GPS ONLY. Se non sfarfalla dopo il fix, installare CORE_ONLY e
ripetere da fermo nelle stesse condizioni. Se resta stabile, confrontare FULL.
Se sfarfalla gia' in GPS ONLY, core, riconoscimento circuito e registrazione non
sono necessari per riprodurre il difetto; rimangono ricezione/decodifica GNSS,
pilotaggio e alimentazione da verificare. Se cambia passando fra i profili,
questo individua un gruppo di attivita' associato al fenomeno, non dimostra da
solo un errore del software: cambia anche il carico elettrico.

In CORE_ONLY il contatore `C` deve crescere e i circuiti vengono riconosciuti
con le regole RC3.3; `C` conta anche PVT distinti senza fix. Il solo fix da fermo
non avvia un giro. In FULL il Manager puo' accedere ai cataloghi/sessioni e
la registrazione richiede l'avvio di una sessione, non il semplice arrivo del fix.
Il comando REC/STOP di BOOT >=3s e' abilitato solo in FULL; nei due profili
ridotti non avvia una registrazione. Il test e' da banco, non per registrare
una sessione in pista con funzionalita' disabilitate.

Per la **Racing normale completa** e' incluso
`goats_42_diag3_rc33_step3e_postfix_racing.yaml`: FULL e `flicker_test: false`.
Il renderer originale RC3.3, font, calcoli, CSV, cataloghi e protocollo USB non
sono stati riscritti. In FULL le funzioni rimangono quelle STEP3D; istruzioni
Manager in `ISTRUZIONI_MANAGER_STEP3.md`. Non e' una correzione dello sfarfallio.

## Analisi del codice

Non viene inviato un comando di cambio frequenza o modalita' LCD al fix. La
ricezione NAV-PVT avviene gia' prima del fix. Con un fix valido il core abilita
il riconoscimento AUTO (ricerca nel catalogo e tre campioni validi consecutivi),
il confronto con traguardo/settori e il percorso dati di una sessione attiva.
Le scritture flash STEP3 sono servite dal tick esterno al callback PVT; lo
store non registra semplicemente perche' e' arrivato il primo fix.
La STEP3E separa questi percorsi senza modificare il parser M9N.

## Build e limiti

`bin/firmware.factory.bin` e' compilato dal primo YAML, **GPS ONLY con Info GPS**:
immagine USB completa, offset 0x0 se richiesto. `firmware.ota.bin` e' soltanto
l'applicazione. Gli altri tre YAML sono validati e compilabili, senza binari
separati inclusi. Il nuovo parametro richiede i componenti STEP3E: aggiungerlo
soltanto a uno YAML vecchio non aggiorna il firmware.

Tutti i profili inclusi hanno `lcd_high_power: false`, `fast_display: true` e
`lcd_data_swap: true`: LPM 8 Hz nominali STEP3B/STEP3D, SPI 4 MHz e stessi
voltaggi/waveform. Nessuna SD, ADC batteria, Wi-Fi/OTA o MSC aggiunti. La scansione
interna LCD continua anche in A. La diagnostica aggiorna i valori ogni secondo.

Compilazione e test software in `VERIFICA.md`. Serve il riscontro fisico dopo
il fix; non viene dichiarato risolto lo sfarfallio.
