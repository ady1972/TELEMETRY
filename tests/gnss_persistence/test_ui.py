import importlib.util
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
ROOT=Path(__file__).resolve().parents[2];VERSION=os.environ.get('GOATS_WINDOWS_VERSION','5.4.15.8')
APP=ROOT/('windows/v'+VERSION+'-burst4')
sys.path.insert(0,str(APP))
spec=importlib.util.spec_from_file_location('manager_flash_ui',APP/('goats_rt_manager_v'+VERSION.replace('.','_')+'.py'))
manager=importlib.util.module_from_spec(spec);spec.loader.exec_module(manager)
import goats_gnss as gnss
from test_storage import Device


class PersistenceUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=manager.QApplication.instance() or manager.QApplication([])

    def setUp(self):
        self.host=manager.QMainWindow();self.host.page=lambda *args:manager.Main.page(self.host,*args)
        self.addCleanup(self.host.close)
        warning=patch.object(manager.QMessageBox,'warning');self.warning=warning.start();self.addCleanup(warning.stop)
        with patch.object(gnss,'ports',return_value=['COM_TEST']):self.page=manager.Main.gnss_page(self.host)
        self.addCleanup(self.page.close)

    def button(self,name):return self.page.findChild(manager.QPushButton,name)
    def combo(self,name):return self.page.findChild(manager.QComboBox,name)
    def read(self,period=40,nav=1):
        state=dict(constellations=['GPS','Galileo'],protocol='UBX+NMEA',uart1_baudrate=230400,
                   **gnss._rate_info({gnss.CFG_RATE_MEAS:period,gnss.CFG_RATE_NAV:nav}))
        if hasattr(gnss,'_nav_sat_info'):
            state.update(gnss._nav_sat_info({gnss.CFG_RATE_MEAS:period,gnss.CFG_RATE_NAV:nav,gnss.CFG_UART1OUTPROT_UBX:1,
                                           gnss.UBX_UART1['NAV-SAT']:gnss._nav_sat_divisor({gnss.CFG_RATE_MEAS:period,gnss.CFG_RATE_NAV:nav})}))
        with patch.object(gnss,'read_navigation_profile',return_value=state),patch.object(gnss,'set_navigation_rate') as write:
            self.button('gnssReadConfiguration').click();write.assert_not_called()
        self.warning.assert_not_called()
        return state

    def test_page_explains_automatic_flash_and_has_no_optional_persistence_checkbox(self):
        policy=self.page.findChild(manager.QLabel,'gnssSavePolicy')
        self.assertIn('FLASH',policy.text())
        self.assertFalse(any('Salva anche' in c.text() for c in self.page.findChildren(manager.QCheckBox)))

    def test_read_updates_hz_selection_and_constellations(self):
        self.read()
        self.assertEqual(tuple(self.combo('gnssRateHz').currentData()),(40,1))
        if tuple(map(int,VERSION.split('.')))>=(5,4,15,9):
            log=self.page.findChild(manager.QTextEdit).toPlainText()
            self.assertIn('navigazione 25 Hz',log)
            self.assertIn('40 ms',log)
            self.assertIn('divisore NAV 1',log)
            self.assertIn('Baud UART1: 230400',log)
        self.assertIn('navigazione 25 Hz',self.page.findChild(manager.QLabel,'gnssReadRate').text())
        self.assertEqual(self.combo('gnssOutputProtocol').currentData(),'UBX+NMEA')
        self.assertFalse(self.page.findChild(manager.QCheckBox,'gnssConstellationGLONASS').isChecked())

    def test_read_preserves_custom_period_and_navigation_divisor(self):
        state=self.read(40,2)
        self.assertEqual(tuple(self.combo('gnssRateHz').currentData()),(40,2))
        self.assertIn('12.5 Hz',self.combo('gnssRateHz').currentText())
        if tuple(map(int,VERSION.split('.')))>=(5,4,15,9):
            log=self.page.findChild(manager.QTextEdit).toPlainText()
            self.assertIn('navigazione 12.5 Hz',log)
            self.assertIn('divisore NAV 2',log)
        with patch.object(manager.QMessageBox,'question',return_value=manager.QMessageBox.Yes), \
             patch.object(gnss,'set_navigation_rate',return_value=state) as write:
            self.button('gnssApplyRate').click()
        write.assert_called_once_with('COM_TEST',230400,40,2)

    def test_profile_button_saves_in_flash_without_an_extra_option(self):
        d=Device()
        button=next(b for b in self.page.findChildren(manager.QPushButton) if b.text()=='APPLICA COSTELLAZIONI E PROTOCOLLO')
        with patch.object(gnss.serial,'Serial',side_effect=d.connect), \
             patch.object(manager.QMessageBox,'question',return_value=manager.QMessageBox.Yes):
            button.click()
        self.warning.assert_not_called()
        self.assertEqual(next(f for f in d.sent if f[3]==0x8a)[7],7)
        self.assertTrue(d.flash)
        self.assertIn('Profilo salvato e verificato',self.page.findChild(manager.QTextEdit).toPlainText())

    def test_frequency_button_automatically_persists_both_rate_keys(self):
        self.read();d=Device()
        with patch.object(gnss.serial,'Serial',side_effect=d.connect), \
             patch.object(manager.QMessageBox,'question',return_value=manager.QMessageBox.Yes):
            self.button('gnssApplyRate').click()
        self.warning.assert_not_called()
        self.assertEqual((d.flash[gnss.CFG_RATE_MEAS],d.flash[gnss.CFG_RATE_NAV]),(40,1))

    def test_baud_button_can_save_the_current_speed(self):
        with patch.object(manager.QMessageBox,'question',return_value=manager.QMessageBox.Yes), \
             patch.object(gnss,'set_uart1_baud') as write:
            self.button('gnssApplyBaud').click()
        write.assert_called_once_with('COM_TEST',230400,230400)
        self.assertIn('salvato e verificato',self.page.findChild(manager.QTextEdit).toPlainText())

    def test_flash_failure_is_displayed_without_a_success_message(self):
        with patch.object(manager.QMessageBox,'question',return_value=manager.QMessageBox.Yes), \
             patch.object(gnss,'set_navigation_rate',side_effect=RuntimeError('Salvataggio FLASH non verificato')):
            self.button('gnssApplyRate').click()
        self.assertIn('FLASH non verificato',self.warning.call_args.args[2])
        self.assertNotIn('salvata e verificata',self.page.findChild(manager.QTextEdit).toPlainText())


if __name__=='__main__':unittest.main(verbosity=2)
