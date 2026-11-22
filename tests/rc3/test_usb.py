import hashlib
import io
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "windows/v5.4.15.12-burst4"))
import goats_firmware_usb as usb


class FirmwareUsbTests(unittest.TestCase):
    def setUp(self):
        scratch = self.enterContext(TemporaryDirectory())
        self.manifest = Path(scratch) / "firmware.json"
        self.table = b"goats partition table fixture"
        self.model = "GUITION_43"
        project, limit, _ = usb.MODELS[self.model]
        self.enterContext(patch.dict(usb.MODELS, {
            self.model: (project, limit, hashlib.sha256(self.table).hexdigest()),
        }))
        image = bytearray(112)
        image[0] = 0xE9
        image[12:14] = b"\x09\x00"
        image[32:36] = b"\x32\x54\xcd\xab"
        image[80:80 + len(project)] = project
        self.image = bytes(image)
        self.manifest.with_suffix(".bin").write_bytes(self.image)
        self.enterContext(patch.dict(usb.APPROVED_IMAGES, {
            self.model: hashlib.sha256(self.image).hexdigest(),
        }))
        self.manifest.write_text(json.dumps({
            "model": self.model,
            "version": "RC3",
            "size": len(self.image),
            "sha256": hashlib.sha256(self.image).hexdigest(),
        }))
        self.loader = Mock()
        self.loader.read_flash.side_effect = [
            self.table, self.image, b"\xff" * usb.OTA_DATA_LENGTH,
        ]
        device = Mock(CHIP_NAME="ESP32-S3", secure_download_mode=False)
        device.run_stub.return_value = self.loader
        connected = self.enterContext(patch.object(usb, "detect_chip"))
        connected.return_value.__enter__.return_value = device
        self.writer = self.enterContext(patch.object(usb, "esptool_main"))

    def test_detects_model_from_device(self):
        self.assertEqual(usb.detect_model("COM9"), self.model)
        self.writer.assert_not_called()

    def test_writes_only_verified_app_on_same_connection(self):
        usb.update_firmware(self.model, self.manifest, "COM9")
        self.writer.assert_called_once()
        cli_args, = self.writer.call_args.args
        self.assertEqual(cli_args[-3:-1], ["write_flash", "0x10000"])
        self.assertIs(self.writer.call_args.kwargs["esp"], self.loader)

    def test_rejects_wrong_layout_before_write(self):
        self.loader.read_flash.side_effect = [b"other table"]
        with self.assertRaisesRegex(ValueError, "layout"):
            usb.update_firmware(self.model, self.manifest, "COM9")
        self.writer.assert_not_called()

    def test_rejects_nondefault_slot_before_write(self):
        self.loader.read_flash.side_effect = [
            self.table, self.image, b"\0" * usb.OTA_DATA_LENGTH,
        ]
        with self.assertRaisesRegex(ValueError, "slot"):
            usb.update_firmware(self.model, self.manifest, "COM9")
        self.writer.assert_not_called()

    def test_rejects_modified_image_before_write(self):
        self.manifest.with_suffix(".bin").write_bytes(self.image + b"changed")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            usb.update_firmware(self.model, self.manifest, "COM9")
        self.writer.assert_not_called()

    def test_rejects_manifest_for_an_unpublished_image(self):
        changed = self.image + b"changed"
        self.manifest.with_suffix(".bin").write_bytes(changed)
        manifest = json.loads(self.manifest.read_text())
        manifest.update(size=len(changed), sha256=hashlib.sha256(changed).hexdigest())
        self.manifest.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "pubblicato"):
            usb.update_firmware(self.model, self.manifest, "COM9")
        self.writer.assert_not_called()

    def test_downloads_and_checks_both_files(self):
        bin_file = self.manifest.with_suffix(".bin")
        with patch.object(usb, "urlopen", side_effect=[
            io.BytesIO(self.manifest.read_bytes()), io.BytesIO(bin_file.read_bytes()),
        ]) as fetch:
            result = usb.download_package(self.model, self.manifest.parent / "cache")
        self.assertEqual(usb.load_firmware(self.model, result), self.image)
        self.assertTrue(fetch.call_args_list[0].args[0].endswith(f"{self.model}-RC3.json"))
        self.assertTrue(fetch.call_args_list[1].args[0].endswith(f"{self.model}-RC3.bin"))


if __name__ == "__main__":
    unittest.main()
