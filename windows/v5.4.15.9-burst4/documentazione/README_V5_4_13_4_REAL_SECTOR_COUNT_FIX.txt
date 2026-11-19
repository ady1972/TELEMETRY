GOATS RT Manager V5.4.13.4 - REAL SECTOR COUNT FIX

Correzione gestione settori circuito:
- nel formato pista/GTC3 le voci `sectors` sono LINEE split intermedie;
- N linee intermedie corrispondono a N+1 settori cronometrati reali;
- esempio: 2 linee -> S1 finish/linea1, S2 linea1/linea2, S3 linea2/finish;
- il protocollo USB resta invariato e continua a trasferire N linee fisiche, evitando incompatibilita' e corruzione del catalogo;
- nella finestra dei circuiti presenti sul laptimer il Manager mostra ora sia i settori reali sia le linee intermedie;
- chiarite le diciture nell'editor circuito e nei messaggi di validazione.

Tutte le altre funzioni della V5.4.13.3 sono mantenute.
