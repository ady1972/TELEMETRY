GOATS RT Manager V5.4.9.7

FIX launcher PowerShell:
La V5.4.9.6 poteva fermarsi durante il semplice test delle dipendenze perché
PowerShell trasformava l'output STDERR del processo Python in NativeCommandError.

V5.4.9.7:
- i test silenziosi di Python/dipendenze vengono eseguiti tramite cmd.exe;
- il normale ModuleNotFoundError durante la verifica non interrompe più lo script;
- se PySide6 manca, il launcher continua e passa all'installazione automatica;
- ambiente locale .goats_venv invariato;
- diagnostica aggiornata.

IMPORTANTE:
Per un test pulito puoi semplicemente estrarre questa versione in una NUOVA
cartella. Non serve installare PySide6 manualmente.
