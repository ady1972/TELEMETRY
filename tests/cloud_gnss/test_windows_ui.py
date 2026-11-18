import importlib.util
import os
from pathlib import Path
import sys
import json
import tempfile
import time
from types import MethodType
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
ROOT=Path(__file__).resolve().parents[2]
APP=ROOT/('windows/v'+os.environ.get('GOATS_WINDOWS_VERSION','5.4.15.6')+'-burst4')
sys.path.insert(0,str(APP))
spec=importlib.util.spec_from_file_location('manager_new',APP/('goats_rt_manager_v'+os.environ.get('GOATS_WINDOWS_VERSION','5.4.15.6').replace('.','_')+'.py'))
manager=importlib.util.module_from_spec(spec);spec.loader.exec_module(manager)
import goats_gnss as gnss


class WindowsUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=manager.QApplication.instance() or manager.QApplication([])

    def setUp(self):
        self.host=manager.QMainWindow();self.host.page=lambda *args:manager.Main.page(self.host,*args)
        self.addCleanup(self.host.close)

    def test_opening_page_does_not_change_receiver_and_lists_all_choices(self):
        with patch.object(gnss.serial,'Serial') as serial,patch.object(gnss,'ports',return_value=['COM_TEST']):
            page=manager.Main.gnss_page(self.host);self.addCleanup(page.close)
            for name in gnss.CONSTELLATIONS:self.assertIsNotNone(page.findChild(manager.QCheckBox,'gnssConstellation'+name))
            combo=page.findChild(manager.QComboBox,'gnssOutputProtocol')
            self.assertEqual([combo.itemData(i) for i in range(combo.count())],['UBX','NMEA','UBX+NMEA'])
            serial.assert_not_called()

    def test_nmea_only_requires_explicit_warning_before_apply(self):
        with patch.object(gnss,'ports',return_value=['COM_TEST']):page=manager.Main.gnss_page(self.host)
        self.addCleanup(page.close)
        combo=page.findChild(manager.QComboBox,'gnssOutputProtocol');combo.setCurrentIndex(combo.findData('NMEA'))
        button=next(b for b in page.findChildren(manager.QPushButton) if b.text()=='APPLICA COSTELLAZIONI E PROTOCOLLO')
        with patch.object(manager.QMessageBox,'question',return_value=manager.QMessageBox.Yes) as confirm, \
             patch.object(gnss,'apply_navigation_profile') as apply:
            button.click()
            self.assertIn('non è compatibile',confirm.call_args.args[2])
            self.assertEqual(apply.call_args.args[0:2],('COM_TEST',230400))
            self.assertEqual(apply.call_args.args[3],'NMEA')

    def test_windows_sync_worker_imports_session_tracks_and_retries_idempotently(self):
        from goats_cloud_sync import sync_folder
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for folder in ('pc/sessions','pc/tracks','phone/sessions','phone/tracks','phone/cache'):
                (root/folder).mkdir(parents=True)
            (root/'phone/sessions/test.grt').write_bytes((APP/'sample_test.grt').read_bytes())
            track=json.loads((APP/'tracks/esempio.json').read_text())
            track.update(id='test_sync',name='Test sync')
            (root/'phone/tracks/test_sync.json').write_text(json.dumps(track))
            sync_folder(root/'cloud',root/'phone/sessions',root/'phone/tracks',root/'phone/cache')
            host=self.host
            host.cloud_folder=str(root/'cloud');host.active_sessions_dir=root/'pc/sessions'
            host.active_tracks_dir=root/'pc/tracks';host.cloud_status=manager.QLabel()
            host.store=manager.SessionStore(host.active_sessions_dir/'sessions.sqlite3')
            host._potential_lap_cache={};host._track_data_cache={};host.embedded_tools={}
            host.refresh_sessions=lambda:None
            if hasattr(manager.Main,'_prepare_session_files'):
                host._prepare_session_files=MethodType(manager.Main._prepare_session_files,host)
            host._cloud_start=MethodType(manager.Main._cloud_start,host)
            host._cloud_finished=MethodType(manager.Main._cloud_finished,host)
            try:
                with patch.object(manager,'DATA_DIR',root/'private'):
                    for cycle in range(2):
                        host._cloud_start()
                        deadline=time.monotonic()+5
                        while host._cloud_future is not None and time.monotonic()<deadline:
                            self.app.processEvents();time.sleep(.01)
                        self.assertIsNone(host._cloud_future)
                        self.assertIn('Errori: 0',host.cloud_status.text())
                        self.assertEqual(len(host.store.sessions()),1)
                    self.assertTrue((host.active_tracks_dir/'test_sync.json').exists())
            finally:
                host._cloud_poll_timer.stop()
                host._cloud_executor.shutdown(wait=True)
                host.store.conn.close()


if __name__=='__main__':unittest.main(verbosity=2)
