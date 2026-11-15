GOATS RT Manager V5.4.13.9 - CARTELLA ARCHIVIO SESSIONI

NOVITÀ
- Nuova pagina Impostazioni.
- Cartella archivio sessioni selezionabile.
- Compatibile con cartelle locali, OneDrive, Google Drive, Dropbox e cartelle Synology sincronizzate/montate.
- Il percorso scelto viene memorizzato in data/manager_settings.json.
- Se la cartella configurata non è disponibile all’avvio, il Manager usa automaticamente l’archivio locale.
- Quando si cambia cartella, l’archivio corrente viene copiato nella nuova posizione.
- Se nella destinazione esiste già goats_rt_sessions.sqlite3, è possibile scegliere se usarlo o sostituirlo.
- Modalità SQLite cloud-safe: journal DELETE per evitare file WAL/SHM persistenti nelle cartelle sincronizzate.

NOTA
Non utilizzare contemporaneamente lo stesso database SQLite da due PC. Attendere la sincronizzazione cloud prima di aprire il Manager sull’altro dispositivo.

Tutte le altre funzioni della V5.4.13.8 restano invariate.
