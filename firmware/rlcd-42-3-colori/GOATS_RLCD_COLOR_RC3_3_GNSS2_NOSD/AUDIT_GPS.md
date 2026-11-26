# RC3.3 NOSD AUDIT — verifica senza tasti

Questa pagina osserva la stessa variante senza SD della Racing normale:
medesimi UART, configuratore, parser, core, NVS e intervalli di polling.
Il renderer Racing viene sempre eseguito. Ogni dieci secondi viene sostituito
soltanto il frame finale con i contatori AUDIT; il disegno supplementare e le
zone SPI trasferite possono comunque cambiare il carico temporale.

Attendere circa un minuto, poi fotografare tutta la pagina **RC3.3 NOSD AUDIT**
quando compare. La riga HEAP/versioni cambia ogni sei secondi: se possibile
fotografare entrambe le informazioni. Non occorrono tasti o log seriale.

| Campo | Significato |
|---|---|
| INIT | Componente GNSS attivato da on_boot |
| CFG | Funzione di configurazione terminata; non prova l'accettazione dei comandi |
| MSC | Sempre 0 in questa variante: Mass Storage escluso |
| UARTERR | Bus UART segnato fallito da ESPHome |
| UART / SET / HW | Periferica ESP, baud impostato e baud letto dal driver |
| RX / UBX / CKERR | Byte letti, frame con checksum valido ed errori |
| POLL / PVT Hz | Chiamate al lettore e frequenza osservata dal parser |
| CORE | NAV-PVT distinti passati al core RC3.3, prima del controllo del fix |
| SAT / FIX / OK | Satelliti usati/visibili, tipo fix UBX e bit gnssFixOK |
| ETA / UP / RX1 | Eta' PVT in clock ESPHome, uptime e livello istantaneo GPIO1 |
| DRV / GETERR / BUF | Driver installato, errore lettura baud e byte in buffer |
| HEAP / MAX | RAM interna libera e massimo blocco contiguo |
| ESPHOME / IDF | Versioni effettive della compilazione caricata |

Il livello istantaneo GPIO1 non dimostra la presenza o assenza di impulsi.
Il controllo del buffer non consuma byte e non invia comandi al GPS.
Un valore hardware 230432 anziche' 230400 e' un normale arrotondamento del baud.

Gli stati distinguono boot non attivato, polling assente, configurazione non
terminata, errore driver, nessun byte, byte senza UBX, UBX senza NAV-PVT,
NAV-PVT non passato al core e core con/senza fix 3D.

Per la prima prova si puo' installare **bin/firmware.audit.factory.bin** tramite
ESPHome Web: viene fornito gia' compilato con dipendenze note. In alternativa
ricompilare lo YAML `_nosd_audit.yaml`; la pagina mostra la versione ESPHome.
La SD rimane esclusa in entrambe le procedure.

La fotografia della DIAG2 standalone conferma comunicazione/fix, ma non
conferma l'integrazione RC3.3. La mancanza della SD e il vecchio ciclo di mount
sono una variabile concreta rimossa; l'esito GPS richiede ancora questa prova.
