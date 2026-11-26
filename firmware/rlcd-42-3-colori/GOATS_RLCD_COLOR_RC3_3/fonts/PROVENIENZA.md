# Font e glifi locali

Famiglia: **Roboto Condensed**, peso 700, progetto Google Fonts.
Licenza: SIL Open Font License 1.1, testo originale in `OFL.txt`.

File sorgente variabile acquisito il 26 novembre 2026:

https://github.com/google/fonts/blob/main/ofl/robotocondensed/RobotoCondensed%5Bwght%5D.ttf

SHA-256 del file variabile:
`dace262afcee68a5276f200d8026c57221735c0118ab5fda8c2c0d3dc409a8d0`.

`RobotoCondensed-Bold.ttf` è l'istanza statica dell'asse `wght=700`, ottenuta
con `fontTools.varLib.instancer.instantiateVariableFont` senza modificare
i contorni dei glifi. SHA-256 del TTF locale:
`288e36c14ddb22beb83317e7089b497586e1c190abdc7cb46b81f4c4cafc3a7c`.

Tutte le schermate usano il motore `Font` di ESPHome con `bpp: 1`.
Le dimensioni (13, 16, 20, 28, 36, 42, 44, 52, 60, 64, 72, 78, 82 px) e la
selezione del font in funzione del riquadro sono quelle della RLCD RC3.3.
Il font viene rasterizzato da ESPHome alla dimensione finale: non si applicano
resize, dilatazioni, correzioni dei tratti o dithering temporale.

Il TTF locale evita il download dei font Google durante la compilazione.
Non è necessario un generatore separato dei glifi. Nel test host del layout
si usano `glyph_to_glyphinfo` e la classe C++ `Font` della stessa versione
ESPHome per produrre le anteprime e confrontare i due renderer.
