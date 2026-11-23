"""Update GOATS firmware through the ESP32-S3 ROM loader."""

from hashlib import sha256
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory, mkdtemp
from urllib.request import urlopen

from esptool import FatalError, detect_chip, main as esptool_main
from serial.tools.list_ports import comports


MODELS = {
    "GUITION_43": (
        b"goats-rt-laptimer-v2", 0x1C0000,
        "45e2c4086233cc7a1167262b7ad6d44288e6b131e7b7f0061ddd2438997b807d",
    ),
    "RLCD_MONO_42": (
        b"goats-rlcd-mg902-rc2", 0x7C0000,
        "1a0727f7935aff03694457fb7f5c76e289a7b0f71017b8c649e4ae9e4034028f",
    ),
}
DOWNLOAD_VERSION = "RC3.1"
APPROVED_IMAGES = {
    "GUITION_43": {
        "RC3": "ef1da62b21a7b68d95caa2395d099e3b75539eb0297ae82f459aba74857e66b5",
        "RC3.1": "bac17785f949e09a59aa6809f513eda4cef15c0952432c53d8aa0270719ea707",
    },
    "RLCD_MONO_42": {
        "RC3": "851bdc7f6af2be034501816497970acbe9b261c2d5b9a2416e7718ef63957cf3",
        "RC3.1": "fada0dbe2714783268e1938c3b8397c67f0d2d2e3cb0a56fc8ca1227e9fcf921",
    },
}
PACKAGE_ROOT = "https://raw.githubusercontent.com/ady1972/TELEMETRY/rc3-usb-packages"
APP_OFFSET = 0x10000
TABLE_OFFSET = 0x8000
TABLE_LENGTH = 0xC00
OTA_DATA_OFFSET = 0x9000
OTA_DATA_LENGTH = 0x2000
ESPRESSIF_USB_SERIAL_JTAG = (0x303A, 0x1001)


def validate_image(model, image):
    project, slot_limit, _ = MODELS[model]
    if (len(image) < 112 or len(image) > slot_limit
            or image[0] != 0xE9
            or image[12:14] != b"\x09\x00"
            or image[32:36] != b"\x32\x54\xcd\xab"
            or image[80:112].split(b"\0", 1)[0] != project):
        raise ValueError("Immagine applicativa ESP32-S3 incompatibile con il modello.")


def load_firmware(model, manifest_path):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("model") != model:
        raise ValueError("Il manifesto deve indicare il modello rilevato.")
    version = manifest.get("version")
    approved = APPROVED_IMAGES[model]
    if not isinstance(version, str) or version not in approved:
        raise ValueError("La versione indicata nel manifesto non è supportata.")
    image_path = manifest_path.with_suffix(".bin")
    size = image_path.stat().st_size
    if not 112 <= size <= MODELS[model][1]:
        raise ValueError("Dimensione del file firmware fuori dai limiti dello slot.")
    image = image_path.read_bytes()
    validate_image(model, image)
    digest = sha256(image).hexdigest()
    if manifest.get("size") != len(image) or manifest.get("sha256") != digest:
        raise ValueError("Dimensione o SHA-256 del firmware differente dal manifesto.")
    if digest != approved[version]:
        raise ValueError(f"SHA-256 diverso dal firmware {version} pubblicato per questo modello.")
    return version, image


def model_from_loader(loader):
    table = loader.read_flash(TABLE_OFFSET, TABLE_LENGTH)
    fingerprint = sha256(table).hexdigest()
    for model, (project, _, expected_table) in MODELS.items():
        if fingerprint != expected_table:
            continue
        header = loader.read_flash(APP_OFFSET, 112)
        if header[32:36] == b"\x32\x54\xcd\xab" and header[80:112].split(b"\0", 1)[0] != project:
            raise ValueError("La tabella e l'identità dell'applicazione indicano modelli diversi.")
        return model
    raise ValueError("Il dispositivo USB non ha un layout GOATS RC3 riconosciuto.")


def check_device(device):
    if device.CHIP_NAME != "ESP32-S3" or device.secure_download_mode:
        raise ValueError("Serve un ESP32-S3 in modalità BOOT con lettura flash abilitata.")


def supports_usb_reset(device):
    return (device.vid, device.pid) == ESPRESSIF_USB_SERIAL_JTAG


def connect_bootloader(port, *, allow_usb_reset=False):
    for mode in ("no_reset", "usb_reset"):
        if mode == "usb_reset":
            if not allow_usb_reset or not any(
                device.device == port and supports_usb_reset(device) for device in comports()
            ):
                break
            print(f"Avvio in modalità BOOT via USB su {port}…", flush=True)
        try:
            return detect_chip(port, connect_mode=mode, connect_attempts=2)
        except FatalError as error:
            if not str(error).startswith("Failed to connect to "):
                raise
            connection_error = error

    raise ValueError(
        f"Il bootloader non risponde su {port}. Metti il laptimer in modalità BOOT, "
        "aggiorna l’elenco delle porte e seleziona di nuovo la sua COM.\n"
        f"{str(connection_error).splitlines()[0]}"
    ) from connection_error


def detect_model(port, *, allow_usb_reset=False):
    with connect_bootloader(port, allow_usb_reset=allow_usb_reset) as device:
        check_device(device)
        loader = device.run_stub()
        try:
            return model_from_loader(loader)
        finally:
            loader.soft_reset(stay_in_bootloader=True)


def download_package(model, cache):
    _, slot_limit, _ = MODELS[model]
    name = f"GOATS-{model}-{DOWNLOAD_VERSION}"
    cache.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="goats-download-") as scratch:
        directory = Path(scratch)
        for extension, limit in (("json", 4096), ("bin", slot_limit)):
            filename = f"{name}.{extension}"
            with urlopen(f"{PACKAGE_ROOT}/{filename}", timeout=30) as response:
                content = response.read(limit + 1)
            if not content or len(content) > limit:
                raise ValueError("Dimensione del download fuori dai limiti.")
            (directory / filename).write_bytes(content)
        manifest = directory / f"{name}.json"
        version, image = load_firmware(model, manifest)
        if version != DOWNLOAD_VERSION:
            raise ValueError(f"Il pacchetto GitHub deve contenere il firmware {DOWNLOAD_VERSION}.")
        destination = Path(mkdtemp(prefix=f"{model}-", dir=cache))
        target = destination / manifest.name
        target.with_suffix(".bin").write_bytes(image)
        target.write_bytes(manifest.read_bytes())
        return target


def update_firmware(model, manifest_path, port):
    version, image = load_firmware(model, manifest_path)
    with TemporaryDirectory(prefix="goats-firmware-") as scratch:
        firmware = Path(scratch) / "application.bin"
        firmware.write_bytes(image)
        with connect_bootloader(port, allow_usb_reset=True) as device:
            check_device(device)
            loader = device.run_stub()
            print("Controllo partizioni del dispositivo USB…", flush=True)
            if model_from_loader(loader) != model:
                raise ValueError("Dispositivo diverso da quello richiesto dal pacchetto.")
            ota_data = loader.read_flash(OTA_DATA_OFFSET, OTA_DATA_LENGTH)
            if ota_data != b"\xff" * OTA_DATA_LENGTH:
                raise ValueError("Selezione slot diversa dalla configurazione USB prevista.")
            print("Scrittura e verifica dell'immagine applicativa…", flush=True)
            # The active stub already read the partition table on this connection.
            esptool_main([
                "--chip", "esp32s3", "--port", port, "--before", "no_reset",
                "--no-stub", "--after", "hard_reset", "write_flash", "--compress",
                hex(APP_OFFSET), str(firmware),
            ], esp=loader)
    print(f"Scrittura verificata. Controlla l'indicazione {version} sul display.", flush=True)


if __name__ == "__main__":
    try:
        action, *args = sys.argv[1:]
        if action in ("detect", "detect_usb_boot"):
            model = detect_model(args[0], allow_usb_reset=(action == "detect_usb_boot"))
            print(f"GOATS_MODEL={model}", flush=True)
        elif action == "download":
            print(f"GOATS_PACKAGE={download_package(args[0], Path(args[1]))}", flush=True)
        elif action == "update":
            update_firmware(args[0], Path(args[1]), args[2])
        else:
            raise ValueError("Azione firmware sconosciuta.")
    except (OSError, ValueError, KeyError, FatalError) as exc:
        print(f"Aggiornamento USB interrotto: {exc}", file=sys.stderr, flush=True)
        raise SystemExit(1)
