import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'mobile/v0.2.2/fullapp/src/main/python'))
import android_bridge as bridge
import goats_cloud_sync as sync


class MobileBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        bridge.init_app(str(self.root/'phone'));self.addCleanup(bridge._STORE.conn.close)
        for folder in ('cloud','pc/sessions','pc/tracks','pc/cache'):(self.root/folder).mkdir(parents=True)

    def test_imports_session_and_circuit_into_real_mobile_database(self):
        sample=ROOT/'windows/v5.4.15.5-burst4/sample_test.grt'
        (self.root/'pc/sessions/test.grt').write_bytes(sample.read_bytes())
        track=json.loads((ROOT/'windows/v5.4.15.5-burst4/tracks/esempio.json').read_text())
        track['id']='pista_pc';track['name']='Pista PC'
        (self.root/'pc/tracks/pista_pc.json').write_text(json.dumps(track))
        sync.sync_folder(self.root/'cloud',self.root/'pc/sessions',self.root/'pc/tracks',self.root/'pc/cache')
        result=json.loads(bridge.sync_cloud_folder(str(self.root/'cloud')))
        self.assertEqual((result['imported'],result['tracks_imported'],result['errors']),(1,1,[]))
        sessions=json.loads(bridge.sessions_json());self.assertEqual(len(sessions),1)
        self.assertEqual(len(json.loads(bridge.analysis_json(sessions[0]['id']))['points']),50)
        bridge.set_session_notes(sessions[0]['id'],'nota solo locale')
        again=json.loads(bridge.sync_cloud_folder(str(self.root/'cloud')))
        self.assertEqual(again['imported'],0)
        self.assertEqual(json.loads(bridge.sessions_json())[0]['notes'],'nota solo locale')
        self.assertTrue(json.loads(bridge.track_json('pista_pc'))['ok'])

    def test_mobile_track_save_is_visible_to_pc(self):
        track=json.loads((ROOT/'windows/v5.4.15.5-burst4/tracks/esempio.json').read_text())
        track.update(id='pista_mobile',name='Pista Mobile',trigger_radius_m=35)
        bridge.save_track_json(json.dumps(track));bridge.sync_cloud_folder(str(self.root/'cloud'))
        result=sync.sync_folder(self.root/'cloud',self.root/'pc/sessions',self.root/'pc/tracks',self.root/'pc/cache')
        self.assertGreaterEqual(result['tracks_imported'],1)
        value=json.loads((self.root/'pc/tracks/pista_mobile.json').read_text())
        self.assertEqual(value['trigger_radius_m'],35)


if __name__=='__main__':unittest.main(verbosity=2)
