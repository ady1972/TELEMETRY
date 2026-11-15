# Verifiche dell'importazione Mobile / Windows

I test usano solo esempi distribuiti e dati sintetici in directory temporanee.
Non aprono porte seriali, non inviano richieste cloud e non cambiano i sorgenti.
La variante Windows importa Qt per verificare i cataloghi e richiede le
dipendenze di `windows/v5.4.15.4-burst4/requirements.txt`; la variante Mobile verifica il
motore Python fuori da Android e usa la libreria standard.

Dalla root della repository:

```sh
python tests/mobile_windows/verify_import.py windows
python tests/mobile_windows/verify_import.py mobile
```

I processi vanno eseguiti separatamente perché i due progetti distribuiscono
moduli omonimi con implementazioni proprie. Sono previsti 12 test Windows
e 10 Mobile, oltre alle esclusioni dei casi specifici dell'altra piattaforma.
Non sostituiscono build APK, avvio nativo Windows o prove hardware.
