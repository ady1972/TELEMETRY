GOATS RT Manager V5.4.10.6 - MULTI TRACK MERGE

Correzione invio circuiti:
1. L'elenco Circuiti ora consente la selezione multipla con click successivi.
2. Prima dell'invio il Manager esegue GTRK_GET e legge il catalogo esistente.
3. I circuiti selezionati vengono fusi con il catalogo remoto.
4. Se un nome circuito esiste già viene aggiornato; se è nuovo viene aggiunto.
5. I circuiti remoti non selezionati vengono mantenuti.
6. Se la lettura del catalogo remoto fallisce, il Manager NON invia nulla.

Nota protocollo:
GTC3 non trasferisce l'id JSON del circuito; il matching usa quindi il nome normalizzato (slug), coerente con il parser già presente.
