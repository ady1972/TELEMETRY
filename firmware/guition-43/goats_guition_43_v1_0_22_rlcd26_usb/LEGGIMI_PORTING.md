# GOATS Guition V1.0.22 RLCD26 USB

Versione separata da V1.0.20 e V1.0.21. Porta l'integrazione di cronometraggio,
traccia e archivio RLCD TEST26 mantenendo l'interfaccia e la compatibilita' Guition.
Non e' una certificazione dell'accuratezza GNSS o un test su dispositivo.

## ESPHome Builder Windows

Se si usa il repository: aprire **firmware\guition-43** e selezionare
**goats_guition_43_v1_0_22_rlcd26_usb.yaml**. La sottocartella
**goats_guition_43_v1_0_22_rlcd26_usb** deve restare accanto al YAML.
Nel pacchetto ZIP usare la cartella radice del pacchetto, con la stessa struttura.
Non selezionare la sola cartella degli header e non usare i YAML precedenti.

```powershell
python -m esphome config goats_guition_43_v1_0_22_rlcd26_usb.yaml
python -m esphome compile goats_guition_43_v1_0_22_rlcd26_usb.yaml
```

## Catena dei dati

1. Il parser originale valida il checksum NAV-PVT e mantiene i dati GPS della UI.
2. Il consumatore accoda l'epoca completa: coordinate, velocita', iTOW, istante ESP,
   HDOP e satelliti. Esclude duplicati consecutivi iTOW come RLCD.
3. Il consumatore di cronometraggio usa l'ammissibilita' RLCD: gnssFixOK, fix 3D e
   almeno quattro satelliti. Non cambia il criterio GPS mostrato sulla UI.
4. Finita la decodifica, ogni epoca viene consegnata una sola volta al motore e
   alla sessione. Il consumatore non chiama FatFS o NVS.
5. La sessione accoda i punti CSV in RAM. Non campiona piu' l'ultima posizione
   globale con un timer: un segnale assente non produce posizioni duplicate.
6. Un tick esterno al parser apre la traccia, scrive fino a otto punti e salva
   al massimo un record giro NVS. La finalizzazione svuota la coda prima di chiudere.

La coda NAV e quella CSV hanno 512 posti. Se piene, rifiutano il nuovo campione;
non nascondono la perdita cancellando il piu' vecchio. Gli overflow NAV sono
nei contatori diagnostici; le perdite CSV sono in GOATS_SESSIONS.trace_dropped().
Il diario NVS trattiene globalmente gli ultimi 80 giri; la coda di persistenza
e la lista giri della sessione sono limitate a 80. La UI conserva al massimo
20 sessioni. Questi limiti non arrestano il motore o la traccia CSV.

Il tempo CSV deriva dalle differenze iTOW, con gestione del confine settimana.
Un iTOW duplicato non aggiunge un punto; un salto all'indietro/reset non viene
interpretato come una settimana di durata. Dopo il salto si riparte dalla
nuova sequenza; le anomalie sono diagnosticate, non corrette nel cronometro.
HDOP appartiene all'ultimo NAV-DOP decodificato al momento del PVT.

## Motore e grafica

goats_laptimer.h e' identico byte per byte al motore V1.0.20/RLCD TEST26.
Traguardo, intermedi, riarmo, minimo giro, BEST, passo gara e filtri restano
quelli del riferimento. Il motore riceve ancora l'istante ESP di decodifica:
il parametro iTOW e' ignorato al suo interno. Non sono state introdotte
interpolazione temporale, direzione di attraversamento o nuove regole di invalidita'.

Racing conserva geometria/font/colori/oggetti. I colori dei settori leggono
ora lo stesso stato conservato usato dai delta; il lampeggio post-giro confronta
il BEST come RLCD. La pagina post-giro Guition mantiene le informazioni sul passo.
Il dettaglio sessioni estende verticalmente le colonne esistenti con S1/S2/...;
gli altri campi aggiungono righe vuote per mantenere l'allineamento. Le sessioni
vecchie senza settori continuano a mostrare solo i valori originali.

## Archivio compatibile e recupero

GSA3, GSA2, CSV GPS e protocolli Manager/USB restano invariati. Le nuove
informazioni non vengono inserite nel payload GSES/GSES2 o nel CSV dei punti.

- La SD conserva metadati GSA3 e traccia con lo schema precedente.
- Il file supplementare E<id>.GSE contiene GSE1, ID sessione, numero/tempo giro,
  fino a 13 settori per giro e CRC32. Il caricamento controlla CRC, lunghezze,
  numero giro e tempo prima di associare i settori ai metadati esistenti.
- Il diario NVS goats_j22 conserva fino a 80 record giro con CRC e cache RAM.
  I disegni della UI non effettuano letture NVS/SD. Il diario non richiede SD.
- Al riavvio, metadati originali, eventuale vecchio checkpoint, diario e file
  GSE vengono riconciliati. Record NVS incompatibili con data/ora/pista o tempo
  di un giro gia' archiviato non sovrascrivono il dato esistente.
- Senza SD, si conservano giri e settori nel diario; NON esiste una traccia CSV
  persistente alternativa. Senza completamento di un giro, il diario circuito
  non ha un record da recuperare. Una sessione libera viene registrata alla chiusura.
- Chiusura e scarto fermano il motore; ulteriori campioni non riaprono una
  sessione chiusa. Il reset sessione esplicito riabilita l'acquisizione.
- Lo scarto elimina il diario della sessione corrente. La cancellazione di
  una sessione elimina anche il relativo GSE e i record NVS, oltre ai file originali.

Un salvataggio puo' essere accettato grazie al diario NVS anche se manca il CSV
su SD. Verificare la presenza della SD e il file last_save_status.txt prima di
considerare disponibile la traiettoria completa; il diario non la sostituisce.

## SD, USB e limiti real-time

Il mount/probe post-boot attende uno stato senza cronometraggio, sessioni o USB
occupata. Se non si raggiunge tale stato entro 120 s, viene saltato per quel boot.
Il tick storage viene sospeso durante transazioni Manager e MSC e per 2 s dopo
l'ultima attivita' USB. Un trasferimento lungo puo' esaurire le code RAM.

Come RLCD, FatFS/NVS restano sul task applicativo: differire e limitare il numero
di punti per tick NON rende non bloccante una singola f_write/f_sync/nvs_commit.
Restano da misurare su hardware latenza SD, continuita' UART e RAM disponibile.
La sincronizzazione periodica ogni 25 righe resta; in chiusura e' rimossa la
f_sync duplicata immediatamente prima di f_close, come TEST26.
I checkpoint SD ripetuti nel percorso di fine giro sono sostituiti dal diario NVS.

GNSS/UART/pin, baud rate 230400, configurazione del ricevitore e frequenza
restano invariati. Nessun Wi-Fi, OTA o nuovo comando USB. La diagnostica V1.0.21
e' mantenuta; il logger con baud_rate 0 non offre log visibili sul monitor USB.

## Verifica

Test di integrazione e compilazione Linux: workflow GitHub Actions
"Guition V1.0.22 verification" sulla PR del branch porting/guition-v1.0.22-rlcd26.
Il risultato finale della compilazione e le eventuali limitazioni sono riportati
in VERIFICA.md. Nessun test su display, SD o circuito reale e' implicito.
