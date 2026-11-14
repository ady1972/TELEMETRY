# Guition: delta percepito meno preciso di RLCD

Segnalazione utente durante discussione prove RC1: delta oscillante anche
lontano dai settori. Nessuna misura hardware acquisita.

Confronto RC1: goats_laptimer.h è uguale fra RLCD e Guition nel motore,
inclusi matching sul punto più vicino del Best Lap, traccia ogni almeno
100 ms, filtro temporale di 1000 ms, massimo 3000 punti e soglia di 35 m.
Differenze del file: include dei tipi e accessor GUI compatibile Guition.
RC2 mantiene questi stessi motori (invarianti verificate dalla suite RC2).
Non modificato algoritmo o timing GNSS in base alla sola segnalazione.

Differenze confermate di presentazione:
- RLCD: riquadro principale con live_delta_seconds, salvo post-giro configurato;
  display configurato ogni 100 ms.
- Guition: lbl_delta aggiornato nel blocco grafico da 200 ms. Durante
  sector_hold_active il valore è sector_hold_delta_seconds (5 secondi),
  poi torna al valore lap_delta_seconds. La sola dicitura DELTA non distingue
  i due riferimenti. Ulteriori hold/post-giro sono gestiti separatamente.

Possibile fattore temporale da misurare, non causa dimostrata:
Guition accoda ogni NAV-PVT con millis() al momento della decodifica;
il drain passa sample.ms al motore. Anche RLCD usa millis() al consumo.
Il motore riceve iTOW ma non lo usa per il delta. Se più epoche sono lette
insieme dopo un blocco GUI/SD, i tempi software possono essere compressi.
Non cambiare la base tempi senza prova e autorizzazione sui vincoli GNSS.

Prossimo passo: distinguere sintomo (oscillazioni, ritardo o valore errato;
solo dopo i settori o anche sul resto del giro). Poi confrontare gli stessi
campioni e le latenze di ricezione/rendering; eventuali dati diagnostici
Guition includono max_decode_gap_ms, max_itow_step_ms, queue_overflow.
La correzione non è ancora individuata o validata sull'hardware.

## Riproduzione software e correzione locale Guition RC2

Confermata vulnerabilità del filtro: più campioni con lo stesso `sample.ms`
attivavano il ramo `dt <= 0`, che assegnava il valore spaziale non filtrato.
Non è un effetto della sostituzione del delta settore. Il motore RC1 comune
espone questo comportamento; l'effettiva frequenza sul Guition va misurata.

Replay sintetico con motore Guition RC1 reale, traiettoria circolare identica
ripetuta a 25 Hz, nessun rumore GPS:
- letture regolari ogni 40 ms: escursione circa 0,00158 s;
- decodifica raggruppata ogni 200 ms: escursione 0,2 s;
- decodifica raggruppata ogni 400 ms: escursione 0,4 s.
Sono condizioni artificiali, non misure del dispositivo.

Correzione limitata al filtro live in Guition RC2: a timestamp uguale conserva
il valore filtrato; al timestamp seguente applica il filtro con il tempo
trascorso. Inizializzazione e salto temporale all'indietro mantengono il
comportamento precedente. Non cambia epoche, ricevitore, tempi giro/settore,
formato CSV, matching spaziale, costante del filtro o motore RLCD.

La prova tests/rc2/test_guition_delta.cpp fallisce prima e passa dopo la modifica.
Controlla continuità del valore durante i gruppi e risposta a un rallentamento
reale del giro (da 60 a 66 secondi): il delta non viene congelato. Nella prova
identica raggruppata l'escursione dopo la correzione è zero. Questo non
certifica la precisione del delta reale e non elimina gli effetti del
campionamento spaziale o delle latenze sull'acquisizione.
Suite completa python tests/rc2/run.py PASS. Compilazione ESP32 e collaudo
hardware di questa revisione non eseguiti; nessun firmware caricato.
