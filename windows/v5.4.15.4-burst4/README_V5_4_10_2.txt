GOATS RT Manager V5.4.10.2

FIX DOWNLOAD SESSIONI / "RISPOSTA PROTOCOLLO V2 NON VALIDA: NESSUNA"

Causa:
dalle versioni firmware che ricostruiscono la traccia completa dalla microSD,
GSES2_GET deve prima leggere e convertire Sxxxxxx.CSV. Con migliaia di punti
il firmware può impiegare diversi secondi prima di inviare GSES2_BEGIN.
Il Manager usava timeout seriale 0,25 s e concludeva erroneamente "nessuna".

Modifiche:
- attesa iniziale GSES2_BEGIN fino a 25 s;
- lettura delle righe protocollo indipendente dal timeout seriale breve;
- timeout dei chunk V2 più robusti;
- fallback automatico al vecchio GSES_GET;
- il fallback riapre la porta seriale pulita;
- messaggio diagnostico finale mostra separatamente errore V2 e legacy.

Compatibile con GOATS RT V11.0.1.36 e con firmware precedenti che espongono
solo il protocollo sessioni legacy.

Mantiene:
- interfaccia integrata Circuiti / Sessioni USB / AssistNow;
- import automatico delle sessioni nel database;
- cartelle <circuito>_<data>;
- trace CSV e analisi mappa;
- launcher automatico Python/PySide6.
