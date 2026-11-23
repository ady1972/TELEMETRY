# GOATS Guition 4.3"

## RC3.2 USB — Indicatore batteria

Variante GUITION per il collaudo via USB dal [Manager presente su `main`](../../windows/v5.4.15.18-burst4/).
[Configurazione ESPHome](goats_guition_43_rc3_1.yaml) · [Pacchetto applicativo](usb/).
L’icona arrotonda il
riempimento al pixel più vicino e mostra un calo solo dopo tre secondi sotto il
livello visualizzato. Per il collaudo, verificare il riempimento a fine carica,
poi osservare l’icona durante l’uso a batteria e dopo lo scollegamento USB.
La schermata «BATTERIA CARICA» ha un rilevamento separato, basato sulla tensione
misurata durante la ricarica USB.

## RC3.1 — Candidato da collaudare

Per ESPHome, tenere lo YAML accanto alla cartella con i componenti e le risorse.
[Configurazione ESPHome RC3.1](https://github.com/ady1972/TELEMETRY/blob/4c249067e2f524bc63283dae62bd6abdda6cabd0/firmware/guition-43/goats_guition_43_rc3_1.yaml) · [File del firmware RC3.1](https://github.com/ady1972/TELEMETRY/tree/4c249067e2f524bc63283dae62bd6abdda6cabd0/firmware/guition-43/goats_guition_43_rc3_1).

Per aggiornare via USB dal Manager Windows, usare il pacchetto del proprio modello.
[Scarica il pacchetto ZIP](https://raw.githubusercontent.com/ady1972/TELEMETRY/rc3-usb-packages/GOATS-GUITION_43-RC3.1.zip) · [Guida e verifiche](../../docs/RC3_USB.md).

## RC2 — Versione precedente

Ingresso ESPHome: `goats_guition_43_rc2.yaml`, affiancato alla cartella `goats_guition_43_rc2`.
[Correzioni, formato TA06NO01.CSV e piano di prova](goats_guition_43_rc2/RC2.md).
RC2 applica orario locale, nomi con giorno e data di registrazione nei dettagli.
Collaudo hardware previsto dall'utente nella settimana 16–22 novembre 2026.
Le note RC1 sotto descrivono la precedente base, conservata invariata.


Firmware ESP32-S3 per display Guition 480x272.

Versione precedente: **V1.0.22 RC1 RLCD26 USB**, base V1.0.22.
Ingresso ESPHome: `goats_guition_43_rc1.yaml`, affiancato alla cartella
`goats_guition_43_rc1`. [Note RC1](goats_guition_43_rc1/RC1.md).

L'utente conferma tempi e funzionamento allineati con RLCD TEST26
nell'ultimo test comparativo, comunicato il 13/11/2026. La promozione aggiorna le
etichette di versione; logiche e dati rimangono quelli della base provata.

Versioni precedenti conservate: V1.0.20, V1.0.21 diagnostica e V1.0.22.
Versione stabile di riferimento storico: V1.0.15.

[Roadmap comune](../../ROADMAP.md): orario RLCD, nomi dei file e data
esatta di registrazione nei dettagli. Correzioni non incluse in RC1.

Compilazione tramite ESPHome. Wi-Fi e OTA esclusi.
