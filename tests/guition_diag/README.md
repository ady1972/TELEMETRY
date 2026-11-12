# Test diagnostica Guition V1.0.21

Verifica invarianti dalla root del repository:

```powershell
python tests/guition_diag/check_invariants.py
```

Test C++ host (GCC/Clang oppure `zig c++`), sempre dalla root:

```text
c++ -std=c++17 -Wall -Wextra -Werror -I tests/guition_diag/stubs -I firmware/guition-43/goats_guition_43_v1_0_21_diag_usb tests/guition_diag/test_diag.cpp -o test_diag
```

Eseguire l'eseguibile risultante. Gli stub sostituiscono solamente orologio e logger;
il test include gli header diagnostici e la coda realmente usati dal firmware.
Copre rollover settimana, duplicati, salti iTOW, overflow FIFO, confini sessione,
soglie SD strette, operazioni annidate, snapshot e inibizione dei riepiloghi.
Non sostituisce compilazione ESP32 o prove hardware.
