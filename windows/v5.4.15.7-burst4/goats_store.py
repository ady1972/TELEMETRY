import sqlite3, hashlib, math
from pathlib import Path

GNSS_WEEK_MS = 604800000

class SessionStore:
    def __init__(self,path,cloud_safe=False):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        self.cloud_safe=bool(cloud_safe)
        self.conn=sqlite3.connect(self.path); self.conn.row_factory=sqlite3.Row
        # Per cartelle sincronizzate evitiamo i file -wal/-shm persistenti, che
        # i client cloud possono sincronizzare separatamente dal database.
        self.conn.execute('PRAGMA journal_mode='+('DELETE' if self.cloud_safe else 'WAL'))
        self.conn.execute('PRAGMA synchronous=FULL' if self.cloud_safe else 'PRAGMA synchronous=NORMAL')
        self.conn.execute('PRAGMA foreign_keys=ON'); self._schema()

    def close(self):
        try:self.conn.commit()
        except Exception:pass
        if not self.cloud_safe:
            try:self.conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
            except Exception:pass
        try:self.conn.close()
        except Exception:pass

    def _schema(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions(id INTEGER PRIMARY KEY AUTOINCREMENT,fingerprint TEXT UNIQUE NOT NULL,source_format TEXT,source_path TEXT,date TEXT,time TEXT,track_name TEXT,session_type TEXT,firmware TEXT,sample_rate_hz REAL,recovered INTEGER,crc32 TEXT,duration_ms INTEGER,point_count INTEGER,lap_count INTEGER,max_speed_kmh REAL,avg_speed_kmh REAL,best_lap_ms INTEGER,imported_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS points(session_id INTEGER,seq INTEGER,elapsed_ms INTEGER,latitude REAL,longitude REAL,speed_kmh REAL,heading_deg REAL,hdop REAL,satellites INTEGER,lap INTEGER,fix INTEGER,free_recording INTEGER,PRIMARY KEY(session_id,seq),FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE);
        CREATE INDEX IF NOT EXISTS idx_points_session_lap ON points(session_id,lap,seq);
        CREATE TABLE IF NOT EXISTS laps(session_id INTEGER,lap INTEGER,start_ms INTEGER,end_ms INTEGER,lap_time_ms INTEGER,max_speed_kmh REAL,avg_speed_kmh REAL,point_count INTEGER,PRIMARY KEY(session_id,lap),FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE);
        """)
        scol={row[1] for row in self.conn.execute('PRAGMA table_info(sessions)').fetchall()}
        if 'notes' not in scol:
            self.conn.execute("ALTER TABLE sessions ADD COLUMN notes TEXT DEFAULT ''")
        if 'source_sha256' not in scol:
            self.conn.execute("ALTER TABLE sessions ADD COLUMN source_sha256 TEXT DEFAULT ''")
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_sessions_source_sha ON sessions(source_sha256)')
        self.conn.execute('CREATE TABLE IF NOT EXISTS session_file_imports(sha256 TEXT PRIMARY KEY,complete INTEGER NOT NULL)')
        pcols={row[1] for row in self.conn.execute('PRAGMA table_info(points)').fetchall()}
        additions=(
            ('gnss_itow_ms','INTEGER DEFAULT 0'),('nav_seq','INTEGER DEFAULT 0'),
            ('pvt_hz','REAL DEFAULT 0'),('laptimer_hz','REAL DEFAULT 0'),('csv_hz','REAL DEFAULT 0'),
            ('finish_signed_m','REAL'),('finish_window','INTEGER DEFAULT 0'))
        for name,typ in additions:
            if name not in pcols:
                self.conn.execute(f'ALTER TABLE points ADD COLUMN {name} {typ}')
        self.conn.commit()

    def _fp(self,s):
        return hashlib.sha256(f'{s.source_format}|{s.source_path}|{s.date}|{s.time}|{s.track_name}|{len(s.points)}|{s.crc32}'.encode()).hexdigest()

    @staticmethod
    def _point_diag_tuple(p):
        fs=getattr(p,'finish_signed_m',float('nan'))
        try: fs=float(fs)
        except Exception: fs=float('nan')
        if not math.isfinite(fs): fs=None
        return (
            int(getattr(p,'gnss_itow_ms',0) or 0), int(getattr(p,'nav_seq',0) or 0),
            float(getattr(p,'pvt_hz',0.0) or 0.0), float(getattr(p,'laptimer_hz',0.0) or 0.0),
            float(getattr(p,'csv_hz',0.0) or 0.0), fs, int(getattr(p,'finish_window',0) or 0))

    def import_session(self,s):
        fp=self._fp(s)
        row=self.conn.execute('SELECT id FROM sessions WHERE fingerprint=?',(fp,)).fetchone()
        laps=self._laps(s); pts=s.points
        duration=max((p.elapsed_ms for p in pts),default=int(s.legacy_summary.get('duration_ms',0) or 0))
        vmax=max((p.speed_kmh for p in pts),default=float(s.legacy_summary.get('max_speed_kmh',0) or 0))
        vavg=sum((p.speed_kmh for p in pts),0.0)/len(pts) if pts else float(s.legacy_summary.get('average_speed_kmh',0) or 0)
        best=min((x['lap_time_ms'] for x in laps if x['lap_time_ms']>0),default=int(s.legacy_summary.get('best_lap_ms',0) or 0))
        with self.conn:
            if row:
                sid=int(row['id'])
                self.conn.execute('DELETE FROM points WHERE session_id=?',(sid,))
                self.conn.execute('DELETE FROM laps WHERE session_id=?',(sid,))
                self.conn.execute('UPDATE sessions SET source_format=?,source_path=?,date=?,time=?,track_name=?,session_type=?,firmware=?,sample_rate_hz=?,recovered=?,crc32=?,duration_ms=?,point_count=?,lap_count=?,max_speed_kmh=?,avg_speed_kmh=?,best_lap_ms=? WHERE id=?',
                    (s.source_format,s.source_path,s.date,s.time,s.track_name,s.session_type,s.firmware,s.sample_rate_hz,s.recovered,s.crc32,duration,len(pts),len(laps),vmax,vavg,best,sid))
            else:
                cur=self.conn.execute('INSERT INTO sessions(fingerprint,source_format,source_path,date,time,track_name,session_type,firmware,sample_rate_hz,recovered,crc32,duration_ms,point_count,lap_count,max_speed_kmh,avg_speed_kmh,best_lap_ms) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    (fp,s.source_format,s.source_path,s.date,s.time,s.track_name,s.session_type,s.firmware,s.sample_rate_hz,s.recovered,s.crc32,duration,len(pts),len(laps),vmax,vavg,best))
                sid=cur.lastrowid
            sql='INSERT INTO points(session_id,seq,elapsed_ms,latitude,longitude,speed_kmh,heading_deg,hdop,satellites,lap,fix,free_recording,gnss_itow_ms,nav_seq,pvt_hz,laptimer_hz,csv_hz,finish_signed_m,finish_window) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'
            chunk=[]
            for i,p in enumerate(pts):
                chunk.append((sid,i,p.elapsed_ms,p.latitude,p.longitude,p.speed_kmh,p.heading_deg,p.hdop,p.satellites,p.lap,p.fix,p.free_recording)+self._point_diag_tuple(p))
                if len(chunk)>=5000:
                    self.conn.executemany(sql,chunk); chunk=[]
            if chunk:self.conn.executemany(sql,chunk)
            for x in laps:
                self.conn.execute('INSERT INTO laps VALUES(?,?,?,?,?,?,?,?)',(sid,x['lap'],x['start_ms'],x['end_ms'],x['lap_time_ms'],x['max_speed_kmh'],x['avg_speed_kmh'],x['point_count']))
        return int(sid)

    @staticmethod
    def _gnss_delta_ms(a,b):
        a=int(a or 0); b=int(b or 0)
        if a<=0 or b<=0:return None
        d=(b-a)%GNSS_WEEK_MS
        return d if d<=10000 else None

    @classmethod
    def _cross_between(cls,a,b,allow_extrapolate=False):
        try:
            da=float(getattr(a,'finish_signed_m',float('nan')))
            db=float(getattr(b,'finish_signed_m',float('nan')))
        except Exception:return None
        if not (math.isfinite(da) and math.isfinite(db)) or abs(db-da)<1e-9:return None
        if da==0.0:f=0.0
        elif db==0.0:f=1.0
        elif da*db<=0.0:f=-da/(db-da)
        elif allow_extrapolate:
            f=-da/(db-da)
            if not (-1.5<=f<=0.5):return None
        else:return None
        if not allow_extrapolate and not (0.0<=f<=1.0):return None
        if abs(da)>25.0 or abs(db)>25.0:return None
        elapsed=float(a.elapsed_ms)+f*(float(b.elapsed_ms)-float(a.elapsed_ms))
        gd=cls._gnss_delta_ms(getattr(a,'gnss_itow_ms',0),getattr(b,'gnss_itow_ms',0))
        itow=None
        if gd is not None:
            itow=(float(getattr(a,'gnss_itow_ms',0))+f*gd)%GNSS_WEEK_MS
        return {'elapsed':elapsed,'itow':itow,'fraction':f}

    @classmethod
    def _duration_cross_ms(cls,start,end):
        if start and end and start.get('itow') is not None and end.get('itow') is not None:
            d=(end['itow']-start['itow'])%GNSS_WEEK_MS
            if 1000.0<=d<=600000.0:return int(round(d))
        if start and end:return max(0,int(round(end['elapsed']-start['elapsed'])))
        return 0

    @classmethod
    def _sd_crossing_laps(cls,s,ordered):
        pts_all=list(s.points)
        if len(pts_all)<3 or len(ordered)<2:return None
        diag=0
        for p in pts_all:
            try: valid=bool(getattr(p,'gnss_itow_ms',0)) and math.isfinite(float(getattr(p,'finish_signed_m',float('nan'))))
            except Exception: valid=False
            diag+=1 if valid else 0
        if diag<max(10,int(len(pts_all)*0.5)):return None
        first_idx={}
        for i,p in enumerate(pts_all):
            if p.lap>0 and p.lap not in first_idx:first_idx[p.lap]=i
        first_lap=ordered[0][0]; fi=first_idx.get(first_lap,0)
        start_cross=None
        cand=pts_all[fi:min(len(pts_all),fi+8)]
        for j in range(len(cand)-1):
            c=cls._cross_between(cand[j],cand[j+1],True)
            if c is not None and c['fraction']<=0.25:
                start_cross=c; break
        if start_cross is None:
            p0=pts_all[fi]
            start_cross={'elapsed':float(p0.elapsed_ms),'itow':float(p0.gnss_itow_ms) if getattr(p0,'gnss_itow_ms',0) else None,'fraction':0.0}
        out=[]; prev=start_cross
        for idx,(lap,lappts) in enumerate(ordered[:-1]):
            bi=first_idx.get(ordered[idx+1][0])
            if bi is None:break
            best=None; bestdist=10**9
            for j in range(max(1,bi-12),min(len(pts_all)-1,bi+12)+1):
                c=cls._cross_between(pts_all[j-1],pts_all[j],False)
                if c is not None and abs(j-bi)<bestdist:
                    best=c; bestdist=abs(j-bi)
            if best is None:
                pn=pts_all[bi]
                best={'elapsed':float(pn.elapsed_ms),'itow':float(pn.gnss_itow_ms) if getattr(pn,'gnss_itow_ms',0) else None,'fraction':0.0}
            lap_ms=cls._duration_cross_ms(prev,best)
            out.append(dict(lap=int(lap),start_ms=max(0,int(round(prev['elapsed']))),end_ms=max(0,int(round(best['elapsed']))),lap_time_ms=lap_ms,max_speed_kmh=max(x.speed_kmh for x in lappts),avg_speed_kmh=sum(x.speed_kmh for x in lappts)/len(lappts),point_count=len(lappts)))
            prev=best
        return out

    def _laps(self,s):
        if s.legacy_laps:
            return [dict(lap=int(x['number']),start_ms=0,end_ms=int(x['lap_time_ms']),lap_time_ms=int(x['lap_time_ms']),max_speed_kmh=float(x.get('max_speed_kmh',0)),avg_speed_kmh=float(x.get('average_speed_kmh',0)),point_count=int(x.get('point_count',0))) for x in s.legacy_laps if int(x.get('number',0))>0]
        groups={}
        for p in s.points:
            if p.lap>0:groups.setdefault(p.lap,[]).append(p)
        ordered=sorted(groups.items()); out=[]
        if s.source_format=='SDCSV':
            cross=self._sd_crossing_laps(s,ordered)
            if cross is not None:return cross
            for i,(lap,pts) in enumerate(ordered[:-1]):
                next_pts=ordered[i+1][1]; start=int(pts[0].elapsed_ms); end=int(next_pts[0].elapsed_ms)
                out.append(dict(lap=int(lap),start_ms=start,end_ms=end,lap_time_ms=max(0,end-start),max_speed_kmh=max(x.speed_kmh for x in pts),avg_speed_kmh=sum(x.speed_kmh for x in pts)/len(pts),point_count=len(pts)))
            return out
        for lap,pts in ordered:
            start,end=pts[0].elapsed_ms,pts[-1].elapsed_ms
            out.append(dict(lap=lap,start_ms=start,end_ms=end,lap_time_ms=max(0,end-start),max_speed_kmh=max(x.speed_kmh for x in pts),avg_speed_kmh=sum(x.speed_kmh for x in pts)/len(pts),point_count=len(pts)))
        return out

    def sessions(self,search=''):
        if search:return self.conn.execute('SELECT * FROM sessions WHERE track_name LIKE ? OR date LIKE ? OR session_type LIKE ? OR notes LIKE ? ORDER BY id DESC',tuple([f'%{search}%']*4)).fetchall()
        return self.conn.execute('SELECT * FROM sessions ORDER BY id DESC').fetchall()
    def session(self,sid):return self.conn.execute('SELECT * FROM sessions WHERE id=?',(sid,)).fetchone()
    def update_notes(self,sid,notes):
        with self.conn:self.conn.execute('UPDATE sessions SET notes=? WHERE id=?',(str(notes or ''),int(sid)))
    def laps(self,sid):return self.conn.execute('SELECT * FROM laps WHERE session_id=? ORDER BY lap',(sid,)).fetchall()
    def points(self,sid,lap=None):
        return self.conn.execute('SELECT * FROM points WHERE session_id=?'+(' AND lap=?' if lap is not None else '')+' ORDER BY seq',(sid,lap) if lap is not None else (sid,)).fetchall()
    def delete(self,sid):
        with self.conn:self.conn.execute('DELETE FROM sessions WHERE id=?',(sid,))
