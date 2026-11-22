# RC3 — Aggiornamento USB e caratteri in grassetto

RC3 usa il GOATS RT Manager Windows V5.4.15.12 per aggiornare via USB Guition 4.3 e RLCD 4.2 monocromatico. Guition usa font Roboto e Roboto Condensed grassetto anche nei widget LVGL che ereditano il font predefinito. RLCD mantiene Roboto Condensed 700, già configurato per tutti i testi visualizzati dal firmware. Le due configurazioni ESPHome RC3 spostano il riferimento alla propria cartella mantenendo le basi RC2.

## Aggiornare dal Manager

1. Terminare la sessione, espellere eventuali volumi USB Mass Storage e collegare il laptimer a una porta dati USB. Entrare in modalità download tenendo premuto BOOT durante il reset o l'accensione, secondo i pulsanti presenti sulla scheda.
2. Aprire **Firmware USB** nel Manager, selezionare la porta e premere **Rileva laptimer**. Il Manager identifica il modello dalla tabella partizioni e controlla l'identità dell'applicazione quando l'intestazione è leggibile.
3. Selezionare **Scarica firmware da GitHub** per ottenere il pacchetto RC3 del modello rilevato. Per l'installazione offline, scaricare o copiare il pacchetto in anticipo e scegliere **Apri file firmware locale**. Il file `.bin` e il suo `.json` devono avere lo stesso nome base e stare nella stessa cartella.
4. Premere **Aggiorna firmware via USB** e confermare. Il Manager ricontrolla SHA-256 rispetto al manifesto e alla propria copia dell'hash ufficiale RC3, quindi verifica destinazione dell'immagine, modello e selezione dello slot prima della scrittura.
5. Attendere la verifica della scrittura e il riavvio. Controllare **RC3** nella schermata Info del dispositivo. Se resta in modalità BOOT, rilasciare BOOT e riavviare.

Il Manager scrive solo l'applicazione a `0x10000`. La tabella delle partizioni, il bootloader e NVS restano fuori dall'intervallo scritto. L'importazione USB e la microSD seguono la procedura già in uso. L'aggiornamento richiede il layout RC2 verificato e un dispositivo che avvia dallo slot iniziale. In caso di interruzione, rientrare in modalità BOOT e ripetere con lo stesso pacchetto. Un dispositivo senza bootloader o con layout diverso richiede una installazione completa tramite USB prima di usare questo flusso.

I pacchetti per il Manager e per il download manuale sono nel [branch di distribuzione RC3](https://github.com/ady1972/TELEMETRY/tree/rc3-usb-packages).

## Collaudo

- Build ESPHome 2026.7.3 riuscita su entrambi i modelli. Guition 1.089.728 byte, RLCD 645.680 byte. Gli hash delle tabelle coincidono con quelli delle configurazioni RC2 di riferimento.
- Suite software RC2 superata per cronometraggio, tracciamento e salvataggio.
- Sette test USB superati con trasporto simulato. Prova Qt della pagina riuscita per rilevamento, download e abilitazione dei pulsanti.
- Da verificare su hardware: aggiornamento RC2 → RC3 su entrambi i modelli, riavvio e versione, aggiornamento ripetuto, recupero dopo interruzione, impostazioni e microSD, testi più lunghi e schermate di gara, GNSS 25 Hz, tempi e settori.
