"""Exercise the single BOOT button and review of local and downloaded firmware."""

from hashlib import sha256
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from time import monotonic
import unittest
from unittest.mock import patch

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QComboBox, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget
from serial.tools.list_ports_common import ListPortInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "windows/v5.4.15.19-burst4"))
import goats_firmware_usb as usb
import goats_firmware_usb_ui as ui


class FirmwareReviewTests(unittest.TestCase):
    def setUp(self):
        self.app = QApplication.instance() or QApplication([])
        self.directory = Path(self.enterContext(TemporaryDirectory()))
        self.model = "GUITION_43"
        project = usb.MODELS[self.model][0]
        header = bytearray(112)
        header[0] = 0xE9
        header[12:14] = bytes.fromhex("0900")
        header[32:36] = bytes.fromhex("3254cdab")
        header[80:80 + len(project)] = project
        approved = {}
        for version in ("RC3", "RC3.1", "RC3.2"):
            image = bytes(header) + version.encode()
            digest = sha256(image).hexdigest()
            approved[version] = digest
            manifest = self.directory / f"{version}.json"
            manifest.with_suffix(".bin").write_bytes(image)
            manifest.write_text(json.dumps({
                "model": self.model, "version": version, "size": len(image), "sha256": digest,
            }))
        for suffix in (".bin", ".json"):
            (self.directory / f"current{suffix}").write_bytes(
                (self.directory / f"RC3.1{suffix}").read_bytes()
            )
        self.enterContext(patch.dict(usb.APPROVED_IMAGES, {self.model: approved}))
        self.script = self.directory / "goats_firmware_usb.py"
        self.script.write_text(f'''
from pathlib import Path
import sys
action, *args = sys.argv[1:]
if action == "detect_usb_boot":
    assert args == ["COM9"]
    print("GOATS_MODEL={self.model}")
elif action == "detect":
    assert args == ["COM10"]
    print("GOATS_MODEL={self.model}")
elif action == "download":
    assert args[0] == "{self.model}"
    print("GOATS_PACKAGE=" + str(Path(__file__).with_name("RC3.2.json")))
elif action == "compare":
    assert args[0] == "{self.model}"
    result = {{"RC3": "older", "RC3.2": "newer", "current": "same"}}[Path(args[1]).stem]
    print("GOATS_COMPARISON=" + result)
elif action == "restart":
    assert args == ["{self.model}", "COM10"]
    print("Riavvio richiesto")
else:
    raise AssertionError(action)
''')
        native = ListPortInfo("COM9")
        native.vid, native.pid = 0x303A, 0x1001
        bridge = ListPortInfo("COM10")
        bridge.vid, bridge.pid = 0x10C4, 0xEA60
        self.enterContext(patch.object(ui, "__file__", str(self.script.with_name("ui.py"))))
        self.enterContext(patch.object(ui, "comports", return_value=[native, bridge]))
        self.window = QWidget()
        self.addCleanup(self.window.close)
        ui.populate_update_page(self.window, QVBoxLayout(self.window))
        self.port = self.window.findChild(QComboBox)
        self.buttons = {button.text(): button for button in self.window.findChildren(QPushButton)}

    def wait_for(self, predicate):
        deadline = monotonic() + 5
        while not predicate():
            if monotonic() >= deadline:
                self.fail("Timeout waiting for firmware UI state")
            QTest.qWait(10)

    def labels(self):
        return [label.text() for label in self.window.findChildren(QLabel)]

    def test_one_boot_button_handles_both_native_and_manual_boot(self):
        self.assertNotIn("Rileva laptimer", self.buttons)
        boot = self.buttons["Entra in BOOT e rileva"]
        self.port.setCurrentIndex(self.port.findData("COM10"))
        self.assertTrue(boot.isEnabled())
        with patch.object(QMessageBox, "question") as confirm:
            boot.click()
            self.wait_for(lambda: "Guition 4.3" in self.labels())
            confirm.assert_not_called()
        self.port.setCurrentIndex(self.port.findData("COM9"))
        with patch.object(QMessageBox, "question", return_value=QMessageBox.No) as confirm:
            boot.click()
            confirm.assert_called_once()
            self.assertNotIn("Guition 4.3", self.labels())
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
            boot.click()
            self.wait_for(lambda: "Guition 4.3" in self.labels())

    def test_local_and_online_packages_show_status_colors_and_allow_reboot(self):
        reboot = self.buttons["Riavvia laptimer"]
        self.assertFalse(reboot.isEnabled())
        self.port.setCurrentIndex(self.port.findData("COM10"))
        self.buttons["Entra in BOOT e rileva"].click()
        self.wait_for(reboot.isEnabled)
        with patch.object(ui.QFileDialog, "getOpenFileName", return_value=(str(self.directory / "RC3.bin"), "")):
            self.buttons["Apri file firmware locale"].click()
        self.wait_for(lambda: "Il pacchetto selezionato è di una versione precedente." in self.labels())
        self.assertTrue(any(label.startswith("Changelog RC3 · Guition 4.3") for label in self.labels()))
        self.assertTrue(self.buttons["Aggiorna firmware via USB"].isEnabled())

        green = "NUOVA VERSIONE FIRMWARE DISPONIBILE"
        download = self.buttons["Scarica firmware da GitHub"]
        self.assertEqual(download.text(), "Scarica RC3.2 da GitHub")
        download.click()
        self.wait_for(lambda: green in self.labels())
        self.assertTrue(any(label.startswith("Changelog RC3.2 · Guition 4.3") for label in self.labels()))
        green_label = next(label for label in self.window.findChildren(QLabel) if label.text() == green)
        self.assertIn("color: #59de8b", green_label.styleSheet())

        red = "AGGIORNAMENTO NON NECESSARIO"
        with patch.object(ui.QFileDialog, "getOpenFileName", return_value=(str(self.directory / "current.bin"), "")):
            self.buttons["Apri file firmware locale"].click()
        self.wait_for(lambda: any(label.startswith(red) for label in self.labels()))
        red_label = next(label for label in self.window.findChildren(QLabel) if label.text().startswith(red))
        self.assertIn("color: #ff7474", red_label.styleSheet())
        self.assertIn("font-size: 18pt", red_label.styleSheet())
        self.assertFalse(self.buttons["Aggiorna firmware via USB"].isEnabled())

        reboot.click()
        self.wait_for(lambda: "Modello da rilevare" in self.labels())
        self.assertFalse(reboot.isEnabled())
        self.assertFalse(any(label.startswith("Changelog") for label in self.labels()))



if __name__ == "__main__":
    unittest.main()
