GOATS RT Manager Android V0.2.1 - TRACK EDITOR + WI-FI + CLOUD SYNC

Novità rispetto alla V0.2.0:
- rimossa completamente la sezione Bluetooth/BLE per il trasferimento sessioni;
- importazione dal Lap Timer esclusivamente via Wi-Fi;
- archivio locale dei file sessione originali in aggiunta al database SQLite;
- selezione di una cartella Cloud Sync tramite il selettore Android;
- compatibile con provider esposti dal sistema (Google Drive, OneDrive, Dropbox, Synology Drive, memoria condivisa, ecc.);
- sincronizzazione bidirezionale: cloud -> Android e archivio Android -> cloud;
- opzione Sincronizzazione automatica: dopo ogni nuova importazione il file viene salvato anche nel cloud;
- mantenuta la piena gestione Circuiti/editor della V0.2.0.

Flusso consigliato:
1. Creare una cartella dedicata, ad esempio GOATS_RT_CLOUD.
2. Nell'app Android: Sessioni -> CLOUD -> SELEZIONA CARTELLA.
3. Attivare Sincronizzazione automatica.
4. Sul Manager Windows V5.4.13.9 selezionare la cartella locale corrispondente sincronizzata dal client cloud.
5. Attivare Auto Sync sul PC.

Le sessioni trasferite dal laptimer via Wi-Fi vengono prima archiviate localmente, poi importate nel database e, se Cloud Sync è attivo, copiate nella cartella cloud.
