GOATS RT Manager V5.4.13.5 - BRAKE + CORNER SPEED ANALYSIS

Base: V5.4.13.4 REAL_SECTOR_COUNT_FIX.

NOVITA'
- Analisi frenate e curve unificata.
- Mantiene punto di frenata, delta prima/dopo, guadagno/perdita zona, durata e tempo zona.
- Aggiunge V prima freno per distinguere la velocita' all'inizio della staccata dalla velocita' curva.
- Aggiunge V INGRESSO curva nello stesso punto fisico per tutti i giri.
- Aggiunge V MINIMA curva.
- Aggiunge V USCITA curva nello stesso punto fisico per tutti i giri.
- Aggiunge DeltaV IN, DeltaV MIN e DeltaV OUT rispetto al giro di riferimento.
- Il riferimento resta automaticamente il giro piu' veloce tra quelli selezionati.
- Ingresso/uscita sono campionati attorno alla minima del giro di riferimento (circa -15 m / +25 m) usando interpolazione sul profilo distanza GPS.
- Tutte le altre funzioni della V5.4.13.4 restano invariate.

AVVIO
Usare AVVIA_GOATS_RT_MANAGER_V5.bat come nelle versioni precedenti.
