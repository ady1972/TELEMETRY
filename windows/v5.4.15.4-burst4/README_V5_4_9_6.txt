GOATS RT Manager V5.4.9.6

FIX AVVIO / PYSIDE6
- nuovo launcher Windows robusto;
- cerca automaticamente Python 3.10, 3.11, 3.12, 3.13 o 3.14;
- crea un ambiente virtuale locale .goats_venv;
- verifica PySide6, pyserial e requests;
- installa automaticamente le dipendenze mancanti;
- riutilizza l'ambiente locale agli avvii successivi;
- non dipende più dai pacchetti installati nel Python globale;
- diagnostica aggiornata alla V5.4.9.6.

NOTA
Il primo avvio può richiedere alcuni minuti perché PySide6 è un pacchetto
di grandi dimensioni e deve essere scaricato. È necessaria una connessione
Internet solo se le dipendenze non sono già presenti nell'ambiente GOATS.

Mantiene tutte le modifiche V5.4.9.5:
- IMPORTA CIRCUITI DAL LAPTIMER;
- interfaccia Sessioni USB compatta;
- interfaccia AssistNow compatta;
- eliminazione dell'intestazione duplicata AssistNow Predictive.
