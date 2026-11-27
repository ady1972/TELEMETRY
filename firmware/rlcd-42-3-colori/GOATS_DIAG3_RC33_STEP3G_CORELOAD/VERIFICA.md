# Verifica STEP3G CORELOAD — 27/11/2026

```sh
esphome compile firmware/rlcd-42-3-colori/goats_42_diag3_rc33_step3g_coreload.yaml
python tests/diag3_rc33_step3g_coreload/differential.py
python tests/diag3_rc33_step3g_coreload/modes.py
python tests/diag3_rc33_step3g_coreload/backend.py
python tests/diag3_rc33_step3g_coreload/run.py
python tests/diag3_rc33_step3g_coreload/check_build.py
```

- Base STEP3F 3398ae6. Parser/configuratore GNSS, pin/baud/25 Hz, backend
  store/USB, record/CSV, renderer/font, LCD e trasferimento a blocchi invariati.
- Sostituiti solo i coseni in tre percorsi con memoizzazione degli stessi
  argomenti double (chiave bit-esatta), senza cambiare formule circostanti,
  scansione AUTO, frequenze o regole. Cache fissa, fallback oltre 50 indici.
- Confronto C++ ASan/UBSan di due build con codice produttivo: STEP3F originale
  e STEP3G; quest'ultima viene eseguita sia con cache off sia on. Parser/core/
  runtime/store reali, modelli SDK per UART/flash/NVS/USB. Ogni passo confronta
  gli stati osservabili, i bit dei float di delta/medie/settori, eventi UI e
  dati CSV. Output byte-identici in tutti e tre gli scenari:

| Scenario | Valutazioni cos OFF -> ON | SHA256 output, prefisso |
|---|---|---|
| 1200 campioni, AUTO su 50 circuiti da fermo | 64933 -> 449 | f088adca779a2ea4 |
| 4200 campioni, piu' giri/settori/tracce/delta | 1039503 -> 9896 | 4f50ad227c69f3f6 |
| 1200 campioni, modifica/riordino/clear/reload catalogo | 62132 -> 548 | 54a0cec0eefcd543 |

- Incluse assenza/perdita fix e duplicati iTOW. Le richieste geometriche restano
  nello stesso numero: si riducono solo le valutazioni della funzione coseno.
  I conteggi non sono benchmark CPU/consumo o misure del pannello.
- Regressioni su tutti e cinque i profili: 50 PVT senza fix +500 con fix a
  25 Hz, dispatcher/observer/REC; backend reale con servizi separati, nessuna
  scrittura al solo fix da fermo, contatori W/ID, 101 punti a 25 Hz.
- Test FULL originale e client reale Windows V5.4.15.20: cataloghi, CRC,
  BURST4/list/download/delete/CSV/recovery/capacita' passati con il core nuovo.
- Renderer/packing/BOOT, frame immutabile, finestra e 30000 byte, 13 blocchi
  <=2400 byte, requester, A/B e wrap millis passati. Modello 63/255ms di invio
  invariato, senza pretesa di benchmark fisico.
- Diagnostica CORE mean/peak misura il solo consumatore PVT in finestre di
  circa 1 s; nei double UART il tempo micros e' deterministico (zero durata),
  i valori reali vanno letti sulla scheda. COS e' rapporto di richieste riusate.
- Preprocessore/ELF: una UART/controller/core privato, Canvas non registrato,
  nessun SD mount/TinyUSB/MSC/setup USB legacy; main FULL, diagnostica iniziale,
  HPM false e core_cache true. Strumentazione e cache collegate.
- ESPHome 2026.7.3 / Arduino 3.3.10 / IDF 5.5.5: compilazione passata,
  app 618199 byte, RAM statica 151895 byte, config_hash 0x5503ee9a.
- Tre YAML aggiuntivi validati; factory compilato dal principale FULL CACHE.
  Il confezionamento controlla CRC ZIP, ogni SHA256 e i quattro YAML estratti.

STEP3G non e' ancora stata provata sul pannello dell'utente. TE rimane aperto
come consentito per il segnale non utilizzato. Non vengono dichiarati risolto
lo sfarfallio, causa identificata o miglioramento percentuale del tempo CPU.
