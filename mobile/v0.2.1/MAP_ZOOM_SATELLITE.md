# V0.1.4 - Mappa satellite e zoom traiettoria

Modifiche principali:

- modalità **SAT** con mappa satellitare Esri World Imagery sotto la traiettoria;
- pinch-to-zoom e pan nativi tramite Leaflet nella modalità satellitare;
- modalità **OFFLINE** mantenuta anche senza Internet;
- pinch-to-zoom e pan anche sulla traiettoria offline;
- pulsanti `-`, `+` e `FIT` nella vista offline;
- la mappa satellitare richiede connessione Internet; la traiettoria offline continua a funzionare senza rete.

La mappa SAT carica Leaflet 1.9.4 e le tessere Esri World Imagery via HTTPS. L'attribuzione Esri è mostrata sulla mappa.
