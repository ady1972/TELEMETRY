"""Update GOATS firmware through the ESP32-S3 ROM loader."""

from binascii import crc32
from hashlib import md5, sha256
import json
from pathlib import Path
from struct import Struct
import sys
from tempfile import TemporaryDirectory, mkdtemp
from urllib.request import urlopen

import goats_firmware_catalog as catalog

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
DOWNLOAD_VERSIONS = {"GUITION_43": "RC3.2", "RLCD_MONO_42": "RC3.3"}
APPROVED_IMAGES = {
    "GUITION_43": {
        "RC3": "ef1da62b21a7b68d95caa2395d099e3b75539eb0297ae82f459aba74857e66b5",
        "RC3.1": "bac17785f949e09a59aa6809f513eda4cef15c0952432c53d8aa0270719ea707",
        "RC3.2": "4e560f2278d68dab84e4ae66298f12d33ff47e546f127ddbb18c19af5982dd80",
    },
    "RLCD_MONO_42": {
        "RC3": "851bdc7f6af2be034501816497970acbe9b261c2d5b9a2416e7718ef63957cf3",
        "RC3.1": "fada0dbe2714783268e1938c3b8397c67f0d2d2e3cb0a56fc8ca1227e9fcf921",
        "RC3.2": "e395e9dcef09ad479758d194a5a4849c1f15b4db55c257242ea3b0106d5876bb",
    },
}
# Checksums of the approved releases for identification in the active slot.
INSTALLED_FINGERPRINTS = {
    "GUITION_43": {
        "RC3": (1089728, "0a7faa0a30a48a4a7de3b72c3d77c5d8"),
        "RC3.1": (1089760, "e3c0eb6e8f3db5469f3099e1ba01e85f"),
        "RC3.2": (1089840, "774a5981269ff7439398c7d15b04c3bc"),
    },
    "RLCD_MONO_42": {
        "RC3": (645680, "ed4f688c1e53f16912503199de5f5d50"),
        "RC3.1": (645712, "a3390829e97777ea94f6efb2831d746b"),
        "RC3.2": (646240, "45be370a4e55a6108a3381c81211cbca"),
        "RC3.3": (646448, "62a7735903bc1e5bc070befdd4d4997e"),
    },
}
PACKAGE_ROOT = "https://raw.githubusercontent.com/ady1972/TELEMETRY/rc3-usb-packages"
GUITION_PACKAGE_ROOT = "https://raw.githubusercontent.com/ady1972/TELEMETRY/main/firmware/guition-43/usb"
APP_OFFSET = 0x10000
TABLE_OFFSET = 0x8000
TABLE_LENGTH = 0xC00
OTA_DATA_OFFSET = 0x9000
OTA_DATA_LENGTH = 0x2000
OTA_DATA_SECTOR_SIZE = 0x1000
OTA_SELECTOR = Struct("<I20xII")
OTA_PENDING_STATES = (0, 1)
OTA_CONFIRMED_STATES = (2, 0xFFFFFFFF)
OTA_REJECTED_STATES = (3, 4)
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
    if not isinstance(version, str):
        raise ValueError("La versione indicata nel manifesto non è supportata.")
    expected_digest = approved.get(version)
    if expected_digest is None:
        sidecar = manifest_path.with_suffix(".catalog.json")
        if not catalog.enabled(model) or not sidecar.is_file():
            raise ValueError("La versione indicata nel manifesto non è supportata.")
        with sidecar.open("rb") as stream:
            signed = stream.read(catalog.MAX_CATALOG_BYTES + 1)
        entry = catalog.verify_catalog(signed, model, MODELS[model][1], DOWNLOAD_VERSIONS[model])
        if any(manifest.get(field) != entry[field] for field in ("version", "size", "sha256")):
            raise ValueError("Il manifesto non corrisponde al catalogo firmware firmato.")
        expected_digest = entry["sha256"]
    image_path = manifest_path.with_suffix(".bin")
    size = image_path.stat().st_size
    if not 112 <= size <= MODELS[model][1]:
        raise ValueError("Dimensione del file firmware fuori dai limiti dello slot.")
    image = image_path.read_bytes()
    validate_image(model, image)
    digest = sha256(image).hexdigest()
    if manifest.get("size") != len(image) or manifest.get("sha256") != digest:
        raise ValueError("Dimensione o SHA-256 del firmware differente dal manifesto.")
    if digest != expected_digest:
        raise ValueError(f"SHA-256 diverso dal firmware {version} pubblicato per questo modello.")
    return version, image


def selected_boot_slot(ota_data):
    if len(ota_data) != OTA_DATA_LENGTH:
        raise ValueError("Lettura incompleta dei dati di avvio.")
    if ota_data == b"\xff" * OTA_DATA_LENGTH:
        return 0

    # ESP-IDF stores one 32-byte selector per sector. The CRC covers ota_seq only.
    selectors = []
    for offset in (0, OTA_DATA_SECTOR_SIZE):
        sequence, state, checksum = OTA_SELECTOR.unpack_from(ota_data, offset)
        if sequence in (0, 0xFFFFFFFF) or state in OTA_REJECTED_STATES:
            continue
        if crc32(ota_data[offset:offset + 4], 0xFFFFFFFF) == checksum:
            selectors.append((sequence, state))

    if not selectors:
        raise ValueError("Selezione dello slot di avvio non verificabile.")
    sequence, state = max(selectors, key=lambda selector: selector[0])
    if state in OTA_PENDING_STATES:
        raise ValueError("Lo slot di avvio è in attesa di convalida.")
    if state not in OTA_CONFIRMED_STATES:
        raise ValueError("Stato dello slot di avvio non riconosciuto.")
    return (sequence - 1) % 2


def firmware_target(loader):
    table = loader.read_flash(TABLE_OFFSET, TABLE_LENGTH)
    fingerprint = sha256(table).hexdigest()
    for model, (project, slot_size, expected_table) in MODELS.items():
        if fingerprint != expected_table:
            continue
        slot = selected_boot_slot(loader.read_flash(OTA_DATA_OFFSET, OTA_DATA_LENGTH))
        # Both verified GOATS layouts have two contiguous, equal-size application slots.
        address = APP_OFFSET + slot * slot_size
        header = loader.read_flash(address, 112)
        if len(header) != 112:
            raise ValueError("Lettura incompleta dell’intestazione del firmware installato.")
        if header[32:36] == b"\x32\x54\xcd\xab" and header[80:112].split(b"\0", 1)[0] != project:
            raise ValueError("La tabella e l'identità dell'applicazione indicano modelli diversi.")
        return model, slot, address
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
            return firmware_target(loader)[0]
        finally:
            loader.soft_reset(stay_in_bootloader=True)


def fetch_package_file(url, limit):
    with urlopen(url, timeout=30) as response:
        content = response.read(limit + 1)
    if not content or len(content) > limit:
        raise ValueError("Dimensione del download fuori dai limiti.")
    return content


def download_package(model, cache):
    _, slot_limit, _ = MODELS[model]
    download_version = DOWNLOAD_VERSIONS[model]
    package_root = GUITION_PACKAGE_ROOT if model == "GUITION_43" else PACKAGE_ROOT
    signed = None
    if catalog.enabled(model):
        signed = fetch_package_file(f"{package_root}/GOATS-{model}-catalog.json", catalog.MAX_CATALOG_BYTES)
        entry = catalog.verify_catalog(signed, model, slot_limit, download_version)
        download_version = entry["version"]
    name = f"GOATS-{model}-{download_version}"
    cache.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="goats-download-") as scratch:
        directory = Path(scratch)
        for extension, limit in (("json", 4096), ("bin", slot_limit)):
            filename = f"{name}.{extension}"
            (directory / filename).write_bytes(fetch_package_file(f"{package_root}/{filename}", limit))
        manifest = directory / f"{name}.json"
        if signed is not None:
            metadata = json.loads(manifest.read_bytes())
            if not isinstance(metadata, dict) or any(
                metadata.get(field) != entry[field] for field in ("model", "version", "size", "sha256")
            ):
                raise ValueError("Il manifesto non corrisponde al catalogo firmware firmato.")
            manifest.with_suffix(".catalog.json").write_bytes(signed)
        version, image = load_firmware(model, manifest)
        if version != download_version:
            raise ValueError(f"Il pacchetto GitHub deve contenere il firmware {download_version}.")
        destination = Path(mkdtemp(prefix=f"{model}-", dir=cache))
        target = destination / manifest.name
        target.with_suffix(".bin").write_bytes(image)
        if signed is not None:
            target.with_suffix(".catalog.json").write_bytes(signed)
        target.write_bytes(manifest.read_bytes())
        return target


def verify_target(loader, model):
    detected_model, slot, address = firmware_target(loader)
    if detected_model != model:
        raise ValueError("Dispositivo diverso da quello richiesto dal pacchetto.")
    return slot, address


def matches_installed_image(loader, address, image):
    # esptool can checksum the active image on-device. Approved packages use SHA-256.
    return loader.flash_md5sum(address, len(image)).lower() == md5(image, usedforsecurity=False).hexdigest()


def check_installed_firmware(model, manifest_path, port):
    version, image = load_firmware(model, manifest_path)
    with connect_bootloader(port) as device:
        check_device(device)
        loader = device.run_stub()
        try:
            _, address = verify_target(loader, model)
            if matches_installed_image(loader, address, image):
                return "same"
            target_version = tuple(map(int, version[2:].split(".")))
            for installed_version, (size, checksum) in INSTALLED_FINGERPRINTS[model].items():
                if installed_version != version and loader.flash_md5sum(address, size).lower() == checksum:
                    current_version = tuple(map(int, installed_version[2:].split(".")))
                    return "newer" if target_version > current_version else "older"
            return "different"
        finally:
            loader.soft_reset(stay_in_bootloader=True)


def restart_application(loader):
    if loader.uses_usb_jtag_serial():
        # Clear the bootloader flag before the watchdog resets the chip.
        loader.write_reg(loader.RTC_CNTL_OPTION1_REG, 0, loader.RTC_CNTL_FORCE_DOWNLOAD_BOOT_MASK)
        loader.watchdog_reset()
    else:
        loader.hard_reset()


def restart_laptimer(model, port):
    with connect_bootloader(port) as device:
        check_device(device)
        loader = device.run_stub()
        verify_target(loader, model)
        restart_application(loader)
    print("Riavvio del laptimer richiesto. Attendi il ritorno alla schermata normale.", flush=True)


def update_firmware(model, manifest_path, port):
    version, image = load_firmware(model, manifest_path)
    with connect_bootloader(port, allow_usb_reset=True) as device:
        check_device(device)
        loader = device.run_stub()
        print("Controllo partizioni e firmware installato…", flush=True)
        slot, address = verify_target(loader, model)
        if matches_installed_image(loader, address, image):
            loader.soft_reset(stay_in_bootloader=True)
            print(f"Il firmware {version} è già installato.", flush=True)
            return False

        print(f"Scrittura e verifica del firmware nello slot {slot} (0x{address:x})…", flush=True)
        with TemporaryDirectory(prefix="goats-firmware-") as scratch:
            firmware = Path(scratch) / "application.bin"
            firmware.write_bytes(image)
            # The active stub already read the partition table on this connection.
            esptool_main([
                "--chip", "esp32s3", "--port", port, "--before", "no_reset",
                "--no-stub", "--after", "no_reset_stub", "write_flash", "--compress",
                hex(address), str(firmware),
            ], esp=loader)
        print("Scrittura verificata. Riavvio automatico…", flush=True)
        restart_application(loader)
    print(f"Riavvio richiesto. Controlla l'indicazione {version} sul display.", flush=True)
    return True


if __name__ == "__main__":
    try:
        action, *args = sys.argv[1:]
        if action in ("detect", "detect_usb_boot"):
            model = detect_model(args[0], allow_usb_reset=(action == "detect_usb_boot"))
            print(f"GOATS_MODEL={model}", flush=True)
        elif action == "download":
            print(f"GOATS_PACKAGE={download_package(args[0], Path(args[1]))}", flush=True)
        elif action == "compare":
            comparison = check_installed_firmware(args[0], Path(args[1]), args[2])
            print(f"GOATS_COMPARISON={comparison}", flush=True)
        elif action == "restart":
            restart_laptimer(args[0], args[1])
        elif action == "update":
            written = update_firmware(args[0], Path(args[1]), args[2])
            if not written:
                print("GOATS_COMPARISON=same", flush=True)
        else:
            raise ValueError("Azione firmware sconosciuta.")
    except (OSError, ValueError, KeyError, FatalError) as exc:
        print(f"Aggiornamento USB interrotto: {exc}", file=sys.stderr, flush=True)
        raise SystemExit(1)
