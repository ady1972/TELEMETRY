"""Verify USB package compatibility across the two published firmware revisions."""

from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "windows/v5.4.15.13-burst4"))
import goats_firmware_usb as usb


class FirmwareVersionTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(self.enterContext(TemporaryDirectory()))
        self.model = "GUITION_43"
        project = usb.MODELS[self.model][0]
        header = bytearray(112)
        header[0] = 0xE9
        header[12:14] = bytes.fromhex("0900")
        header[32:36] = bytes.fromhex("3254cdab")
        header[80:80 + len(project)] = project
        self.images = {
            "RC3": bytes(header) + b"legacy",
            "RC3.1": bytes(header) + b"new",
        }
        self.enterContext(patch.dict(usb.APPROVED_IMAGES, {
            self.model: {version: sha256(image).hexdigest() for version, image in self.images.items()},
        }))

    def make_manifest(self, version, image):
        return json.dumps({
            "model": self.model,
            "version": version,
            "size": len(image),
            "sha256": sha256(image).hexdigest(),
        }).encode()

    def test_accepts_both_official_versions_offline(self):
        for version, image in self.images.items():
            with self.subTest(version=version):
                manifest = self.directory / f"fixture-{version}.json"
                manifest.write_bytes(self.make_manifest(version, image))
                manifest.with_suffix(".bin").write_bytes(image)
                self.assertEqual(usb.load_firmware(self.model, manifest), (version, image))

    def test_rejects_older_binary_relabelled_as_rc31(self):
        image = self.images["RC3"]
        manifest = self.directory / "fixture.json"
        manifest.write_bytes(self.make_manifest("RC3.1", image))
        manifest.with_suffix(".bin").write_bytes(image)
        with self.assertRaisesRegex(ValueError, "pubblicato"):
            usb.load_firmware(self.model, manifest)

    def test_download_uses_the_release_for_the_detected_model(self):
        version = usb.DOWNLOAD_VERSION
        image = self.images[version]
        with patch.object(usb, "urlopen", side_effect=[
            BytesIO(self.make_manifest(version, image)), BytesIO(image),
        ]) as fetch:
            package = usb.download_package(self.model, self.directory)
        suffix = f"/GOATS-{self.model}-RC3.1"
        self.assertTrue(fetch.call_args_list[0].args[0].endswith(f"{suffix}.json"))
        self.assertTrue(fetch.call_args_list[1].args[0].endswith(f"{suffix}.bin"))
        self.assertEqual(usb.load_firmware(self.model, package), (version, image))

    def test_online_package_cannot_downgrade_to_rc3(self):
        image = self.images["RC3"]
        with patch.object(usb, "urlopen", side_effect=[
            BytesIO(self.make_manifest("RC3", image)), BytesIO(image),
        ]):
            with self.assertRaisesRegex(ValueError, "pacchetto GitHub"):
                usb.download_package(self.model, self.directory)


if __name__ == "__main__":
    unittest.main()
