V5.4.15.0 GNSS BETA
- Nuova pagina Configurazione GNSS nel menu laterale.
- UART diretto: MON-VER, richiesta CFG-RATE-MEAS, richiesta CFG-UART1-BAUDRATE.
- Richiede pyserial e adattatore USB-UART con livelli logici 3,3 V.
- Test sintattico completato; test su ricevitore reale NON eseguito.
- NON include configurazione costellazioni, NMEA, backup automatico o ponte tramite RLCD.
- Prima di scrivere impostazioni fare backup con u-center.
- ACK conferma accettazione comando, NON frequenza reale o persistenza.
- La modifica baud può impedire la lettura dell'ACK al vecchio baud.
- Sessioni seriali e funzionalità preesistenti mantenute dal pacchetto di origine.
