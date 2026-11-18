GOATS RT Manager Android V0.1.8

Correzione mappa/traiettorie:
- eliminata la dipendenza runtime da Leaflet CDN, che poteva lasciare il WebView vuoto;
- viewer satellitare self-contained;
- Esri World Imagery usato solo per le tile;
- polilinee SVG indipendenti dalle tile, quindi visibili anche senza Internet;
- ogni giro e' una polilinea distinta e colorata;
- pinch, pan, +, -, FIT;
- fallback OFFLINE Compose Canvas sempre disponibile.

AssistNow:
- voce rimossa dalla navigazione;
- schermata rimossa;
- API AssistNow rimosse dal bridge Kotlin esposto all'interfaccia.
