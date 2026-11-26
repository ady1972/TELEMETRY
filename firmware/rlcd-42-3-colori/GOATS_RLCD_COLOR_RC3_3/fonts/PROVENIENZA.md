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

Menu e avvisi ESPHome leggono il TTF locale e usano `bpp: 1`.
Per Racing, `generate_native.py` usa Pillow/FreeType, layout BASIC e maschere
monocromatiche alla dimensione finale; ogni pixel del glifo resta un pixel
del pannello. Coordinate, avanzamento e limiti reali dell'inchiostro sono
conservati separatamente. Non vengono applicati resize, correzioni morfologiche,
dilatazioni, antialiasing o dithering temporale.

Sono incluse dimensioni 13–95 px. I caratteri latini dei nomi circuiti sono
disponibili nei font piccoli; un codepoint non disponibile diventa un `?`.
La sequenza UTF-8 viene consumata per intero, evitando tagli a metà carattere.

Per rigenerare, con Pillow installato:

```sh
python GOATS_RLCD_COLOR_RC3_3/fonts/generate_native.py
```

La riproducibilità byte per byte del raster richiede la stessa versione
di Pillow/FreeType. La compilazione ESPHome usa il raster già incluso e
non richiede questo passaggio.
