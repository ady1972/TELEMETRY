# Roadmap GOATS RT

Aggiornata il 13/11/2026. Ambito: laptimer RLCD 4.2 e Guition 4.3.

## Punto di partenza: RC1

L'utente riferisce che, nell'ultimo test comparativo, tempi e funzionamento
del laptimer RLCD e del Guition 4.3 si sono allineati. RC1 identifica questa
base (RLCD TEST26 e Guition V1.0.22 RLCD26 USB) come candidata al rilascio. L'esito riguarda il test riferito dall'utente;
non implica la risoluzione delle anomalie elencate sotto.

La promozione a RC1 aggiorna identificativi e documentazione. Le correzioni
seguenti sono pianificate, non incluse nella promozione.

## 1. Orario locale RLCD — da fare

Segnalazione: RLCD visualizza un orario indietro di un'ora.

Obiettivo: ricavare l'orario locale Europe/Rome dalla data/ora GNSS valida,
gestendo ora solare, ora legale e cambio di giorno, con lo stesso risultato
sui due dispositivi. Evitare una correzione fissa di +1 ora valida soltanto
in una parte dell'anno. Non cambiare epoche GNSS, frequenza o tempi di gara.

Verifica prevista: confronto RLCD/Guition con istanti UTC noti in inverno,
estate, transizioni dell'ora legale e attraversamento della mezzanotte.

## 2. Data e progressivo nei nomi dei file — da fare

Segnalazione: il numero relativo al giorno non cambia; cresce soltanto
il progressivo delle sessioni.

Obiettivo: generare il nome dalla data effettiva di inizio registrazione,
con un progressivo sessione distinto dalla data. Definire una convenzione
comune ai due dispositivi e compatibile con FAT, esportazione e Manager;
non sovrascrivere file esistenti. I file già registrati devono rimanere leggibili.

Verifica prevista: più sessioni nello stesso giorno, giorno successivo,
riavvio, cambio mese/anno, anno bisestile e registrazione iniziata senza
una data GNSS valida. I nomi devono restare univoci anche dopo un riavvio.

## 3. Data esatta di registrazione nei dettagli del file — da fare

Obiettivo: conservare data e ora reali di inizio registrazione e mostrarle
nei dettagli della sessione/file, mantenendole dopo riavvio ed esportazione.
Verificare anche i timestamp FAT visualizzati dal PC: la data di copia o
esportazione non deve essere presentata come data di acquisizione.

Data e ora devono riferirsi allo stesso istante usato per il nome del file,
con una convenzione di fuso orario esplicita. Per vecchi file senza questa
informazione mostrare "data non disponibile", senza inventare una data.

Verifica prevista: confronto con l'ora reale di registrazione su dispositivo,
file esportato e dettagli nel Manager/PC; riapertura di file storici.

## Vincoli comuni

Preservare il comportamento di cronometraggio allineato in RC1, i parametri
GNSS e la compatibilità dei dati. Verificare le correzioni su entrambi i
dispositivi con sessioni confrontabili prima di promuovere la release successiva.
