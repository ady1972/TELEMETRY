# GOATS RLCD 4.2"

Firmware ESP32-S3 con display RLCD. Motore di cronometraggio GNSS 25 Hz.

## Versioni conservate

| Versione | Configurazione ESPHome | Stato |
| --- | --- | --- |
| TEST26 | `goats_rlcd_mg902_r12_1_sd_r14_2_test_26.yaml` | Riferimento del repository; sorgenti invariati. |
| TEST27 | `goats_rlcd_mg902_r12_1_sd_r14_2_test_27.yaml` | Sperimentale: worker CSV giri sul Core 0 e GPIO2 pull-up. Segnalati riavvii al traguardo; causa non confermata. |
| TEST28 | `goats_rlcd_mg902_r12_1_sd_r14_2_test_28.yaml` | Ripristino della logica TEST26 con GPIO2 pull-up, senza worker TEST27. Non ancora provata sul dispositivo dall’utente. |

TEST27 e TEST28 sono importate dagli ZIP forniti dall’utente, senza modifiche ai file originali. Ogni versione mantiene la propria cartella e il proprio LEGGIMI. Nessuna delle due è certificata stabile: questa importazione non include compilazione ESPHome né test hardware.

Le configurazioni nella radice di questa cartella includono il rispettivo YAML completo nella sottocartella della versione. Conservare insieme tutti i file di ciascun pacchetto.

## Prossima verifica

Provare TEST28 per più giri consecutivi, verificando assenza di riavvii e presenza dei giri e della traccia salvata. Se il reset si ripete, acquisire il log seriale con motivo del reset e backtrace prima di attribuirlo alla gestione dual-core.
