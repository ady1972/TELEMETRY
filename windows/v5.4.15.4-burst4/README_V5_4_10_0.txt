GOATS RT Manager V5.4.10.0

INTERFACCIA UNIFICATA
- Circuiti, Sessioni USB e AssistNow non aprono più finestre esterne.
- Le tre funzioni sono ora integrate direttamente nello stack della finestra
  principale del Manager, raggiungibili dal menu laterale.
- Circuiti mantiene editor mappa, toolbar, invio e import dal laptimer.
- Sessioni USB mantiene download, analisi e cancellazione.
- AssistNow mantiene ZTP, download dati, invio M9N, stato e diagnostica.
- Le modalità Sessioni USB e AssistNow non inizializzano più inutilmente la
  mappa dell'Editor Circuiti, riducendo carico e memoria.
- I vecchi richiami open_tool_mode vengono reindirizzati alle pagine interne.

MANTIENE TUTTE LE FUNZIONI PRECEDENTI
- cartelle sessioni <circuito>_<data>;
- import automatico nel database del Manager;
- refresh automatico elenco sessioni;
- bootstrap automatico PySide6/pyserial/requests;
- import selettivo circuiti dal laptimer;
- fix CSV trace.
