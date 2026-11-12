# Test del porting Guition V1.0.22

Dalla root del repository, con Python e G++/Clang:

```sh
python tests/guition_port/check_invariants.py
python tests/guition_port/prepare_host.py /tmp/port-host
g++ -std=c++17 -Wall -Wextra -Wno-misleading-indentation -I /tmp/port-host -I tests/guition_port/stubs -I firmware/guition-43/goats_guition_43_v1_0_22_rlcd26_usb tests/guition_port/test_port.cpp -o /tmp/test_port
/tmp/test_port
```

prepare_host sostituisce soltanto l'adapter SD negli header di sessione copiati
in /tmp e rinomina i tipi del lettore originale per poter includere entrambe
le versioni nello stesso test. La logica di sessione, il codec GSE, la coda e
il diario NVS testati sono quelli effettivi del firmware. NVS e filesystem
sono sostituiti da adapter in RAM; gli eventi del motore sono simulati.
La prova non simula l'hardware o l'accuratezza dell'algoritmo GNSS, il cui
header resta identico byte per byte e viene controllato dagli invarianti.

Copertura: FIFO piena/wrap, settimana iTOW, duplicati, CRC GSE, 250 campioni
distinti con intervallo 40 ms, nessun I/O nell'update per campione, attribuzione
del passaggio al nuovo giro, lettura GSA3 con il codice V1.0.20, riapertura con
settori, recupero giri senza SD, scarto. Il workflow esegue anche ESPHome compile.
