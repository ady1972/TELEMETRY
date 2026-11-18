import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'mobile/v0.2.3/fullapp/src/main/python'))
import android_bridge as bridge
import goats_cloud_sync as sync


class MobileDeletionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.cloud=self.root/'cloud';self.cloud.mkdir()
        bridge.init_app(str(self.root/'phone'));self.addCleanup(bridge._STORE.conn.close)
        self.source=self.cloud/'session.grt'
        self.source.write_bytes((ROOT/'windows/v5.4.15.7-burst4/sample_test.grt').read_bytes())
        self.h=sync.digest(self.source)

    def test_windows_deletion_removes_mobile_rows_and_managed_original(self):
        result=json.loads(bridge.sync_cloud_folder(str(self.cloud)));self.assertEqual(result['imported'],1)
        row=bridge._STORE.sessions()[0];source=Path(row['source_path'])
        self.assertTrue(source.exists());bridge._STORE.update_notes(row['id'],'Solo locale')
        sync.delete_session_files(self.cloud,self.root/'pc/files',self.root/'pc/cache',self.h)
        result=json.loads(bridge.sync_cloud_folder(str(self.cloud)))
        self.assertEqual(result['deleted'],1);self.assertEqual(bridge._STORE.sessions(),[])
        self.assertFalse(source.exists());self.assertFalse(list(self.cloud.glob('*.grt')))
        again=json.loads(bridge.sync_cloud_folder(str(self.cloud)))
        self.assertEqual((again['imported'],again['deleted']),(0,0))

    def test_receipt_arriving_before_session_prevents_initial_import(self):
        sync.delete_session_files(self.cloud,self.root/'pc/files',self.root/'pc/cache',self.h)
        self.source.write_bytes((ROOT/'windows/v5.4.15.7-burst4/sample_test.grt').read_bytes())
        result=json.loads(bridge.sync_cloud_folder(str(self.cloud)))
        self.assertEqual(result['imported'],0);self.assertEqual(bridge._STORE.sessions(),[])
        self.assertFalse(self.source.exists())


if __name__=='__main__':unittest.main(verbosity=2)
