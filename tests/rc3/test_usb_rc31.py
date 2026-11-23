"""Verify USB package compatibility across the two published firmware revisions."""

from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, call, patch

import esptool
from esptool import cmds

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "windows/v5.4.15.15-burst4"))
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

    def connect_simulated_guition(self):
        self.assertEqual(esptool.__version__, "4.14.0")
        table = b"Guition partition table"
        header = self.images["RC3.1"][:112]
        project, capacity, _ = usb.MODELS[self.model]
        self.enterContext(patch.dict(usb.MODELS, {
            self.model: (project, capacity, sha256(table).hexdigest()),
        }))
        loader = Mock(CHIP_NAME="ESP32-S3", IS_STUB=True, secure_download_mode=False)
        loader.read_flash.side_effect = [table, header, b"\xff" * usb.OTA_DATA_LENGTH]
        loader.run_stub.side_effect = AssertionError("An active stub must not be uploaded again")
        loader.read_mac.side_effect = lambda kind: (0, 1, 2, 3, 4, 5) if kind == "BASE_MAC" else None
        loader.get_chip_description.return_value = "ESP32-S3"
        loader.get_chip_features.return_value = ["Wi-Fi", "BLE"]
        loader.get_crystal_freq.return_value = 40
        loader.get_usb_mode.return_value = "USB-Serial/JTAG"
        loader.flash_id.return_value = 0x1640EF
        loader.read_spiflash_sfdp.return_value = 0xEF
        rom = Mock(CHIP_NAME="ESP32-S3", secure_download_mode=False)
        rom.get_security_info.return_value = {"parsed_flags": {"SECURE_DOWNLOAD_ENABLE": False}}
        rom.run_stub.return_value = loader
        rom.__enter__ = Mock(return_value=rom)
        rom.__exit__ = Mock(return_value=False)
        rom_type = Mock(USES_MAGIC_VALUE=False, IMAGE_CHIP_ID=9, return_value=rom)
        transport = Mock(serial_port="COM9", sync_stub_detected=False)
        transport.get_chip_id.return_value = 9
        self.enterContext(patch.object(cmds, "ESPLoader", return_value=transport))
        self.enterContext(patch.object(cmds, "ROM_LIST", [rom_type]))
        return transport, rom, loader

    def test_detect_uses_real_esptool_api_and_returns_to_bootloader(self):
        transport, rom, loader = self.connect_simulated_guition()
        self.assertEqual(usb.detect_model("COM9"), self.model)
        transport.connect.assert_called_once_with("no_reset", 2, detecting=True)
        rom.run_stub.assert_called_once_with()
        loader.soft_reset.assert_called_once_with(stay_in_bootloader=True)
        rom.__exit__.assert_called_once()

    def test_native_usb_reset_follows_a_failed_passive_probe(self):
        transport, _, loader = self.connect_simulated_guition()
        transport.connect.side_effect = [
            esptool.FatalError("Failed to connect to Espressif device: No serial data received."),
            None,
        ]
        native = SimpleNamespace(device="COM9", vid=0x303A, pid=0x1001)
        with patch.object(usb, "comports", return_value=[native]):
            self.assertEqual(usb.detect_model("COM9", allow_usb_reset=True), self.model)
        self.assertEqual(transport.connect.call_args_list, [
            call("no_reset", 2, detecting=True), call("usb_reset", 2, detecting=True),
        ])
        loader.soft_reset.assert_called_once_with(stay_in_bootloader=True)

    def test_failed_probe_on_other_usb_port_is_not_reset(self):
        transport, _, _ = self.connect_simulated_guition()
        transport.connect.side_effect = esptool.FatalError(
            "Failed to connect to Espressif device: No serial data received."
        )
        other = SimpleNamespace(device="COM9", vid=0x10C4, pid=0xEA60)
        native = SimpleNamespace(device="COM10", vid=0x303A, pid=0x1001)
        with patch.object(usb, "comports", return_value=[other, native]):
            with self.assertRaisesRegex(ValueError, "bootloader non risponde su COM9"):
                usb.detect_model("COM9", allow_usb_reset=True)
        transport.connect.assert_called_once_with("no_reset", 2, detecting=True)

    def test_passive_probe_requires_consent_before_any_usb_reset(self):
        transport, _, _ = self.connect_simulated_guition()
        transport.connect.side_effect = esptool.FatalError(
            "Failed to connect to Espressif device: No serial data received."
        )
        with patch.object(usb, "comports") as ports:
            with self.assertRaisesRegex(ValueError, "modalità BOOT"):
                usb.detect_model("COM9")
        transport.connect.assert_called_once_with("no_reset", 2, detecting=True)
        ports.assert_not_called()

    def test_update_uses_real_esptool_parser_with_existing_stub(self):
        transport, rom, loader = self.connect_simulated_guition()
        image = self.images["RC3.1"]
        manifest = self.directory / "fixture.json"
        manifest.write_bytes(self.make_manifest("RC3.1", image))
        manifest.with_suffix(".bin").write_bytes(image)

        def record_write(esp, args):
            self.assertIs(esp, loader)
            self.assertTrue(args.compress)
            ((offset, stream),) = args.addr_filename
            self.assertEqual(offset, usb.APP_OFFSET)
            self.assertEqual(stream.read(), image)

        with patch.object(esptool, "write_flash", record_write):
            usb.update_firmware(self.model, manifest, "COM9")
        transport.connect.assert_called_once_with("no_reset", 2, detecting=True)
        rom.run_stub.assert_called_once_with()
        loader.run_stub.assert_not_called()
        loader.hard_reset.assert_called_once_with()
        rom.__exit__.assert_called_once()

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
