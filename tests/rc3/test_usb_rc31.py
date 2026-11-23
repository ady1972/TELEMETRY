"""Verify USB package compatibility across the two published firmware revisions."""

from hashlib import md5, sha256
from io import BytesIO
import json
from pathlib import Path
from struct import pack
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, call, patch

import esptool
from esptool import cmds

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "windows/v5.4.15.18-burst4"))
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
            "RC3.2": bytes(header) + b"battery",
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

    @staticmethod
    def boot_data(first=None, second=None):
        data = bytearray(b"\xff" * 0x2000)
        for offset, record in ((0, first), (0x1000, second)):
            if record is not None:
                sequence, state, checksum = record
                data[offset:offset + 32] = pack("<I", sequence) + b"\xff" * 20 + pack("<II", state, checksum)
        return bytes(data)

    def connect_simulated_guition(self, ota_data=None):
        self.assertEqual(esptool.__version__, "4.14.0")
        table = b"Guition partition table"
        header = self.images["RC3.1"][:112]
        project, capacity, _ = usb.MODELS[self.model]
        self.enterContext(patch.dict(usb.MODELS, {
            self.model: (project, capacity, sha256(table).hexdigest()),
        }))
        loader = Mock(CHIP_NAME="ESP32-S3", IS_STUB=True, secure_download_mode=False)
        loader.read_flash.side_effect = [table, ota_data if ota_data is not None else self.boot_data(), header]
        loader.flash_md5sum.return_value = "0" * 32
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
        self.verify_write(self.boot_data(), 0x10000)

    def test_updates_slot_zero_when_bootloader_initialized_its_selector(self):
        self.verify_write(self.boot_data((1, 2, 0x4743989A)), 0x10000)

    def test_updates_slot_one_when_its_selector_is_newer(self):
        self.verify_write(self.boot_data((1, 2, 0x4743989A), (2, 0xFFFFFFFF, 0x55F63774)), 0x1D0000)

    def verify_write(self, ota_data, app_address):
        transport, rom, loader = self.connect_simulated_guition(ota_data)
        image = self.images["RC3.1"]
        manifest = self.directory / "fixture.json"
        manifest.write_bytes(self.make_manifest("RC3.1", image))
        manifest.with_suffix(".bin").write_bytes(image)

        def record_write(esp, args):
            self.assertIs(esp, loader)
            self.assertTrue(args.compress)
            ((offset, stream),) = args.addr_filename
            self.assertEqual(offset, app_address)
            self.assertEqual(stream.read(), image)

        with patch.object(esptool, "write_flash", record_write):
            usb.update_firmware(self.model, manifest, "COM9")
        transport.connect.assert_called_once_with("no_reset", 2, detecting=True)
        rom.run_stub.assert_called_once_with()
        loader.run_stub.assert_not_called()
        loader.hard_reset.assert_called_once_with()
        rom.__exit__.assert_called_once()
        self.assertEqual(loader.read_flash.call_args_list, [
            call(0x8000, 0xC00), call(0x9000, 0x2000), call(app_address, 112),
        ])
        loader.flash_md5sum.assert_called_once_with(app_address, len(image))

    def test_matching_firmware_is_detected_before_any_write(self):
        _, _, loader = self.connect_simulated_guition(self.boot_data((2, 2, 0x55F63774)))
        manifest = self.directory / "firmware.json"
        image = self.images["RC3.1"]
        manifest.write_bytes(self.make_manifest("RC3.1", image))
        manifest.with_suffix(".bin").write_bytes(image)
        loader.flash_md5sum.return_value = md5(image, usedforsecurity=False).hexdigest()
        with patch.object(usb, "esptool_main") as write:
            self.assertFalse(usb.update_firmware(self.model, manifest, "COM9"))
        loader.flash_md5sum.assert_called_once_with(0x1D0000, len(image))
        loader.soft_reset.assert_called_once_with(stay_in_bootloader=True)
        write.assert_not_called()

    def test_compare_command_reads_the_active_firmware_without_writing(self):
        _, _, loader = self.connect_simulated_guition(self.boot_data((1, 2, 0x4743989A)))
        manifest = self.directory / "firmware.json"
        image = self.images["RC3.1"]
        manifest.write_bytes(self.make_manifest("RC3.1", image))
        manifest.with_suffix(".bin").write_bytes(image)
        loader.flash_md5sum.return_value = md5(image, usedforsecurity=False).hexdigest()
        with patch.object(usb, "esptool_main") as write:
            self.assertEqual(usb.check_installed_firmware(self.model, manifest, "COM9"), "same")
        loader.flash_md5sum.assert_called_once_with(0x10000, len(image))
        loader.soft_reset.assert_called_once_with(stay_in_bootloader=True)
        write.assert_not_called()


    def test_comparison_distinguishes_upgrade_downgrade_and_unknown(self):
        catalog = {
            version: (len(image), md5(image, usedforsecurity=False).hexdigest())
            for version, image in self.images.items()
        }
        self.enterContext(patch.dict(usb.INSTALLED_FINGERPRINTS, {self.model: catalog}))
        for current, selected, expected in (
            ("RC3", "RC3.1", "newer"), ("RC3.1", "RC3", "older"), (None, "RC3.1", "different"),
        ):
            with self.subTest(current=current, selected=selected):
                _, _, loader = self.connect_simulated_guition()
                loader.flash_md5sum.side_effect = lambda offset, size: (
                    catalog[current][1] if current and size == catalog[current][0] else "0" * 32
                )
                manifest = self.directory / "firmware.json"
                image = self.images[selected]
                manifest.write_bytes(self.make_manifest(selected, image))
                manifest.with_suffix(".bin").write_bytes(image)
                self.assertEqual(usb.check_installed_firmware(self.model, manifest, "COM9"), expected)

    def test_restart_revalidates_model_and_resets_without_writing(self):
        transport, _, loader = self.connect_simulated_guition()
        with patch.object(usb, "esptool_main") as write:
            usb.restart_laptimer(self.model, "COM9")
        transport.connect.assert_called_once_with("no_reset", 2, detecting=True)
        loader.hard_reset.assert_called_once_with()
        loader.flash_md5sum.assert_not_called()
        write.assert_not_called()

    def test_rejects_corrupt_or_pending_selector_before_writing(self):
        for selector in ((1, 2, 0), (1, 1, 0x4743989A)):
            with self.subTest(selector=selector):
                with patch.object(usb, "connect_bootloader") as connect, patch.object(usb, "esptool_main") as write:
                    rom = connect.return_value.__enter__.return_value
                    rom.CHIP_NAME = "ESP32-S3"
                    rom.secure_download_mode = False
                    loader = rom.run_stub.return_value
                    table = b"Guition partition table"
                    loader.read_flash.side_effect = [table, self.boot_data(selector)]
                    manifest = self.directory / "fixture.json"
                    image = self.images["RC3.1"]
                    manifest.write_bytes(self.make_manifest("RC3.1", image))
                    manifest.with_suffix(".bin").write_bytes(image)
                    project, capacity, _ = usb.MODELS[self.model]
                    with patch.dict(usb.MODELS, {self.model: (project, capacity, sha256(table).hexdigest())}):
                        with self.assertRaisesRegex(ValueError, "slot di avvio"):
                            usb.update_firmware(self.model, manifest, "COM9")
                    write.assert_not_called()

    def test_ignores_rejected_or_bad_crc_copy_when_other_copy_is_valid(self):
        for ignored in ((2, 4, 0x55F63774), (2, 2, 0)):
            with self.subTest(selector=ignored):
                self.assertEqual(usb.selected_boot_slot(self.boot_data((1, 2, 0x4743989A), ignored)), 0)

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
        version = usb.DOWNLOAD_VERSIONS[self.model]
        image = self.images[version]
        with patch.object(usb, "urlopen", side_effect=[
            BytesIO(self.make_manifest(version, image)), BytesIO(image),
        ]) as fetch:
            package = usb.download_package(self.model, self.directory)
        suffix = f"/main/firmware/guition-43/usb/GOATS-{self.model}-RC3.2"
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
