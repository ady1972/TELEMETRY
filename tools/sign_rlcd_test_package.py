"""Prepare a signed RLCD USB test package from an ESPHome application binary."""

import argparse
from base64 import b64encode
from hashlib import sha256
import json
from pathlib import Path
import sys
from zipfile import ZIP_DEFLATED, ZipFile

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "windows/v5.4.15.20-burst4"))
import goats_firmware_catalog as catalog
import goats_firmware_usb as usb


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version")
    parser.add_argument("image", type=Path)
    parser.add_argument("key", type=Path, help="Path to the private raw Ed25519 key")
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()

    model = catalog.SIGNED_MODEL
    catalog.version_number(args.version)
    image = args.image.read_bytes()
    usb.validate_image(model, image)
    if f"RLCD {args.version}\0".encode() not in image:
        raise ValueError("La versione dello splash non corrisponde al pacchetto.")
    key = Ed25519PrivateKey.from_private_bytes(args.key.read_bytes())
    if key.public_key().public_bytes_raw() != catalog.PUBLIC_KEY:
        raise ValueError("La chiave privata non corrisponde al canale di test del Manager.")

    metadata = dict(model=model, version=args.version, size=len(image), sha256=sha256(image).hexdigest())
    payload = json.dumps(dict(schema=1, **metadata), separators=(",", ":")).encode()
    envelope = json.dumps({
        "payload": b64encode(payload).decode(),
        "signature": b64encode(key.sign(payload)).decode(),
    }, indent=2).encode() + b"\n"
    catalog.verify_catalog(envelope, model, usb.MODELS[model][1], usb.DOWNLOAD_VERSIONS[model])

    stem = f"GOATS-{model}-{args.version}"
    args.destination.mkdir(parents=True, exist_ok=True)
    manifest = args.destination / f"{stem}.json"
    existing_image = manifest.with_suffix(".bin")
    if existing_image.exists() and existing_image.read_bytes() != image:
        raise ValueError("Questa versione esiste già con un binario diverso.")
    manifest.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    existing_image.write_bytes(image)
    sidecar = manifest.with_suffix(".catalog.json")
    sidecar.write_bytes(envelope)
    usb.load_firmware(model, manifest)
    with ZipFile(manifest.with_suffix(".zip"), "w", ZIP_DEFLATED) as package:
        for entry in (manifest, existing_image, sidecar):
            package.write(entry, entry.name)
    (args.destination / f"GOATS-{model}-catalog.json").write_bytes(envelope)


if __name__ == "__main__":
    main()
