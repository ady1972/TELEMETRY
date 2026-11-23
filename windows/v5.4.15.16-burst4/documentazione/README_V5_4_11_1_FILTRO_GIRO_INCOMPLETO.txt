GOATS RT Manager V5.4.11.2 - FILTRO GIRO INCOMPLETO

Modifiche:
- I CSV SD considerano completo un giro solo quando compare l'inizio del giro successivo.
- Lo spezzone finale presente dopo l'ultimo passaggio sul traguardo viene sempre escluso dall'analisi, indipendentemente dalla sua durata.
- Il tempo giro dei CSV viene calcolato tra l'inizio di due giri consecutivi, evitando di perdere l'intervallo tra l'ultimo fix del giro e il primo fix successivo.
- Il filtro precedente dei giri troppo corti (<80% del Giro 2) resta attivo dopo il filtro di completezza.
- Numero giri, Best Lap, velocità massima e velocità media del riepilogo Analisi sono calcolati solo sui giri completi e validi.
- La barra informazioni segnala esplicitamente quando è stato ignorato lo spezzone finale.

Nota: i punti GPS dello spezzone restano nel database/traccia originale; vengono soltanto esclusi dalle statistiche e dal confronto giri.
