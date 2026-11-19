import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import time
from types import MethodType
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
ROOT=Path(__file__).resolve().parents[2];VERSION=os.environ.get('GOATS_WINDOWS_VERSION','5.4.15.7')
APP=ROOT/('windows/v'+VERSION+'-burst4')
sys.path.insert(0,str(APP))
spec=importlib.util.spec_from_file_location('manager_flow',APP/('goats_rt_manager_v'+VERSION.replace('.','_')+'.py'))
manager=importlib.util.module_from_spec(spec);spec.loader.exec_module(manager)


class WindowsFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=manager.QApplication.instance() or manager.QApplication([])

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.host=manager.QMainWindow();h=self.host
        h.store=manager.SessionStore(self.root/'db.sqlite3')
        h.active_sessions_dir=self.root/'archive';h.active_tracks_dir=self.root/'tracks'
        h.cloud_folder=str(self.root/'cloud');Path(h.cloud_folder).mkdir()
        h.cloud_auto=False;h.cloud_status=manager.QLabel();h.embedded_tools={}
        h._potential_lap_cache={};h._track_data_cache={}
        h.refresh_sessions=lambda:None;h.show_page=lambda *args:None
        h.selected_id=lambda:h.store.sessions()[0]['id'] if h.store.sessions() else None
        for name in ('_prepare_session_files','_startup_sync','_cloud_start','_cloud_finished','do_import','delete_selected'):
            setattr(h,name,MethodType(getattr(manager.Main,name),h))
        self.data=patch.object(manager,'DATA_DIR',self.root/'private');self.data.start()
        self.source=self.root/'original.grt';self.source.write_bytes((APP/'sample_test.grt').read_bytes())

    def tearDown(self):
        h=self.host
        if hasattr(h,'_cloud_poll_timer'):h._cloud_poll_timer.stop()
        if hasattr(h,'_cloud_executor'):h._cloud_executor.shutdown(wait=True)
        h.store.close();h.close();self.data.stop();self.tmp.cleanup()

    def wait(self):
        deadline=time.monotonic()+5
        while getattr(self.host,'_cloud_future',None) is not None and time.monotonic()<deadline:
            self.app.processEvents();time.sleep(.01)
        self.assertIsNone(getattr(self.host,'_cloud_future',None))
        self.assertIn('Errori: 0',self.host.cloud_status.text())

    def test_startup_imports_mobile_files_even_with_periodic_sync_off(self):
        (Path(self.host.cloud_folder)/'from_phone.grt').write_bytes(self.source.read_bytes())
        self.host._startup_sync();self.wait()
        self.assertEqual(len(self.host.store.sessions()),1)
        sid=self.host.selected_id();self.host.store.update_notes(sid,'Preservare')
        self.host._startup_sync();self.wait()
        self.assertEqual(len(self.host.store.sessions()),1)
        self.assertEqual(self.host.store.session(sid)['notes'],'Preservare')

    def test_import_publishes_file_even_with_periodic_sync_off(self):
        with patch.object(manager.QMessageBox,'information'):
            self.host.do_import([str(self.source)])
        self.wait()
        self.assertEqual(len(list(Path(self.host.cloud_folder).glob('*.grt'))),1)
        self.assertEqual(len(self.host.store.sessions()),1)
        self.assertTrue(Path(self.host.store.sessions()[0]['source_path']).is_file())

    def test_confirmed_delete_removes_file_and_does_not_reappear_at_startup(self):
        (Path(self.host.cloud_folder)/'from_phone.grt').write_bytes(self.source.read_bytes())
        self.host._startup_sync();self.wait()
        with patch.object(manager.QMessageBox,'question',return_value=manager.QMessageBox.Yes):
            self.host.delete_selected()
        self.assertEqual(self.host.store.sessions(),[])
        self.assertFalse(list(Path(self.host.cloud_folder).glob('*.grt')))
        self.host._startup_sync();self.wait()
        self.assertEqual(self.host.store.sessions(),[])
        self.assertTrue(self.source.exists())

    def test_import_adopts_a_legacy_source_reconnected_after_startup(self):
        from goats_formats import parse_any
        sid=self.host.store.import_session(parse_any(str(self.source))[0])
        self.host.store.update_notes(sid,'Storica da conservare')
        disconnected=self.source.with_suffix('.offline');self.source.rename(disconnected)
        self.host._startup_sync();self.wait()
        disconnected.rename(self.source)
        with patch.object(manager.QMessageBox,'information'):
            self.host.do_import([str(self.source)])
        self.wait()
        self.assertEqual(len(self.host.store.sessions()),1)
        self.assertEqual(self.host.store.session(sid)['notes'],'Storica da conservare')
        self.assertTrue(self.host.store.session(sid)['source_sha256'])

    def test_cancelled_delete_keeps_rows_and_files(self):
        (Path(self.host.cloud_folder)/'from_phone.grt').write_bytes(self.source.read_bytes())
        self.host._startup_sync();self.wait()
        with patch.object(manager.QMessageBox,'question',return_value=manager.QMessageBox.No):
            self.host.delete_selected()
        self.assertEqual(len(self.host.store.sessions()),1)
        self.assertTrue(list(Path(self.host.cloud_folder).glob('*.grt')))


if __name__=='__main__':unittest.main(verbosity=2)
