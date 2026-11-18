import json
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
APP=ROOT/'windows/v5.4.15.7-burst4'
sys.path.insert(0,str(APP))
from goats_store import SessionStore
from goats_formats import parse_any
from goats_session_archive import import_file,adopt_existing,delete_session,deletion_group
from goats_cloud_sync import sync_folder,digest,delete_session_files


class SessionFileTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.archive=self.root/'pc/files';self.tracks=self.root/'pc/tracks'
        self.cache=self.root/'pc/cache';self.cloud=self.root/'cloud'
        self.source=self.root/'original.grt';self.source.write_bytes((APP/'sample_test.grt').read_bytes())
        self.store=SessionStore(self.root/'db.sqlite3');self.addCleanup(self.store.close)

    def sync(self):
        return sync_folder(self.cloud,self.archive,self.tracks,self.cache,
                           [r['source_path'] for r in self.store.sessions()])

    def test_import_keeps_original_bytes_and_survives_source_removal(self):
        self.assertEqual(import_file(self.store,self.source,self.archive),1)
        row=self.store.sessions()[0];managed=Path(row['source_path'])
        self.assertEqual(managed.parent,self.archive)
        self.assertEqual(managed.read_bytes(),self.source.read_bytes())
        self.source.unlink();self.sync()
        self.assertEqual(next(self.cloud.glob('*.grt')).read_bytes(),managed.read_bytes())
        self.assertEqual(row['source_sha256'],digest(managed))

    def test_duplicate_import_from_another_path_keeps_id_and_notes(self):
        import_file(self.store,self.source,self.archive)
        sid=self.store.sessions()[0]['id'];self.store.update_notes(sid,'Nota locale')
        other=self.root/'other.grt';other.write_bytes(self.source.read_bytes())
        self.assertEqual(import_file(self.store,other,self.archive),0)
        self.assertEqual(len(self.store.sessions()),1)
        self.assertEqual(self.store.session(sid)['notes'],'Nota locale')

    def test_legacy_database_sources_are_adopted_without_replacing_rows(self):
        sid=self.store.import_session(parse_any(str(self.source))[0]);self.store.update_notes(sid,'Storica')
        report=adopt_existing(self.store,self.archive)
        self.assertEqual(report,dict(copied=1,missing=0,errors=[]))
        self.assertEqual(self.store.session(sid)['notes'],'Storica')
        self.assertEqual(import_file(self.store,self.source,self.archive),0)
        self.assertEqual(len(self.store.sessions()),1)
        self.assertEqual(adopt_existing(self.store,self.archive)['copied'],0)

    def test_opens_actual_previous_schema_and_preserves_existing_session(self):
        spec=importlib.util.spec_from_file_location('previous_store',ROOT/'windows/v5.4.15.6-burst4/goats_store.py')
        previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
        path=self.root/'previous.sqlite3';old=previous.SessionStore(path)
        sid=old.import_session(parse_any(str(self.source))[0]);old.update_notes(sid,'Versione precedente');old.close()
        migrated=SessionStore(path)
        try:
            adopt_existing(migrated,self.archive)
            self.assertEqual(migrated.session(sid)['notes'],'Versione precedente')
            self.assertTrue(migrated.session(sid)['source_sha256'])
            self.assertEqual(import_file(migrated,self.source,self.archive),0)
        finally:migrated.close()

    def test_missing_legacy_source_is_reported_and_database_retained(self):
        sid=self.store.import_session(parse_any(str(self.source))[0]);self.source.unlink()
        self.assertEqual(adopt_existing(self.store,self.archive)['missing'],1)
        self.assertIsNotNone(self.store.session(sid))

    def test_delete_removes_managed_and_cloud_copies_but_not_external_original(self):
        import_file(self.store,self.source,self.archive);self.sync()
        # Legacy alias containing identical data must also be removed.
        (self.cloud/'alias.grt').write_bytes(self.source.read_bytes())
        unrelated=self.cloud/'unrelated.csv';unrelated.write_text('lat,lon\n45,9\n')
        result=delete_session(self.store,self.store.sessions()[0]['id'],self.archive,self.cloud,self.cache)
        self.assertEqual((result['deleted'],result['errors']),(1,[]))
        self.assertEqual(self.store.sessions(),[])
        self.assertFalse(list(self.archive.glob('*.grt')))
        self.assertFalse(list(self.cloud.glob('*.grt')))
        self.assertTrue(self.source.exists());self.assertTrue(unrelated.exists())
        self.assertTrue(list((self.cloud/'sessioni_eliminate').glob('*.json')))

    def test_offline_phone_copy_cannot_resurrect_a_deleted_file(self):
        import_file(self.store,self.source,self.archive);self.sync()
        phone=self.root/'phone';phone.mkdir()
        first=sync_folder(self.cloud,phone/'files',phone/'tracks',phone/'cache')
        copied=Path(first['session_files'][0]['path'])
        delete_session(self.store,self.store.sessions()[0]['id'],self.archive,self.cloud,self.cache)
        result=sync_folder(self.cloud,phone/'files',phone/'tracks',phone/'cache',[str(copied)])
        self.assertIn(str(copied),result['deleted_source_paths'])
        self.assertEqual(result['session_files'],[])
        self.assertFalse(copied.exists());self.assertFalse(list(self.cloud.glob('*.grt')))
        # A late provider copy is purged again rather than imported.
        (self.cloud/'late.grt').write_bytes(self.source.read_bytes())
        self.assertEqual(self.sync()['session_files'],[])
        self.assertFalse((self.cloud/'late.grt').exists())

    def test_offline_deletion_is_queued_and_published_on_next_sync(self):
        import_file(self.store,self.source,self.archive)
        blocked=self.root/'blocked';blocked.write_text('not a folder')
        result=delete_session(self.store,self.store.sessions()[0]['id'],self.archive,blocked,self.cache)
        self.assertTrue(result['errors']);self.assertFalse(list(self.archive.glob('*.grt')))
        self.sync();self.assertTrue(list((self.cloud/'sessioni_eliminate').glob('*.json')))
        self.assertFalse(list(self.cloud.glob('*.grt')))

    def test_physical_delete_failure_is_reported_and_retried(self):
        import_file(self.store,self.source,self.archive);self.sync()
        managed=Path(self.store.sessions()[0]['source_path']);original_unlink=Path.unlink
        def fail(path,*a,**kw):
            if path==managed:raise PermissionError('Locked test file')
            return original_unlink(path,*a,**kw)
        with patch.object(Path,'unlink',fail):
            result=delete_session(self.store,self.store.sessions()[0]['id'],self.archive,self.cloud,self.cache)
        self.assertTrue(result['errors']);self.assertTrue(managed.exists())
        self.sync();self.assertFalse(managed.exists())

    def test_invalid_deletion_record_cannot_remove_files(self):
        import_file(self.store,self.source,self.archive);self.sync()
        receipts=self.cloud/'sessioni_eliminate';receipts.mkdir(exist_ok=True)
        (receipts/'bad.json').write_text(json.dumps({'format':'GOATS_SESSION_DELETE_V1','sha256':'../../unrelated'}))
        result=self.sync();self.assertTrue(result['errors'])
        self.assertTrue(list(self.archive.glob('*.grt')))

    def test_multi_session_file_is_deleted_as_one_explicit_group(self):
        p=self.root/'multi.json'
        p.write_text(json.dumps({'sessions':[
            {'track_name':'Pista test','date':'2026-01-01','time':'10:00','laps':[]},
            {'track_name':'Pista test','date':'2026-01-01','time':'11:00','laps':[]}]}))
        self.assertEqual(import_file(self.store,p,self.archive),2)
        sid=self.store.sessions()[0]['id'];ids,h=deletion_group(self.store,sid)
        self.assertEqual(len(ids),2)
        self.assertEqual(delete_session(self.store,sid,self.archive,self.cloud,self.cache)['deleted'],2)
        self.assertEqual(self.store.sessions(),[]);self.assertTrue(p.exists())

    def test_failed_multi_import_is_not_marked_complete_and_retry_keeps_ids(self):
        p=self.root/'multi.json';p.write_text(json.dumps({'sessions':[
            {'date':'2026-01-01','time':'10:00','laps':[]},
            {'date':'2026-01-01','time':'11:00','laps':[]}]}))
        original=self.store.import_session;calls=[]
        def fail_second(session):
            calls.append(session)
            if len(calls)==2:raise RuntimeError('Synthetic interruption')
            return original(session)
        with patch.object(self.store,'import_session',side_effect=fail_second):
            with self.assertRaises(RuntimeError):import_file(self.store,p,self.archive)
        sid=self.store.sessions()[0]['id']
        adopt_existing(self.store,self.archive)
        self.assertEqual(import_file(self.store,p,self.archive),2)
        self.assertEqual(len(self.store.sessions()),2)
        self.assertIsNotNone(self.store.session(sid))


if __name__=='__main__':unittest.main(verbosity=2)
