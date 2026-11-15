# V0.1.3 SQLITE FIX BOOT

Questa build avvia una Activity Android classica, senza Compose/Python/USB.

1. Avvia l'app: deve restare aperta sulla schermata SAFE BOOT.
2. Premi `1 • TEST PYTHON`.
   - Se resta aperta e mostra `PYTHON OK`, il runtime Python è sano.
   - Se il processo si chiude, riapri l'app: `Ultimo stage` identifica il punto del crash nativo.
3. Premi `2 • APRI MANAGER COMPLETO`.
   - Se il Manager si chiude, riapri l'app: la schermata SAFE mostra l'ultimo stage e, per crash Java/Kotlin, lo stack trace completo.
4. Usa `COPIA DIAGNOSTICA` per copiare il report.
