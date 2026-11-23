# RC3 — Aggiornamento USB e caratteri in grassetto

RC3.1 si installa via USB su Guition 4.3 e RLCD 4.2 monocromatico con il GOATS RT Manager Windows V5.4.15.17. Il Manager precedente V5.4.15.12 distribuisce ancora RC3. Guition usa font Roboto e Roboto Condensed grassetto anche nei widget LVGL che ereditano il font predefinito. RLCD mantiene Roboto Condensed 700, già configurato per tutti i testi visualizzati dal firmware. Le due configurazioni ESPHome RC3 spostano il riferimento alla propria cartella mantenendo le basi RC2.

## Aggiornare dal Manager

1. Terminare la sessione, espellere eventuali volumi USB Mass Storage e collegare il laptimer con un cavo dati USB.
2. Aprire **Firmware USB** e scegliere la porta COM del laptimer. Per la porta USB nativa Espressif, premere **Entra in BOOT e rileva** e confermare. Per l'ingresso manuale, tenere premuto il BOOT della scheda durante il reset o l'accensione, rilasciarlo, aggiornare l'elenco delle porte e premere **Entra in BOOT e rileva** sulla COM risultante. Il Manager confronta la tabella partizioni e l'identità dell'applicazione.
3. Selezionare **Scarica RC3.1 da GitHub** per ottenere il pacchetto del modello rilevato. Per l'installazione offline, scaricare o copiare il pacchetto in anticipo e scegliere **Apri file firmware locale**. Il file `.bin` e il suo `.json` devono avere lo stesso nome base e stare nella stessa cartella.
4. Leggere il changelog del modello e della versione selezionata. Attendere il confronto con il firmware installato. Se coincide, il Manager disabilita l'aggiornamento. Altrimenti premere **Aggiorna firmware via USB** e confermare. Il Manager ricontrolla SHA-256 rispetto al manifesto e alla propria copia dell'hash ufficiale della versione, quindi verifica destinazione dell'immagine, modello e selezione dello slot prima della scrittura.
5. Attendere la verifica della scrittura e il riavvio. Controllare la versione selezionata nella schermata Info del dispositivo. Se resta in modalità BOOT, rilasciare BOOT e riavviare.

Il Manager scrive l'applicazione nello slot selezionato dal bootloader. La tabella delle partizioni, il bootloader, la selezione dello slot e NVS restano fuori dall'intervallo scritto. L'importazione USB e la microSD seguono la procedura già in uso. L'aggiornamento richiede un layout GOATS riconosciuto e una selezione dello slot verificabile. In caso di interruzione, rientrare in modalità BOOT e ripetere con lo stesso pacchetto. Un dispositivo senza bootloader o con layout diverso richiede una installazione completa tramite USB prima di usare questo flusso.

I pacchetti per il Manager e per il download manuale sono nel [branch di distribuzione RC3](https://github.com/ady1972/TELEMETRY/tree/rc3-usb-packages).

## Collaudo della pubblicazione RC3 iniziale

- Build ESPHome 2026.7.3 riuscita su entrambi i modelli. Guition 1.089.728 byte, RLCD 645.680 byte. Gli hash delle tabelle coincidono con quelli delle configurazioni RC2 di riferimento.
- Suite software RC2 superata per cronometraggio, tracciamento e salvataggio.
- Sette test USB superati con trasporto simulato. Prova Qt della pagina riuscita per rilevamento, download e abilitazione dei pulsanti.
- Da verificare su hardware: aggiornamento RC2 → RC3 su entrambi i modelli, riavvio e versione, aggiornamento ripetuto, recupero dopo interruzione, impostazioni e microSD, testi più lunghi e schermate di gara, GNSS 25 Hz, tempi e settori.

## RC3.1 — Ripartenza sullo stesso circuito dopo «Salva»

- **Guition.** RC3 nascondeva automaticamente il riepilogo dopo 10 secondi lasciando il cronometro in stato di fine registrazione. In questo stato la pipeline scartava le nuove epoche per il cronometraggio. RC3.1 usa lo stesso riarmo alla scadenza e al tocco di «Chiudi». Il test con pipeline e motore reali riproduce il blocco di RC3 e verifica avvio, giro e salvataggio di due sessioni consecutive sullo stesso circuito con RC3.1.
- **RLCD.** La chiusura manuale e quella per inattività usano già lo stesso finalizzatore con riarmo. RC3.1 azzera anche le statistiche velocità di giro in quella transizione. Il test verifica due salvataggi e uno scarto, ciascuno seguito da un nuovo passaggio e un giro cronometrato, oltre al caso di scarto rifiutato.
- **Manager Windows V5.4.15.14.** Scarica RC3.1 per il modello rilevato e verifica versione, SHA-256 e compatibilità prima della scrittura. Da disco accetta anche il pacchetto ufficiale RC3, con versione visibile prima della conferma.

Il test software usa dati sintetici e storage simulato. Il collaudo fisico richiede due uscite consecutive sullo stesso circuito, lasciando sparire il riepilogo Guition senza toccarlo e passando il traguardo a velocità di gara. Controllare che il primo passaggio avvii la seconda sessione e che il giro successivo venga cronometrato.

Build ESPHome 2026.7.3 riuscite per entrambi i firmware RC3.1. Le immagini
applicative misurano 1.089.760 byte per Guition e 645.712 byte per RLCD.
Le tabelle partizioni coincidono con quelle della pubblicazione RC3. I test
della suite RC2, il test di ripartenza su entrambi i modelli, i test Manager
RC3/RC3.1 e la prova Qt con USB simulato sono passati.

## Rilevamento USB nel Manager V5.4.15.14

Il Manager usa il parametro `connect_mode` di esptool 4.14.0. Dopo la
lettura del modello, esptool torna al bootloader per consentire la scrittura
sulla stessa porta. I test attraversano l'API e il parser reali di esptool
con il trasporto simulato. Il collegamento a un dispositivo fisico resta da collaudare.

## Accesso al bootloader nel Manager V5.4.15.15

Se la prima connessione fallisce, **Entra in BOOT e rileva** prova il reset USB
sulla COM selezionata se Windows la identifica come USB Serial/JTAG nativa
Espressif (`303A:1001`). Se la COM cambia dopo il reset, aggiornare l'elenco delle
porte nel Manager. Quando il comando è disabilitato, usare la procedura BOOT
manuale. I test con trasporto simulato verificano il passaggio a `usb_reset`
e il rispetto della porta selezionata. Il reset sul dispositivo fisico resta da provare.

## Selezione dello slot nel Manager V5.4.15.16

Al primo avvio ESP-IDF può inizializzare il record di selezione dello slot.
Il Manager verifica il CRC del record valido più recente, controlla il modello
sullo slot così selezionato e usa il suo indirizzo per la scrittura. Su un
layout GOATS appena inizializzato, con dati di avvio vuoti, la destinazione
è lo slot iniziale. Una selezione illeggibile o ancora in attesa di convalida
ferma la procedura prima della scrittura. I test con esptool e trasporto
simulato verificano entrambe le destinazioni e il blocco sui record non validi.

## Changelog e confronto firmware nel Manager V5.4.15.17

Il comando **Entra in BOOT e rileva** gestisce anche il rilevamento dopo BOOT
manuale. Il changelog compare dopo la validazione di un pacchetto scaricato o
aperto da disco. Il confronto usa il checksum dell'immagine presente nello
slot attivo e viene ripetuto prima della scrittura. Le immagini ufficiali
RC3 e RC3.1 restano convalidate separatamente con SHA-256. I test verificano
entrambi i percorsi di caricamento, il rilevamento dopo BOOT manuale e la mancata scrittura
quando l'immagine coincide, con trasporto simulato.
