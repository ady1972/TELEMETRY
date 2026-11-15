import base64
import importlib.util
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zlib

REPO = Path(__file__).resolve().parents[2]
# Run separately per platform to keep the original same-named modules isolated.
if len(sys.argv) < 2 or sys.argv[1] not in ('windows', 'mobile'):
    raise SystemExit('Usage: python tests/mobile_windows/verify_import.py windows|mobile')
MODE = sys.argv.pop(1)
MOBILE = REPO / 'mobile/v0.2.1'
WINDOWS = REPO / 'windows/v5.4.15.4-burst4'
MOBILE_ENGINE = MOBILE / 'fullapp/src/main/python'
ROOT = WINDOWS if MODE == 'windows' else MOBILE_ENGINE
sys.path.insert(0, str(ROOT))
from goats_formats import parse_any
from goats_store import SessionStore
from goats_exporters import export_csv, export_json, export_gpx


def load_alias(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class MigrationChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.tmp = Path(self.temp.name)

    def fixture_csv(self, separator=','):
        path = self.tmp / 'session.csv'
        header = ['elapsed_ms','latitude','longitude','speed_kmh','heading_deg','hdop','satellites','lap','fix','free_recording','gnss_itow_ms','nav_seq','pvt_hz','laptimer_hz','csv_hz','finish_signed_m','finish_window']
        rows = [separator.join(header)]
        for i in range(100):
            rows.append(separator.join(map(str,[i*40,45+i/1e6,9+i/1e6,50+i/10,90,0.8,12,1 if i<50 else 2,1,0,100000+i*40,i,25,25,25,-1 if i<50 else 1,1])))
        path.write_text('# mode=CIRCUIT,date=2026-11-15,time=10:00,track=SYNTHETIC\n'+'\n'.join(rows))
        return path

    def test_01_bundled_grt8(self):
        s = parse_any(WINDOWS/'sample_test.grt')[0]
        self.assertEqual((s.source_format,s.track_name,len(s.points)),('GRT8','TEST',50))
        self.assertTrue(s.legacy_summary['crc_ok'])
        self.assertEqual(s.points[-1].elapsed_ms,1960)

    def test_02_csv_metadata_diagnostics_and_completed_lap(self):
        s = parse_any(self.fixture_csv())[0]
        self.assertEqual((s.date,s.time,s.track_name,s.sample_rate_hz),('15/11/2026','10:00:00','SYNTHETIC',25))
        self.assertEqual((len(s.points),s.points[1].gnss_itow_ms,s.points[1].csv_hz),(100,100040,25))
        store = SessionStore(self.tmp/'sessions.db')
        self.addCleanup(getattr(store,"close",store.conn.close))
        sid = store.import_session(s)
        self.assertEqual(len(store.laps(sid)),1)
        self.assertEqual(store.laps(sid)[0]['lap_time_ms'],1980)

    def test_03_csv_semicolon(self):
        self.assertEqual(len(parse_any(self.fixture_csv(';'))[0].points),100)

    def test_04_legacy_gsa_versions(self):
        def text(value):
            raw=value.encode();return bytes([len(raw)])+raw
        for magic,version in ((b'GSA2',1),(b'GSA2',2),(b'GSA3',3)):
            with self.subTest(magic=magic,version=version):
                raw=magic+struct.pack('<HHI',version,1,1)
                raw+=text('15/11/2026')+text('10:00')+text('SYNTHETIC')
                raw+=struct.pack('<IIIffffH',5000,5000,5000,60.,50.,0.8,12.,1)
                raw+=struct.pack('<HIff',1,5000,60.,50.)
                if version>=2:raw+=struct.pack('<HiiHH',1,450000000,90000000,10,500)
                path=self.tmp/'legacy.bin';path.write_bytes(raw)
                s=parse_any(path)[0]
                self.assertEqual(s.legacy_laps[0]['lap_time_ms'],5000)
                self.assertEqual(len(s.points),int(version>=2))
                if version>=2:self.assertEqual(s.points[0].elapsed_ms,400 if version==3 else 1000)

    def test_05_legacy_json(self):
        path=self.tmp/'session.json'
        path.write_text(json.dumps({'date':'15/11/2026','track_name':'SYNTHETIC','laps':[{'number':1,'lap_time_ms':5000,'trace':[{'elapsed_ms':0,'latitude':45.,'longitude':9.,'speed_kmh':50.}]}]}))
        s=parse_any(path)[0]
        self.assertEqual((len(s.points),s.legacy_laps[0]['lap_time_ms']),(1,5000))

    def test_06_sqlite_notes_reimport_delete(self):
        s=parse_any(self.fixture_csv())[0]
        store=SessionStore(self.tmp/'archive.sqlite3', **({'cloud_safe':True} if MODE=='windows' else {}))
        self.addCleanup(getattr(store,"close",store.conn.close))
        sid=store.import_session(s);store.update_notes(sid,'synthetic note')
        self.assertEqual(store.import_session(s),sid)
        self.assertEqual(len(store.sessions()),1)
        self.assertEqual(store.session(sid)['notes'],'synthetic note')
        self.assertEqual(store.conn.execute('PRAGMA journal_mode').fetchone()[0],'delete' if MODE=='windows' else 'wal')
        self.assertEqual(len(store.points(sid)),100)
        store.delete(sid)
        self.assertEqual(len(store.points(sid)),0)
        self.assertEqual(len(store.laps(sid)),0)

    def test_07_exports_and_csv_reimport(self):
        store=SessionStore(self.tmp/'archive.sqlite3');self.addCleanup(getattr(store,"close",store.conn.close))
        sid=store.import_session(parse_any(self.fixture_csv())[0])
        s=store.session(sid);points=store.points(sid)
        export_csv(s,points,self.tmp/'out.csv')
        self.assertEqual(len(parse_any(self.tmp/'out.csv')[0].points),100)
        export_json(s,points,self.tmp/'out.json')
        self.assertEqual(len(json.loads((self.tmp/'out.json').read_text())['points']),100)
        export_gpx(s,points,self.tmp/'out.gpx')
        doc=ET.parse(self.tmp/'out.gpx')
        self.assertEqual(len(doc.findall('.//{http://www.topografix.com/GPX/1/1}trkpt')),100)

    @unittest.skipUnless(MODE=='mobile','Android bridge')
    def test_08_android_bridge_crud_and_catalog(self):
        import android_bridge as bridge
        bridge.init_app(str(self.tmp));self.addCleanup(bridge._STORE.conn.close)
        imported=json.loads(bridge.import_file(str(WINDOWS/'sample_test.grt')))
        sid=imported['sessions'][0]['id']
        self.assertEqual(len(json.loads(bridge.analysis_json(sid))['points']),50)
        bridge.set_session_notes(sid,'synthetic note')
        self.assertEqual(json.loads(bridge.sessions_json())[0]['notes'],'synthetic note')
        track=json.loads((ROOT/'default_tracks/esempio.json').read_text())
        track['name']='SYNTHETIC';track['id']='synthetic'
        track['sectors']=[dict(name='Split',lat1=45.,lon1=9.,lat2=45.0001,lon2=9.0001)]
        self.assertEqual(json.loads(bridge.save_track_json(json.dumps(track)))['real_sectors'],2)
        existing=bridge._build_catalog([json.loads((ROOT/'default_tracks/esempio.json').read_text())])
        merged=json.loads(bridge.prepare_merged_catalog(base64.b64encode(existing).decode(),'["synthetic"]'))
        payload=base64.b64decode(merged['payload_b64'])
        self.assertEqual((merged['total'],merged['preserved']),(2,1))
        self.assertEqual(merged['crc32'],f'{zlib.crc32(payload)&0xffffffff:08X}')
        repeat=json.loads(bridge.prepare_merged_catalog(merged['payload_b64'],'["synthetic"]'))
        self.assertEqual((repeat['total'],repeat['updated']),(2,1))
        bridge.delete_track('synthetic');self.assertFalse(json.loads(bridge.track_json('synthetic'))['ok'])
        bridge.delete_session(sid);self.assertEqual(json.loads(bridge.sessions_json()),[])

    @unittest.skipUnless(MODE=='windows','Cross-platform GTC3 using Qt imports')
    def test_09_cross_platform_gtc3(self):
        from goats_track_editor import TrackManager
        bridge=load_alias('mobile_bridge',MOBILE_ENGINE/'android_bridge.py')
        track=json.loads((WINDOWS/'tracks/esempio.json').read_text())
        track['sectors']=[dict(name='Split',lat1=45.,lon1=9.,lat2=45.001,lon2=9.001)]
        payload,count=TrackManager.build_binary_catalog(TrackManager,tracks=[track])
        self.assertEqual(count,1)
        self.assertEqual(payload,bridge._build_catalog([track]))
        self.assertEqual(TrackManager.parse_binary_catalog(payload),bridge._parse_catalog(payload))

    @unittest.skipUnless(MODE=='windows','Windows transport')
    def test_10_burst_and_legacy_crc_transfer(self):
        from goats_test23_protocol import fetch_file
        class Port:
            def __init__(self,data,burst,bad_crc=False):
                self.data=data;self.burst=burst;self.bad_crc=bad_crc;self.commands=[];self.pending=[];self.offset=0;self.timeout=12
            def write(self,command):
                text=command.decode().strip();self.commands.append(text)
                if text.startswith('GSD_GET '):self.pending.append(f'GSD_BEGIN {len(self.data)}\n'.encode())
                elif text=='GSD_CAPS':self.pending.append(b'GSD_CAPS BURST4=1\n' if self.burst else b'GSD_ERR UNKNOWN\n')
                elif text in ('GSD_NEXT','GSD_NEXT4'):
                    if self.offset==len(self.data):self.pending.append(f'GSD_END {(zlib.crc32(self.data)+(1 if self.bad_crc else 0))&0xffffffff:08X}\n'.encode())
                    else:
                        for _ in range(4 if text=='GSD_NEXT4' else 1):
                            chunk=self.data[self.offset:self.offset+1024]
                            if not chunk:break
                            self.offset+=len(chunk);self.pending.append(b'GSD '+chunk.hex().encode()+b'\n')
            def readline(self):return self.pending.pop(0)
            def flush(self):pass
        data=bytes(range(256))*21
        for burst in (False,True):
            with self.subTest(burst=burst):
                p=Port(data,burst);target=self.tmp/f'{burst}.csv'
                fetch_file(p,'ROOT:S000001.CSV',target,lambda *args:None)
                self.assertEqual(target.read_bytes(),data)
                self.assertEqual('GSD_NEXT4' in p.commands,burst)
        p=Port(data,True,bad_crc=True);target=self.tmp/'bad.csv'
        with self.assertRaises(RuntimeError):fetch_file(p,'ROOT:S000001.CSV',target,lambda *args:None)
        self.assertFalse(target.exists());self.assertFalse(target.with_suffix('.csv.part').exists())
        self.assertEqual(p.commands[-1],'GSD_CANCEL')

    @unittest.skipUnless(MODE=='windows','Windows path validation')
    def test_11_remote_path_validation(self):
        from goats_serial_sessions import local_relative_path
        self.assertEqual(local_relative_path('ROOT:S000001.CSV'),Path('S000001.CSV'))
        self.assertEqual(local_relative_path('ROOT:GOATS/S000001.CSV'),Path('GOATS/S000001.CSV'))
        for name in ('../secret','ROOT:../secret','C:/secret','ROOT:/../secret','a//b'):
            with self.subTest(name=name),self.assertRaises(RuntimeError):local_relative_path(name)

    def test_12_cross_platform_sqlite_schema(self):
        other = MOBILE_ENGINE if MODE=='windows' else WINDOWS
        other_store=load_alias('other_store',other/'goats_store.py').SessionStore
        path=self.tmp/'migrated.sqlite3'
        store=SessionStore(path)
        sid=store.import_session(parse_any(self.fixture_csv())[0])
        store.update_notes(sid,'preserved note');store.conn.close()
        migrated=other_store(path);self.addCleanup(migrated.conn.close)
        self.assertEqual((migrated.session(sid)['notes'],len(migrated.points(sid))),('preserved note',100))
        self.assertEqual(migrated.points(sid)[1]['gnss_itow_ms'],100040)
        self.assertEqual(migrated.laps(sid)[0]['lap_time_ms'],1980)

    def test_13_cross_platform_csv_semantics(self):
        from dataclasses import asdict
        other = MOBILE_ENGINE if MODE=='windows' else WINDOWS
        formats=load_alias('other_formats',other/'goats_formats.py')
        path=self.fixture_csv()
        left,right=parse_any(path)[0],formats.parse_any(path)[0]
        self.assertEqual((left.date,left.time,left.track_name),(right.date,right.time,right.track_name))
        self.assertEqual([asdict(p) for p in left.points],[asdict(p) for p in right.points])


unittest.main(verbosity=2)
