import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
WIN = ROOT / 'windows/v5.4.15.6-burst4'
MOBILE = ROOT / 'mobile/v0.2.2/fullapp/src/main/python'
spec = importlib.util.spec_from_file_location('sync_engine', WIN/'goats_cloud_sync.py')
sync = importlib.util.module_from_spec(spec);spec.loader.exec_module(sync)


class CloudTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name);self.cloud = self.root/'cloud'
        for name in ('pc','phone'):
            for folder in ('sessions','tracks','cache'):(self.root/name/folder).mkdir(parents=True)

    def track(self, peer, name='Pista test', radius=20):
        obj = dict(schema_version=3,id='pista_test',name=name,country='IT',direction='clockwise',
                   start_line=dict(lat1=45.,lon1=9.,lat2=45.001,lon2=9.001),trigger_radius_m=radius,sectors=[])
        (self.root/peer/'tracks/pista_test.json').write_text(json.dumps(obj))
        return obj

    def run_sync(self, peer, known=()):
        base = self.root/peer
        result = sync.sync_folder(self.cloud,base/'sessions',base/'tracks',base/'cache',known)
        self.assertEqual(result['errors'],[])
        return result

    def test_identical_engine_on_both_platforms(self):
        self.assertEqual((WIN/'goats_cloud_sync.py').read_bytes(),(MOBILE/'goats_cloud_sync.py').read_bytes())

    def test_session_round_trip_idempotence_and_no_database_exchange(self):
        source=self.root/'pc/sessions/S001.csv';source.write_text('elapsed_ms,latitude,longitude,speed_kmh\n0,45,9,50\n')
        (self.cloud).mkdir();(self.cloud/'manager_settings.json').write_text('{"token":"synthetic-do-not-share"}')
        self.run_sync('pc',[source])
        result=self.run_sync('phone')
        self.assertEqual(len(result['session_files']),1)
        item=result['session_files'][0];self.assertEqual(Path(item['path']).read_bytes(),source.read_bytes())
        sync.mark_sessions_imported(self.root/'phone/cache',[item['sha256']])
        again=self.run_sync('phone');self.assertEqual(again['session_files'],[]);self.assertEqual(again['uploaded'],0)
        self.assertFalse(list((self.root/'phone/sessions').glob('*settings*')))

    def test_same_name_same_size_different_contents_are_preserved(self):
        for peer,speed in (('pc','50'),('phone','60')):
            (self.root/peer/'sessions/S001.csv').write_text('elapsed_ms,latitude,longitude,speed_kmh\n0,45,9,'+speed+'\n')
        self.run_sync('pc');self.run_sync('phone');self.run_sync('pc')
        self.assertEqual(len(list(self.cloud.glob('*.csv'))),2)
        self.assertEqual((self.root/'pc/sessions/S001.csv').read_text().splitlines()[-1],'0,45,9,50')
        self.assertEqual((self.root/'phone/sessions/S001.csv').read_text().splitlines()[-1],'0,45,9,60')

    def test_failed_import_is_retried_until_acknowledged(self):
        p=self.root/'pc/sessions/one.csv';p.write_text('elapsed_ms,latitude,longitude\n0,45,9\n')
        self.run_sync('pc',[p]);first=self.run_sync('phone');second=self.run_sync('phone')
        self.assertEqual(first['session_files'],second['session_files'])
        sync.mark_sessions_imported(self.root/'phone/cache',[first['session_files'][0]['sha256']])
        self.assertEqual(self.run_sync('phone')['session_files'],[])

    def test_changed_database_source_is_not_silently_skipped(self):
        p=self.root/'pc/sessions/one.csv';p.write_text('latitude,longitude\n45,9\n')
        self.run_sync('pc',[p]);p.write_text('latitude,longitude\n46,9\n')
        result=self.run_sync('pc',[p]);self.assertEqual(len(result['session_files']),1)
        self.assertEqual(len(self.run_sync('pc',[p])['session_files']),1)

    def test_track_updates_pc_to_phone_and_back(self):
        self.track('pc');self.run_sync('pc');result=self.run_sync('phone')
        self.assertEqual(result['tracks_imported'],1)
        self.track('phone',radius=27);self.run_sync('phone');self.run_sync('pc')
        value=json.loads((self.root/'pc/tracks/pista_test.json').read_text())
        self.assertEqual(value['trigger_radius_m'],27)
        self.assertEqual(self.run_sync('pc')['tracks_imported'],0)

    def test_concurrent_edits_remain_as_conflict_variants_without_republishing(self):
        self.track('pc');self.run_sync('pc');self.run_sync('phone')
        self.track('pc',radius=22);self.track('phone',radius=33)
        self.run_sync('pc');phone=self.run_sync('phone');pc=self.run_sync('pc')
        self.assertEqual((phone['conflicts'],pc['conflicts']),(1,1))
        for peer in ('pc','phone'):
            values=[json.loads(p.read_text()) for p in (self.root/peer/'tracks').glob('*.json')]
            self.assertEqual({v['trigger_radius_m'] for v in values},{22,33})
        count=len(list((self.cloud/'circuiti').glob('*.json')))
        self.run_sync('phone');self.run_sync('pc')
        self.assertEqual(len(list((self.cloud/'circuiti').glob('*.json'))),count)
        # An explicit edit after seeing both variants supersedes both heads.
        self.track('pc',radius=44);self.run_sync('pc');result=self.run_sync('phone')
        self.assertEqual(result['conflicts'],0)
        self.assertEqual(json.loads((self.root/'phone/tracks/pista_test.json').read_text())['trigger_radius_m'],44)

    def test_no_remote_deletion_and_revisions_survive_offline(self):
        self.track('pc');self.run_sync('pc');self.run_sync('phone')
        (self.root/'phone/tracks/pista_test.json').unlink();self.run_sync('phone')
        self.assertTrue((self.root/'phone/tracks/pista_test.json').exists())
        self.assertEqual(len(list((self.cloud/'circuiti').glob('*.json'))),1)

    def test_interrupted_cloud_and_local_copies_are_not_imported_or_published(self):
        self.cloud.mkdir()
        partial='session--'+('a'*64)+'.csv'
        for folder in (self.cloud,self.root/'pc/sessions'):
            (folder/partial).write_text('latitude,longitude\n45,9\n')
        result=sync.sync_folder(self.cloud,self.root/'pc/sessions',self.root/'pc/tracks',self.root/'pc/cache')
        self.assertEqual(result['session_files'],[])
        self.assertEqual(result['uploaded'],0)
        self.assertEqual(len(result['errors']),2)
        self.assertEqual(len(list(self.cloud.glob('*.csv'))),1)

    def test_corrupted_track_revision_is_reported_without_overwriting_local(self):
        original=self.track('pc');self.run_sync('pc')
        event=next((self.cloud/'circuiti').glob('*.json'))
        obj=json.loads(event.read_text());obj['track']['trigger_radius_m']=99;event.write_text(json.dumps(obj))
        result=sync.sync_folder(self.cloud,self.root/'pc/sessions',self.root/'pc/tracks',self.root/'pc/cache')
        self.assertTrue(result['errors'])
        self.assertEqual(json.loads((self.root/'pc/tracks/pista_test.json').read_text()),original)


if __name__=='__main__':unittest.main(verbosity=2)
