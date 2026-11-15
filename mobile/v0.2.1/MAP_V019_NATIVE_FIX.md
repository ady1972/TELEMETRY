# GOATS RT Manager Android V0.1.9 - Native Satellite Map

La V0.1.9 sostituisce completamente il viewer WebView della V0.1.8.

## Perche
Nella V0.1.8 i punti GPS venivano caricati correttamente (es. 653 punti) ma il riquadro mappa poteva rimanere completamente nero: il problema era nel layer WebView, non nei dati GPS.

## Nuovo rendering
- Jetpack Compose Canvas nativo.
- Esri World Imagery come tile satellitari HTTPS.
- Polilinee GPS disegnate direttamente dal Canvas sopra le tile.
- Nessuna dipendenza da Leaflet, CDN o JavaScript.
- Cache locale delle tile gia scaricate.
- Se le tile non arrivano, sfondo scuro + traiettoria continuano a essere visualizzati.

## Navigazione
- Auto FIT iniziale sull'intero circuito.
- Pinch-to-zoom.
- Pan con trascinamento.
- Pulsanti +, -, FIT.
- Giri separati e colorati quando il parser fornisce il numero giro.
