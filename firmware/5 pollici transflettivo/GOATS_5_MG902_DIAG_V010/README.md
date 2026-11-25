# GOATS 5″ MG902 DIAG-R1 — versione 0.1.0

Nuovo firmware diagnostico indipendente per VIEWE UEDX80480050E-WB-B,
ESP32-S3, flash 16 MB, PSRAM octal 8 MB, pannello RGB 800×480.
Deriva dai sorgenti dell'archivio `mg902-diag.zip` fornito dall'utente.
Non è ancora un laptimer: mantiene le sei pagine diagnostiche del progetto allegato.
I firmware RLCD, Guition e il precedente firmware 5″ restano invariati.

## Installazione ESPHome

Copia nella stessa cartella ESPHome:

```text
goats_5_mg902_diag.yaml
goats_5_mg902_diag_poll.yaml
GOATS_5_MG902_DIAG_V010/
  components/ubx_diag/...
  tests/test_host.cpp
  README.md
```

Per la prima prova compila e installa **goats_5_mg902_diag.yaml** via USB.
Non occorrono `secrets.yaml`, rete Wi-Fi o Home Assistant. Usare ESPHome
2026.7.3, versione usata per le verifiche software, o una versione compatibile
con `mipi_rgb`, LVGL e ESP-IDF. La prima compilazione scarica dipendenze e font.
I log passano dalla USB UART della scheda (CH340C/UART0), a 115200 baud.

## GPS: ascolto passivo come RLCD

- TX del GPS → GPIO17 della scheda; GND comune.
- RX del GPS scollegato: il firmware principale non configura un TX e non
  invia richieste né comandi al ricevitore.
- Ricevitore già impostato a UBX, 230400 baud, NAV-PVT 25 Hz; buffer RX 8192 byte.
- Alimentazione del modulo secondo le sue specifiche; nessuna modifica
  firmware alle costellazioni, al modello dinamico o ai parametri GNSS.
- I satelliti **usati** provengono da NAV-PVT. I **visti** sono quelli con
  C/N0 > 0 in un NAV-SAT valido ricevuto negli ultimi 5 secondi.
  `Visti --` significa dato assente/scaduto, non zero satelliti.

Se il modulo non trasmette NAV-SAT spontaneamente, il profilo passivo non può
ricavare i satelliti visti dal solo NAV-PVT.

### Profilo opzionale con interrogazioni

Solo per leggere più diagnostica, collegare anche GPIO10 → RX GPS e installare
**goats_5_mg902_diag_poll.yaml**. Deve essere presente anche lo YAML principale.
GPIO10 è il CS della microSD: **lasciare vuoto lo slot SD** con questo profilo.
Vengono inviati esclusivamente poll NAV-SAT/NAV-DOP/NAV-STATUS/MON-RF, MON-VER
e CFG-VALGET RAM. Nessun CFG-VALSET, salvataggio o cambio della configurazione.
Le risposte dipendono dal modello e dal protocollo supportato dal modulo.
Le chiavi non lette vengono ritentate al massimo tre volte per gruppo;
un NAK e una risposta mancante sono mostrati separatamente.

## Display e schermata nera

L'utente ha osservato schermo nero con **luce ancora accesa e log USB presenti**.
Questo orienta l'indagine verso rendering e segnale RGB; non identifica da solo
la causa. L'originale non contiene un timeout di spegnimento automatico.

Questa variante usa:

- retroilluminazione GPIO2 al **50%** dopo l'avvio, gamma 1, nessuna dissolvenza;
- profilo RGB già usato sul precedente 5″: PCLK **32,4 MHz**, invertito,
  orizzontale 24/136/40, verticale 2/21/37, totale 1000×540, 60 Hz;
- PSRAM octal 80 MHz, cache dati 64 KB/linea 64 byte, esecuzione da PSRAM,
  ISR RGB in IRAM; pin RGB identici al progetto allegato;
- LVGL con aggiornamenti parziali, buffer 25%, ciclo di rendering 33 ms,
  attivo senza timer di pausa; controllo ogni 10 s che riprende LVGL solo se
  risulta effettivamente in pausa;
- nessun Wi-Fi, access point, server web o OTA;
- log `display_diag` ogni 10 s: disegni completati, età ultimo disegno,
  durata massima, riprese da pausa; uptime, heap, PSRAM e causa reset.

Il driver `mipi_rgb` di ESPHome gestisce già il riavvio del segnale RGB e il
bounce buffer. Non vengono aggiunti reset continui o riavvii del microcontrollore.
Un disegno completato certifica il percorso software LVGL, **non** l'immagine
fisicamente visibile. La scomparsa dell'immagine resta da verificare sul pannello:
non è dichiarata risolta dalla sola compilazione.

Per il collaudo, lasciare il dispositivo acceso oltre il tempo del precedente
oscuramento. Se ricapita, conservare i log prima e dopo il nero: verificare se
`draw` cresce, `age` resta basso, `paused=0`, e se uptime e memoria sono continui.
Questo aiuta a distinguere un problema di rendering da una perdita del segnale
RGB/pannello. Annotare anche la pagina e il tempo dall'accensione.

## Navigazione senza touch

Le sei pagine ruotano automaticamente ogni **10 secondi**: fix, collegamento,
satelliti, modulo/configurazione, sistema/display, colori di test.
BOOT breve (30–800 ms): pagina successiva; BOOT lungo (1–8 s): azzera contatori
e riavvia le letture di configurazione nel profilo poll. Non resetta il GPS.
Per fermare la rotazione impostare `auto_pages: "false"` nello YAML principale.
Touch GT911 non configurato.

## Correzioni diagnostiche rispetto all'allegato

1. Un iTOW ripetuto/regressivo entra nel verdetto del collegamento: non basta
   ricevere 25 frame/s per dichiarare il flusso temporalmente regolare.
2. NAV-DOP e NAV-STATUS scadono dopo 5 s; non vengono mostrati come dati attuali
   dopo l'interruzione dei relativi messaggi.
3. Dispersione accumulata solo con fix 3D valido e velocità da 0 a <0,5 m/s;
   riparte da zero dopo movimento/perdita del fix.
4. Una risposta CFG-VALGET parziale non completa l'intero gruppo: vengono
   richieste solo le chiavi mancanti, con tentativi limitati.
5. La pagina principale distingue satelliti usati e visti, e dati mancanti.

## Verifiche e provenienza

Test host con frame sintetici e fuzz del parser, ASan/UBSan:

```sh
g++ -std=c++17 -Wall -Wextra -fsanitize=address,undefined \
  -fno-omit-frame-pointer GOATS_5_MG902_DIAG_V010/tests/test_host.cpp \
  -o /tmp/mg902-tests
/tmp/mg902-tests
```

Risultato: **74/74 verifiche superate**, incluse 40.000 iterazioni fuzz.
Validazione ESPHome e compilazione dei due profili: vedere `VERIFICHE.txt`
nel pacchetto. Nessun test hardware eseguito durante questa modifica.

Archivio sorgente originale: `mg902-diag.zip`.
SHA-256: `dbb71c22f9a7b23f9fbc1afddc1e58d573bda4257e660b8e022dc52c6b041cbc`.
Parser e interfaccia derivano dall'allegato; adattamenti DIAG-R1 documentati sopra.
Versione progetto conservata **0.1.0**; etichetta distinta **DIAG-R1**.
