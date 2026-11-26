# DIAG3 + RC3.3 STEP1 — motore in RAM

La DIAG3 e' il nuovo riferimento: l'utente ha dichiarato **«la diag3 e' perfetta»**
il 26/11/2026. Questo e' il primo passo di integrazione della RLCD RC3.3 su
quella base; non riprende il precedente porting Racing che aveva perso il GPS.

## Cosa integra questo passo

- Motore laptimer e tipi circuito RC3.3, con logiche giro/settori, LAST/BEST,
  delta e passo gara; stessi sorgenti del riferimento dentro guardie private.
- Consumatore NAV-PVT e riconoscimento automatico circuiti della RC3.3.
- Rilevamento sessione in corso e velocita' massima per giro in RAM.
- Catalogo gia' letto dalla DIAG3, copiato una sola volta nelle strutture RC3.3.

La pagina resta quella della DIAG3, con satelliti/HDOP/velocita' 60px e tutti
i contatori di stabilita'. Cambiano solo il titolo **DIAG3 + RC3.3 STEP1** e
l'ultima riga, che mostra il lavoro del motore:

```text
CORE RC3.3:1234 V:1200 G:0 P:0
```

- **CORE**: NAV-PVT distinti elaborati dal consumatore RC3.3. Deve crescere
  mentre arrivano dati; i messaggi con iTOW ripetuto sono scartati come in RC3.3.
- **V**: campioni che passano i criteri RC3.3 (tipo fix >=3, gnssFixOK,
  almeno 4 satelliti e coordinate entro i limiti). Un fix 2D puo' essere
  mostrato come valido dalla DIAG3, senza incrementare V.
- **G**: giri completati dal motore.
- **P**: circuiti presenti nel catalogo caricato dalla DIAG3. Con P=0 i dati
  GPS e CORE funzionano comunque, ma non si possono rilevare giri reali.

I giri di questo passo restano in RAM. Non si attivano ancora archivi NVS
RC3.3, menu, renderer Racing, import/export Manager o altri livelli hardware.
La base DIAG3 conserva le proprie letture/catalogo e inizializzazione NVS
originali; l'integrazione aggiuntiva non effettua accessi NVS per campione.

## Il GPS resta nella DIAG3

UART, logger, framework, pin, buffer, partizioni, configuratore e parser
sono identici alla DIAG3. Stessi 17 frame, cinque cambi baud, ritardi e
richiesta 230400/25 Hz in RAM. Stesso componente e ciclo principale,
stesso driver LCD/SPI; nessun secondo display o lettore UART viene creato.

Un callback passivo sui frame gia' validati passa il payload NAV-PVT originale
al consumatore RC3.3, senza modificarlo. La vecchia coda COLOR viene soltanto
svuotata: non alimenta un secondo laptimer. Non vengono chiamati setup/tick
USB della RC3.3, mount SD, TinyUSB o scritture di archivi. La SD rimane esclusa.

Il motore RC3.3 viene compilato soltanto nel file .cpp del componente. Gli
header privati non creano un secondo motore nel main.cpp generato da ESPHome.
In questo componente il codice RC3.3 usa millis Arduino, come la DIAG3;
nessuna macro del clock del precedente porting completo viene importata.

## Installazione e prima prova

Estrarre tutto, tenere affiancati `goats_42_diag3_rc33_step1.yaml` e la cartella
`GOATS_DIAG3_RC33_STEP1`, quindi compilare/installare con ESPHome via USB.
Nello ZIP sono inclusi anche `bin/firmware.factory.bin` gia' compilato per
ESPHome Web (immagine completa, offset 0x0 se richiesto) e l'applicazione
`firmware.ota.bin`, che non va usata come immagine completa.
Nessun Wi-Fi o OTA introdotto, nessun Manager necessario.

Non cambiare fili: GPS TX -> GPIO1, GPS RX <- GPIO2, massa comune;
LCD CS10/DC9/RST8/MOSI11/CLK12. Scheda ESP32-S3 N16R8, flash 16 MB.
Nessun pulsante o SD richiesto per questa prova.

Ripetere la stessa prova della DIAG3: verificare i quattro valori principali,
FIX CONT/PERSI/BUCHI PVT e, in piu', CORE e V che crescono. Dopo alcuni minuti
fotografare l'intera pagina. G=0 fuori circuito o senza catalogo e' normale.
Il primo frame e la sequenza di avvio DIAG3 rimangono conservati.

Compilazione e prove software in `VERIFICA.md`. L'esito sul dispositivo di
questo nuovo blocco deve ancora essere verificato prima delle parti successive.
