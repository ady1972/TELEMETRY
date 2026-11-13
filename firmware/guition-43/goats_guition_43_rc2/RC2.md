# RC2 — data, ora e registrazioni

Base: RC1 del 13/11/2026. Le cartelle RC1 rimangono invariate.
Versione predisposta per le prove hardware dell'utente nella settimana
16–22 novembre 2026; non viene dichiarata già collaudata sui dispositivi.

## Correzioni

- Data/ora NAV-PVT UTC convertite con regole Europe/Rome (CET/CEST),
  transizioni alle 01:00 UTC, cambio di giorno/mese/anno e anni bisestili.
  I campioni di gara continuano a usare gli stessi millis/iTOW della RC1;
  motore, UART, baud, frequenza e comandi al ricevitore sono invariati.
- Nome comune `PPDDMMNN.CSV`: **TA06NO01.CSV** significa circuito TA,
  giorno 06, novembre NO, sessione 01 per quel circuito/giorno.
  Due lettere del circuito, giorno a due cifre, mese italiano e progressivo
  da 01 a 99. Mesi: GE FE MZ AP MG GI LG AG SE OT NO DI.
- Il progressivo riparte da 01 per una nuova data/circuito se il nome è libero.
  Si cercano i nomi esistenti anche dopo un riavvio; nessun file è sovrascritto.
  In caso di circuiti con le stesse iniziali o file di un anno precedente
  con lo stesso giorno/mese, si avanza al primo numero libero. L'anno completo
  resta nei dati, dato il limite 8.3 del nome. A 99 nomi occupati il file LIVE
  viene conservato e la chiusura segnala errore, senza inventare un'altra data.
- La data iniziale viene congelata: chiudere dopo mezzanotte non cambia la data
  della sessione. Guition conserva la data di ogni campione in coda, evitando
  di attribuire al primo campione il giorno dell'ultimo messaggio ricevuto.
- I commenti CSV riportano data, ora con secondi e fuso Europe/Rome; le righe
  numeriche, i formati GSA3/GSE e i messaggi del protocollo Manager restano invariati.
- I dettagli mostrano la data di registrazione, non quella di esportazione.
  Una data assente/non valida rimane "DATA NON DISPONIBILE". I vecchi archivi
  Guition con sola precisione al minuto restano visibili senza aggiungere secondi fittizi.
- L'orologio civile ESP32 è sincronizzato in modo differito dal GNSS per i
  timestamp FAT alla creazione. Alla chiusura la data di ultima modifica del
  CSV è impostata alla data/ora iniziale, non all'ora di chiusura. FAT conserva
  i secondi con risoluzione di 2 s; il CSV e i metadati conservano i secondi interi.
  Sul PC la proprietà "creazione" può dipendere dalla copia effettuata dal sistema
  operativo: il riferimento persistente è la data nei dati e nell'ultima modifica.
- Se la data GNSS iniziale manca, il file usa il nome numerico `Sxxxxxx.CSV`
  e non riceve una data inventata da messaggi successivi.
- File LIVE rimasti dopo interruzione o errore vengono conservati come
  `Rxxxxxx.CSV` prima di iniziare una nuova registrazione. Anche una registrazione senza ID NVS valido è recuperata senza cancellare
un precedente RECOV.CSV. I lettori accettano
  i nuovi nomi, i recuperi e i nomi storici; l'associazione ID/sessione→CSV
  è persistita in file Mxxxxxx.TRC anche su RLCD.

## Dettagli dei metadati

Su RLCD una cache NVS separata contiene data e ora delle ultime 80 sessioni;
il formato dei record giro esistenti non cambia. Acquisizione e cattura della
data lavorano in RAM; persistenza e tentativi in caso di errore avvengono fuori
dal consumatore NAV. I dettagli delle sessioni precedenti prive di questi
metadati mostrano data non disponibile. La pagina INFO GPS mostra l'ora locale.

Su Guition data e ora restano nei metadati GSA3 e nel diario NVS esistenti,
ora con i secondi. La registrazione libera senza un tempo GNSS recente non
riutilizza data/ora memorizzate prima della perdita di segnale.

## Verifica software e prove hardware

```sh
python tests/rc2/run.py
```

La suite verifica inverno/estate, transizioni DST, mezzanotte/cambio anno e
bisestile, date invalide, formato TA06NO01, collisioni, progressivo al cambio
giorno, esaurimento 99 file, mappa ID, timestamp FAT, dati ignoti, recupero NVS,
data dei campioni in coda e integrazione Guition con 250 punti a 25 Hz,
lettore GSA3 originale, scarto, guasti SD/NVS e recupero dei giri.
I test FAT eseguono le funzioni reali di chiusura/naming contro un adapter in RAM.
Non riproducono tempi e guasti elettrici di una scheda SD reale.

Prima dell'uso in pista: confrontare l'orario RLCD/Guition, salvare più sessioni
nello stesso giorno, riavviare, verificare il primo numero libero, aprire dal
Manager e tramite USB MSC, confrontare data nei dettagli e proprietà del CSV.
Provare anche il giorno successivo, passaggio di mezzanotte, vecchi file e
avvio senza data valida. Verificare che tempi giro e registrazione restino
allineati alla RC1. Nessun flash automatico viene effettuato.

## Esito verifica del 13/11/2026

Suite `tests/rc2/run.py`: PASS. Validazione e compilazione/link ESP32-S3
con ESPHome 2026.7.3 ed ESP-IDF 5.5.5: PASS.
- RAM: used 181635 bytes from 341760 bytes.
- Flash: used 1209611 bytes from 1835008 bytes.

Nessuna prova hardware RC2 o caricamento sul dispositivo eseguiti.
