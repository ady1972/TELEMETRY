GOATS RT Manager V5.4.10.4 - CURSORE GRAFICO/MAPPA

Correzione della funzione richiesta in Analisi.

Il precedente tentativo usava QLineSeries.hovered: quel segnale richiede che
il puntatore colpisca praticamente il pixel della linea e in uso reale poteva
sembrare non funzionante.

Nuovo comportamento:
- l'intera area del grafico Velocità/tempo segue il mouse;
- quando il puntatore è entro circa 32 px dalla curva, viene individuato il
  campione temporale più vicino;
- sul grafico appare una linea verticale tratteggiata come cursore;
- contemporaneamente sulla mappa appare un marker sul punto GPS esatto;
- la mappa mostra anche tempo e velocità;
- con confronto A/B viene scelta automaticamente la curva più vicina al mouse;
- uscendo dalla curva il marker e il cursore scompaiono.

Mantenute tutte le funzioni precedenti, inclusa Importa Sessioni.
Versione invariata: V5.4.10.4.
