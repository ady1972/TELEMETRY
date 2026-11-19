# Verifica Manager Windows V5.4.15.5

I test verificano i controlli Qt e il JavaScript della mappa generato dal
Manager usando esclusivamente telemetria sintetica. Nessuna porta seriale,
credenziale o registrazione personale viene utilizzata.

Installazione ed esecuzione dalla root, preferibilmente in un ambiente virtuale:

```sh
python -m pip install -r windows/v5.4.15.5-burst4/requirements.txt playwright
python -m playwright install chromium
python tests/windows_fullscreen/test_fullscreen.py
```

Sono inclusi sei test, con sottocasi per tutte le otto combinazioni delle
caselle e le modalità iniziali Frenata/Velocità curva. Verificano anche
riapertura della finestra, caricamento web ritardato, zoom/posizione stabili,
replay durante il cambio visibilità, sessione vuota e rimozione del riquadro
descrittivo nella vista normale e nel fullscreen.

La libreria Leaflet 1.9.4 usata anche dall'app viene caricata dal CDN una volta
per la verifica, poi servita localmente al browser di test; tutte le altre
richieste web del browser vengono bloccate. Per usare una copia già scaricata,
impostare `GOATS_LEAFLET_DIR` alla cartella contenente `leaflet.js` e `leaflet.css`.
È possibile indicare un Chromium installato con `GOATS_CHROMIUM`.

Le prove automatiche non sostituiscono il collaudo su Windows con archivi e
hardware reali.

## Velocità estese — V5.4.15.10

Con `GOATS_WINDOWS_VERSION=5.4.15.10` la suite verifica anche eredità della
velocità 5x nel fullscreen, avvio a 10x, ciclo completo del tasto S e cambio
velocità durante Play. Un orologio controllato in Chromium verifica i rapporti
0,5/1/2/5/10x e il cambio da 1x a 10x senza salto del tempo accumulato.
I test sono otto; quello dei nuovi controlli è saltato nelle versioni precedenti.
