GOATS RT Manager V5.4.10.4 - CSV FIX

Correzioni:
- lettura corretta della riga reale del firmware:
  # mode=...,date=...,time=...,track=...
- data e ora vengono prese dal CSV e non dal timestamp FAT del file;
- nome circuito reale viene preso da track=;
- frequenza CSV impostata a 25 Hz;
- apertura pagina Analisi forza il caricamento della sessione selezionata;
- risolto il caso in cui mappa e grafico restavano entrambi bianchi pur
  avendo punti correttamente importati.

IMPORTANTE:
Le sessioni CSV già importate con la versione precedente mantengono i vecchi
metadati nel database. Eliminarle dal Manager e reimportare gli stessi CSV
con questa build.

Versione Manager invariata: V5.4.10.4.
