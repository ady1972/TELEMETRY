
# GOATS RT - Istruzioni per Codex

## Obiettivo
Sviluppare firmware di telemetria kart per ESP32-S3,
con cronometraggio GNSS a 25 Hz.

## Piattaforme
- Guition 4.3": display 480x272, ESP32-S3.
- RLCD 4.2": display SPI, ESP32-S3.
- GNSS MG-902 con u-blox M9N.

## Firmware di riferimento
- Guition V1.0.15: riferimento stabile.
- Guition V1.0.22 RC1: candidata al rilascio, base V1.0.22 RLCD26 USB.
- RLCD RC1: candidata al rilascio basata su TEST26.
- RLCD TEST26: riferimento per cronometraggio e settori, conservato invariato.
- Allineamento tempi/funzionamento TEST26 e Guition V1.0.22 confermato
  dall’utente il 13/11/2026. Problemi data/ora aperti in ROADMAP.md.

## Vincoli GNSS
Non modificare senza autorizzazione:
- Protocollo UBX NAV-PVT.
- Frequenza 25 Hz.
- Baud rate 230400.
- Configurazione UART e pin hardware.
- Costellazioni e configurazione del ricevitore.
- Acquisizione e gestione temporale GNSS.

## Grafica
- Conservare il layout originale di ogni dispositivo.
- Non modificare font, colori e posizionamento
  senza richiesta.
- Mantenere coerenti splash screen, schermata Info
  e versione firmware.

## Sessioni e microSD
- Preservare la registrazione dei punti GPS a 25 Hz.
- Non modificare il formato CSV senza richiesta.
- Evitare operazioni SD bloccanti durante il cronometraggio.
- Non modificare il protocollo di trasferimento USB
  senza autorizzazione.

## Wi-Fi e OTA
- Non introdurre Wi-Fi o OTA nei firmware
  senza richiesta esplicita.

## Gestione versioni
- Non sovrascrivere le versioni stabili.
- Utilizzare branch separati per le modifiche.
- Documentare le modifiche effettuate.
- Aggiornare coerentemente tutti i riferimenti
  alla versione firmware.

## Compilazione
- Utilizzare ESPHome.
- Verificare la compilazione quando possibile.
- Non dichiarare funzionante un firmware
  senza test hardware.
- Non modificare file non pertinenti alla richiesta.

## Metodo di lavoro
1. Analizzare i sorgenti coinvolti.
2. Identificare dipendenze e possibili regressioni.
3. Applicare modifiche limitate e verificabili.
4. Eseguire controlli e compilazione se disponibili.
5. Riassumere file modificati e risultati.
  
