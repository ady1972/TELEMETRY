# RLCD R12.1 SD R14.2 RC1

Promozione del 13/11/2026, base **RLCD TEST26**.
L'utente conferma che tempi e funzionamento di RLCD TEST26 e Guition V1.0.22
si sono allineati nell'ultimo test comparativo. RC1 è una candidata al rilascio,
non una dichiarazione di assenza di difetti.

Gli originali rimangono conservati. Per ESPHome Builder copiare lo YAML
RC1 esterno insieme alla cartella dedicata. Modificati identificativi,
etichette di versione e percorsi; nessuna modifica a GNSS, cronometro,
registrazione, protocollo Manager o menu. Splash e Info indicano RC1.

Orario locale RLCD, nomi dei file e data di registrazione nei dettagli
sono interventi futuri, descritti nella [roadmap](../../../ROADMAP.md).
La promozione non applica queste correzioni.

## Verifiche della promozione

- Validazione, generazione C++ e compilazione/link ESP32-S3 RC1: PASS
  con ESPHome 2026.7.3, ESP-IDF 5.5.5, Linux (13/11/2026).
- Confronto dei sorgenti e YAML con la base: logiche preservate;
  differenze limitate a identificativi, etichette RC1 e percorsi.
- RAM statica: used 109043 bytes from 341760 bytes. Applicazione: used 639179 bytes from 8126464 bytes.
- Generato `firmware.factory.bin`; nessun caricamento automatico.
- Nessuna nuova prova hardware RC1 eseguita dall'assistente.
