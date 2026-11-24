"""Exercise the signed catalog through Manager download and local validation."""

import base64
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "windows/v5.4.15.20-burst4"))
import goats_firmware_catalog as catalog
import goats_firmware_usb as usb


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.model = "RLCD_MONO_42"
        self.key = Ed25519PrivateKey.generate()
        self.enterContext(patch.object(catalog, "PUBLIC_KEY", self.key.public_key().public_bytes_raw()))
        self.cache = Path(self.enterContext(TemporaryDirectory()))
        image = bytearray(128)
        image[0] = 0xE9
        image[12:14] = b"\x09\x00"
        image[32:36] = b"\x32\x54\xcd\xab"
        project = usb.MODELS[self.model][0]
        image[80:80 + len(project)] = project
        self.image = bytes(image)
        self.manifest = dict(model=self.model, version="RC3.4", size=len(image), sha256=sha256(image).hexdigest())

    def signed(self, **changes):
        payload = json.dumps({"schema": 1, **self.manifest, **changes}).encode()
        return json.dumps({
            "payload": base64.b64encode(payload).decode(),
            "signature": base64.b64encode(self.key.sign(payload)).decode(),
        }).encode()

    def test_future_release_download_and_offline_revalidation(self):
        with patch.object(usb, "urlopen", side_effect=[
            BytesIO(self.signed()), BytesIO(json.dumps(self.manifest).encode()), BytesIO(self.image),
        ]) as fetch:
            result = usb.download_package(self.model, self.cache)
        suffixes = ["/GOATS-RLCD_MONO_42-catalog.json",
                    "/GOATS-RLCD_MONO_42-RC3.4.json", "/GOATS-RLCD_MONO_42-RC3.4.bin"]
        for request, suffix in zip(fetch.call_args_list, suffixes, strict=True):
            self.assertTrue(request.args[0].endswith(suffix))
        self.assertEqual(usb.load_firmware(self.model, result), ("RC3.4", self.image))
        result.with_suffix(".bin").write_bytes(self.image[:-1] + b"!")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            usb.load_firmware(self.model, result)
        result.with_suffix(".catalog.json").unlink()
        with self.assertRaisesRegex(ValueError, "non è supportata"):
            usb.load_firmware(self.model, result)

    def test_rejects_tampered_catalog_before_firmware_download(self):
        envelope = json.loads(self.signed())
        envelope["payload"] = base64.b64encode(b"tampered").decode()
        with patch.object(usb, "urlopen", return_value=BytesIO(json.dumps(envelope).encode())) as fetch:
            with self.assertRaisesRegex(ValueError, "Firma"):
                usb.download_package(self.model, self.cache)
            fetch.assert_called_once()

    def test_rejects_wrong_model_and_downgrade(self):
        limit = usb.MODELS[self.model][1]
        for payload in (self.signed(model="GUITION_43"), self.signed(version="RC3.1"),
                        self.signed(version="../other"), self.signed(size=limit + 1)):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                catalog.verify_catalog(payload, self.model, limit, "RC3.2")


if __name__ == "__main__":
    unittest.main()
