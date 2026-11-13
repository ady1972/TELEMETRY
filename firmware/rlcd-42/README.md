# GOATS RLCD 4.2"

## RC2 per il prossimo collaudo

Ingresso ESPHome: `goats_rlcd_rc2.yaml`, affiancato alla cartella `GOATS_RLCD_RC2`.
[Correzioni, formato TA06NO01.CSV e piano di prova](GOATS_RLCD_RC2/RC2.md).
RC2 applica orario locale, nomi con giorno e data di registrazione nei dettagli.
Collaudo hardware previsto dall'utente nella settimana 16–22 novembre 2026.
Le note RC1 sotto descrivono la precedente base, conservata invariata.


Firmware ESP32-S3 con display RLCD. Motore di cronometraggio GNSS 25 Hz.

## RC1 corrente

[GOATS RLCD RC1](GOATS_RLCD_RC1/RC1.md), basata su **TEST26**.
Ingresso ESPHome: `goats_rlcd_rc1.yaml`, affiancato alla cartella
`GOATS_RLCD_RC1`. L'utente conferma tempi e funzionamento allineati
con Guition V1.0.22 nell'ultimo test comparativo, comunicato il 13/11/2026.
La versione TEST28 non è la base di questa promozione.

Orario indietro di un'ora, nomi file e data esatta di registrazione nei dettagli
restano nella [roadmap](../../ROADMAP.md).

## Versioni conservate

| Versione | Configurazione ESPHome | Stato |
| --- | --- | --- |
| TEST26 | `goats_rlcd_mg902_r12_1_sd_r14_2_test_26.yaml` | Riferimento del repository; sorgenti invariati. |
| TEST27 | `goats_rlcd_mg902_r12_1_sd_r14_2_test_27.yaml` | Sperimentale: worker CSV giri sul Core 0 e GPIO2 pull-up. Segnalati riavvii al traguardo; causa non confermata. |
| TEST28 | `goats_rlcd_mg902_r12_1_sd_r14_2_test_28.yaml` | Ripristino della logica TEST26 con GPIO2 pull-up, senza worker TEST27. Non ancora provata sul dispositivo dall’utente. |

TEST27 e TEST28 sono importate dagli ZIP forniti dall’utente, senza modifiche ai file originali. Ogni versione mantiene la propria cartella e il proprio LEGGIMI. Nessuna delle due è certificata stabile: questa importazione non include compilazione ESPHome né test hardware.

Le configurazioni nella radice di questa cartella includono il rispettivo YAML completo nella sottocartella della versione. Conservare insieme tutti i file di ciascun pacchetto.

## Verifica storica TEST28

Provare TEST28 per più giri consecutivi, verificando assenza di riavvii e presenza dei giri e della traccia salvata. Se il reset si ripete, acquisire il log seriale con motivo del reset e backtrace prima di attribuirlo alla gestione dual-core.
