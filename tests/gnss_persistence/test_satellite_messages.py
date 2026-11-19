"""Receiver configuration diagnostics used by Guition and passive RLCD."""
import os
os.environ.setdefault('GOATS_WINDOWS_VERSION','5.4.15.11')
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import importlib.util
import sys
import unittest
from unittest.mock import patch
from test_storage import Device,gnss,APP


class SatelliteMessageTests(unittest.TestCase):
    def use(self,d):return patch.object(gnss.serial,'Serial',side_effect=d.connect)

    def at_25_hz(self):
        d=Device();d.ram.update({gnss.CFG_RATE_MEAS:40,gnss.CFG_RATE_NAV:1})
        return d

    def test_ubx_profiles_save_pvt_dop_at_full_rate_and_sat_at_one_hz(self):
        for protocol in ('UBX','UBX+NMEA'):
            with self.subTest(protocol=protocol):
                d=self.at_25_hz()
                with self.use(d):values=gnss.apply_navigation_profile('COM1',230400,('GPS','Galileo'),protocol)
                self.assertEqual(values[gnss.UBX_UART1['NAV-PVT']],1)
                self.assertEqual(values[gnss.UBX_UART1['NAV-DOP']],1)
                self.assertEqual(values[gnss.UBX_UART1['NAV-SAT']],25)
                self.assertEqual(values[gnss.UBX_UART1['NAV-STATUS']],0)
                self.assertNotIn(gnss.CFG_RATE_MEAS,values);self.assertNotIn(gnss.CFG_RATE_NAV,values)
                self.assertNotIn(gnss.CFG_UART1_BAUDRATE,values)
                self.assertEqual((d.ram[gnss.CFG_RATE_MEAS],d.ram[gnss.CFG_RATE_NAV]),(40,1))
                d.reboot()
                for name,rate in (('NAV-PVT',1),('NAV-DOP',1),('NAV-SAT',25)):
                    self.assertEqual(d.ram[gnss.UBX_UART1[name]],rate)

    def test_nmea_only_keeps_all_ubx_navigation_messages_disabled(self):
        d=self.at_25_hz()
        with self.use(d):values=gnss.apply_navigation_profile('COM1',230400,('GPS',),'NMEA')
        for key in gnss.UBX_UART1.values():self.assertEqual(values[key],0)
        self.assertEqual(values[gnss.NMEA_UART1['GGA']],1)
        self.assertEqual(values[gnss.NMEA_UART1['RMC']],1)
        self.assertEqual((d.ram[gnss.CFG_RATE_MEAS],d.ram[gnss.CFG_RATE_NAV]),(40,1))

    def test_changing_frequency_retunes_satellite_divisor_and_saves_it(self):
        d=self.at_25_hz()
        with self.use(d):
            gnss.apply_navigation_profile('COM1',230400,('GPS',),'UBX')
            gnss.set_navigation_rate('COM1',230400,100,1)
            state=gnss.read_navigation_profile('COM1',230400)
        self.assertEqual((state['navigation_hz'],state['nav_sat_divisor'],state['nav_sat_hz']),(10,10,1))
        d.reboot();self.assertEqual(d.ram[gnss.UBX_UART1['NAV-SAT']],10)
        self.assertEqual((d.ram[gnss.UBX_UART1['NAV-PVT']],d.ram[gnss.UBX_UART1['NAV-DOP']]),(1,1))

    def test_fractional_navigation_frequency_uses_a_conservative_divisor(self):
        d=self.at_25_hz();d.ram[gnss.CFG_RATE_NAV]=2
        with self.use(d):
            gnss.apply_navigation_profile('COM1',230400,('GPS',),'UBX')
            state=gnss.read_navigation_profile('COM1',230400)
        self.assertEqual(state['nav_sat_divisor'],13)
        self.assertAlmostEqual(state['nav_sat_hz'],12.5/13)
        self.assertLessEqual(state['nav_sat_hz'],1)

    def test_slow_navigation_cannot_emit_sat_faster_than_navigation(self):
        d=Device();d.ram[gnss.CFG_RATE_NAV]=5
        with self.use(d):
            gnss.apply_navigation_profile('COM1',230400,('GPS',),'UBX')
            state=gnss.read_navigation_profile('COM1',230400)
        self.assertEqual((state['nav_sat_divisor'],state['nav_sat_hz']),(1,.2))

    def test_rate_change_does_not_enable_sat_when_it_was_disabled(self):
        d=self.at_25_hz();d.ram[gnss.UBX_UART1['NAV-SAT']]=0
        with self.use(d):gnss.set_navigation_rate('COM1',230400,100,1)
        self.assertEqual(d.ram[gnss.UBX_UART1['NAV-SAT']],0)
        self.assertNotIn(gnss.UBX_UART1['NAV-SAT'],d.flash)

    def test_read_reports_disabled_when_ubx_output_is_off(self):
        d=self.at_25_hz();d.ram.update({gnss.CFG_UART1OUTPROT_UBX:0,gnss.CFG_UART1OUTPROT_NMEA:1})
        with self.use(d):state=gnss.read_navigation_profile('COM1',230400)
        self.assertFalse(state['nav_sat_enabled']);self.assertEqual(state['nav_sat_hz'],0)

    def test_invalid_rate_read_prevents_any_configuration_write(self):
        d=self.at_25_hz();d.ram[gnss.CFG_RATE_NAV]=0
        with self.use(d),self.assertRaises(RuntimeError):gnss.apply_navigation_profile('COM1',230400,('GPS',),'UBX')
        self.assertFalse(any(f[3]==0x8a for f in d.sent));self.assertEqual(d.flash,{})


sys.path.insert(0,str(APP))
spec=importlib.util.spec_from_file_location('sat_manager',APP/'goats_rt_manager_v5_4_15_11.py')
manager=importlib.util.module_from_spec(spec);spec.loader.exec_module(manager)
import goats_gnss as ui_gnss


class SatelliteLogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=manager.QApplication.instance() or manager.QApplication([])

    def test_log_reads_satellite_rate_from_receiver_without_writing(self):
        for enabled in (True,False):
            with self.subTest(enabled=enabled):
                host=manager.QMainWindow();host.page=lambda *args:manager.Main.page(host,*args)
                with patch.object(ui_gnss,'ports',return_value=['COM_TEST']):page=manager.Main.gnss_page(host)
                d=Device();d.ram.update({gnss.CFG_RATE_MEAS:40,gnss.CFG_RATE_NAV:1,gnss.UBX_UART1['NAV-SAT']:25,
                                      gnss.CFG_UART1OUTPROT_UBX:int(enabled),gnss.CFG_UART1OUTPROT_NMEA:int(not enabled)})
                try:
                    with patch.object(ui_gnss.serial,'Serial',side_effect=d.connect),patch.object(manager.QMessageBox,'warning') as warning:
                        page.findChild(manager.QPushButton,'gnssReadConfiguration').click()
                    warning.assert_not_called()
                    log=page.findChild(manager.QTextEdit).toPlainText()
                    self.assertIn('UBX-NAV-SAT: 1 Hz (divisore 25).' if enabled else 'UBX-NAV-SAT: disabilitato.',log)
                    self.assertIn('navigazione 25 Hz',log)
                    self.assertFalse(any(f[3]==0x8a for f in d.sent))
                finally:page.close();host.close()


if __name__=='__main__':unittest.main(verbosity=2)
