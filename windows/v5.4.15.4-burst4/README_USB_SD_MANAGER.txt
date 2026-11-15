GOATS RT Manager V5.4.10.4 - USB SD DAL MANAGER

Version unchanged: V5.4.10.4.

Sessioni USB now includes ATTIVA USB SD.

Flow:
1. Select laptimer COM port.
2. Press ATTIVA USB SD.
3. Manager sends USB_SD_MODE.
4. Firmware replies USB_SD_ACK and switches from COM to USB Mass Storage.
5. Manager waits up to 20 seconds for a Windows drive containing GOATS.
6. Manager opens the GOATS folder and lets you select one or more CSV sessions.
7. Selected CSVs are imported directly into the shared SQLite database.
8. Use Windows safe eject.
9. Press RIAVVIA on the laptimer.

Compatible firmware:
GOATS RT V11.0.1.40 with goats_v11_0_1_40_usb_sd.yaml.

CSV parsing, Qt Windows fix and Analysis CSV fixes are retained.
