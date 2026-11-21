# ESP32-S3-Zero — TEST ALIMENTAZIONE 01

Variante da banco per [issue #33](https://github.com/ady1972/TELEMETRY/issues/33),
derivata dal branch `codex/rlcd-42-tricolore-v0405`.
Non è un firmware di cronometraggio. Le versioni da pista restano intatte.

## Scheda e firmware

- ESP32-S3-Zero, **flash 4 MB**, senza PSRAM richiesta o abilitata.
  Il profilo PlatformIO `esp32-s3-devkitc-1` identifica il chip; la dimensione
  è esplicitamente sovrascritta a 4 MB. Controllare la variante reale della Zero.
- ESPHome **2026.7.3**, framework ESP-IDF 5.5.5.
- ST7306 Osptek rosso/nero/bianco, SPI mode 0 a 4 MHz.
- Sequenza comandi, impulso RESET di 200 ms, rotazione e packing RBW estratti
  dalla V0.40.5 originale. Font bitmap locale copiato senza modifiche.
- Schermata immediata dopo il reset e l'inizializzazione LCD (circa 800 ms
  di attese obbligatorie del driver, oltre all'avvio ESP): titolo, campioni dei
  tre colori, secondi grandi e causa dell'ultimo reset con relativo codice ESP-IDF.
- Contatore a zero al primo frame, aggiornato ogni secondo con timer monotono
  a 64 bit; riparte da zero dopo ogni riavvio. Nessun salvataggio persistente.
- Nessuna UART, attesa del fix, microSD, joystick/tasti, sessione, Wi-Fi o OTA.
  Il logger usa solo USB Serial/JTAG e non richiede un PC connesso per proseguire.

Il reset reason è ciò che ESP-IDF riesce a rilevare: `BROWNOUT` è un indizio,
ma l'assenza di questa scritta non esclude una caduta di tensione. Un'interruzione
completa può risultare come semplice accensione. Il programma non misura volt.

## Collegamenti del test

Collegare e scollegare i moduli **solo a USB rimossa**. La Zero è alimentata
dalla sua USB; nessuna alimentazione esterna in parallelo.

| Segnale del modulo | ESP32-S3-Zero |
|---|---|
| LCD VCC / GND | 3V3 / GND |
| LCD CS | GPIO10 |
| LCD DC | GPIO9 |
| LCD RESET / RST | GPIO8 |
| LCD MOSI / DIN / SDA SPI | GPIO11 |
| LCD SCLK / CLK / SCL SPI | GPIO12 |
| LCD TE | Scollegato |
| MG902 VCC, solo prova B | 3V3, **solo se la specifica scheda MG902 accetta 3,3 V su VCC** |
| MG902 GND, solo prova B | GND comune |
| MG902 TX e RX | Entrambi fisicamente scollegati, in entrambe le prove |
| Multimetro, tensione continua | Puntale rosso su 3V3 Zero, nero su GND Zero |

I numeri indicano **GPIO**, non posizioni del connettore. Verificare la serigrafia
del proprio modulo LCD/GPS: DIN e CLK sono segnali SPI, non I2C. Non ricavare
la compatibilità VCC dal solo nome MG902 o dal chip M9N; se non è documentata,
non eseguire la prova B a 3,3 V. Non spostare VCC a 5 V per tentativi.
Per misurare tensione usare i morsetti V/COM del multimetro, non quello corrente.

## Prova A/B con la stessa alimentazione USB

1. **Preparazione:** caricare questo firmware, poi rimuovere USB. Mantenere
   invariati alimentatore/porta USB, cavo, cablaggio del display e multimetro.
2. **A — solo display:** GPS completamente scollegato. Collegare USB per un
   avvio a freddo; annotare tensione fra 3V3 e GND all'avvio e a regime, colori,
   causa reset e continuità del contatore per almeno 60 secondi.
3. **B — display più GPS:** rimuovere USB e attendere lo spegnimento. Dopo aver
   verificato la compatibilità VCC, collegare soltanto MG902 VCC e GND.
   TX/RX restano scollegati. Ricollegare **la stessa USB** e ripetere le misure.
4. Se B fallisce, tornare ad A con un altro avvio a freddo per verificare che
   il comportamento sia ripetibile. Non collegare il GPS a dispositivo acceso.

| Condizione | 3V3 avvio / regime | Conteggio continuo? | Reset reason / riavvii | Note |
|---|---|---|---|---|
| A: solo display | ___ / ___ V | ___ | ___ | ___ |
| B: display + MG902 | ___ / ___ V | ___ | ___ | ___ |
| A ripetuta | ___ / ___ V | ___ | ___ | ___ |

Un'immagine ferma non dimostra che l'ESP32 sia operativo: il segnale utile è
il conteggio che avanza. Il ritorno a zero segnala un nuovo avvio. Display
fermo, display spento e reset sono osservazioni diverse. Il multimetro può
non catturare transitori rapidi; nessuna conclusione sulla corrente massima
del regolatore può essere ricavata dal solo test. Fermare la prova se un
componente si scalda in modo anomalo.

## ESPHome e primo flash USB

Nella cartella ESPHome devono essere affiancati:

```text
goats_s3_zero_test_alimentazione_01.yaml
GOATS_S3_ZERO_TEST_ALIMENTAZIONE_01/
  components/goats_power_test/
  README.md
  ...
```

Aprire lo YAML esterno. Tutte le dipendenze applicative e i font sono locali;
la prima compilazione richiede Internet per ESPHome/ESP-IDF e i tool di build.

```sh
esphome config goats_s3_zero_test_alimentazione_01.yaml
esphome compile goats_s3_zero_test_alimentazione_01.yaml
esphome upload goats_s3_zero_test_alimentazione_01.yaml --device /dev/ttyACM0
```

Sostituire la porta con quella reale, per esempio `COM5` in Windows.
Se necessario tenere premuto BOOT, premere e rilasciare RESET, poi rilasciare
BOOT per entrare nel bootloader USB della Zero. Dopo il flash riavviare.

Per un primo flash manuale usare **firmware.factory.bin a offset 0x0**, che
include bootloader, partizioni e applicazione. `firmware.bin` è la sola app
e non è il file per un primo flash a offset zero. Esempio con esptool 5:

```sh
python -m esptool --chip esp32s3 --port COM5 write-flash 0x0 firmware.factory.bin
```

Questo firmware non offre OTA. Un flash sostituisce il programma presente:
usare la scheda da banco prevista; il progetto completo TEST26 richiede
16 MB e non va caricato sulla Zero da 4 MB senza un porting dedicato.

## Verifica

Vedere `VERIFICA.md` per gli esiti effettivi di controlli, build e pacchetto.
La prova elettrica A/B e la conferma sul display fisico spettano al banco;
la compilazione non dimostra la stabilità del regolatore.
