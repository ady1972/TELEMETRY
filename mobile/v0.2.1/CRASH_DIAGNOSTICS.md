# GOATS RT Manager Android V0.1.1 - Crash diagnostics

Questa build non usa più `PyApplication` come bootstrap automatico. Python/Chaquopy viene avviato esplicitamente in `MainActivity` dentro un blocco di protezione.

Se Python, SQLite, il bridge o USB causano un errore durante l'avvio, l'app resta aperta e mostra lo stack trace sullo schermo.

Passi di test:
1. Compilare l'APK con GitHub Actions.
2. Installarlo sopra la V0.1 (o disinstallare la V0.1 e installare pulito).
3. Avviare l'app.
4. Se compare `Errore di avvio`, fare uno screenshot completo del testo.

Questo permette di identificare esattamente il modulo responsabile senza usare ADB/logcat.
