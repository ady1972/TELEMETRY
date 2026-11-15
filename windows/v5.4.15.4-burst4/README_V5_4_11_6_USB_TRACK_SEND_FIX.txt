GOATS RT Manager V5.4.11.6

FIX INVIO CIRCUITI USB

Problema corretto:
- nelle versioni con merge incrementale il Manager apriva la COM per GTRK_GET, la chiudeva e la riapriva immediatamente per GTRK_BEGIN;
- sul Guition questa sequenza poteva provocare il riavvio/reset della connessione USB prima della risposta GTRK_READY.

Correzione:
- GTRK_GET e GTRK_BEGIN ora avvengono nella STESSA connessione seriale;
- la COM non viene chiusa tra lettura del catalogo esistente e invio del catalogo unificato;
- mantenuto il merge non distruttivo: i circuiti non selezionati restano sul laptimer;
- timeout protocollo più robusti.

Tutte le funzioni della V5.4.11.5 restano invariate.
