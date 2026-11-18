from __future__ import annotations
import json, struct, zlib, csv, re, datetime
from dataclasses import dataclass
from pathlib import Path

GRT8_HEADER = struct.Struct('<4sHHHHIIIIII B3x 11s9s64s32s100s')
GRT8_RECORD = struct.Struct('<IiiHHHHBB')

@dataclass
class Point:
    elapsed_ms:int; latitude:float; longitude:float; speed_kmh:float
    heading_deg:float=0.0; hdop:float=0.0; satellites:int=0; lap:int=0; fix:int=1; free_recording:int=0
    gnss_itow_ms:int=0; nav_seq:int=0; pvt_hz:float=0.0; laptimer_hz:float=0.0; csv_hz:float=0.0
    finish_signed_m:float=float('nan'); finish_window:int=0

@dataclass
class ParsedSession:
    source_format:str; source_path:str; date:str; time:str; track_name:str; session_type:str
    firmware:str; sample_rate_hz:float; recovered:int; crc32:str; points:list[Point]
    legacy_laps:list[dict]; legacy_summary:dict

def _cstr(raw:bytes)->str:
    return raw.split(b'\0',1)[0].decode('utf-8',errors='replace').strip()

def sniff_format(path):
    p=Path(path)
    magic=p.read_bytes()[:4]
    if magic==b'GRT8': return 'GRT8'
    if magic==b'GSA3': return 'GSA3'
    if magic==b'GSA2': return 'GSA2'
    if p.suffix.lower()=='.json': return 'JSON'
    if p.suffix.lower()=='.csv': return 'SDCSV'
    raise ValueError(f'Formato non riconosciuto: {magic!r}')

def parse_grt8(path):
    p=Path(path); points=[]
    with p.open('rb') as f:
        raw=f.read(GRT8_HEADER.size)
        if len(raw)!=GRT8_HEADER.size: raise ValueError('Header GRT8 troncato')
        vals=GRT8_HEADER.unpack(raw)
        magic,version,header_size,record_size,sample_hz,flags,start_ms,end_ms,record_count,checkpoint_count,data_crc,stype,date_b,time_b,track_b,firmware_b,_=vals
        if magic!=b'GRT8' or version!=1: raise ValueError('Versione GRT8 non supportata')
        if header_size!=256 or record_size not in (22,24): raise ValueError(f'Layout GRT8 non supportato: record {record_size}')
        payload=bytearray()
        while True:
            b=f.read(record_size)
            if not b: break
            if len(b)!=record_size: break
            payload.extend(b)
            elapsed,lat,lon,speed10,heading10,hdop100,lap,sats,rf=GRT8_RECORD.unpack(b[:GRT8_RECORD.size])
            points.append(Point(elapsed,lat/1e7,lon/1e7,speed10/10.0,heading10/10.0,hdop100/100.0,sats,lap,1 if rf&1 else 0,1 if rf&2 else 0))
    calc=zlib.crc32(payload)&0xffffffff if payload else 0
    return ParsedSession('GRT8',str(p),_cstr(date_b),_cstr(time_b),_cstr(track_b) or 'Circuito','FREE' if stype==1 else 'CIRCUIT',_cstr(firmware_b),float(sample_hz or 25),1 if flags&2 else 0,f'{data_crc:08X}' if data_crc else '',points,[],{'header_record_count':record_count,'parsed_record_count':len(points),'crc_ok': calc==data_crc if data_crc and payload else None})

def _parse_gsa_blob(data:bytes,source_path=''):
    off=0
    def take(fmt):
        nonlocal off
        n=struct.calcsize(fmt)
        if off+n>len(data): raise ValueError('Archivio sessioni troncato')
        v=struct.unpack_from(fmt,data,off); off+=n
        return v[0] if len(v)==1 else v
    def text():
        nonlocal off
        n=take('<B'); s=data[off:off+n].decode('utf-8',errors='replace'); off+=n; return s
    magic=data[:4]
    if magic not in (b'GSA2',b'GSA3'): raise ValueError('Formato GSA non riconosciuto')
    off=4; version,count=take('<HH')
    if magic==b'GSA2' and version not in (1,2): raise ValueError(f'GSA2 v{version} non supportato')
    if magic==b'GSA3' and version!=3: raise ValueError(f'GSA3 v{version} non supportato')
    out=[]
    for _ in range(count):
        sid=take('<I'); date=text(); tm=text(); track=text(); duration,best,last=take('<III'); vmax,vavg,hdop,sats=take('<ffff'); nlap=take('<H')
        laps=[]; points=[]
        for _ in range(nlap):
            number=take('<H'); lap_ms=take('<I'); lmax,lavg=take('<ff'); ntrace=take('<H') if version>=2 else 0
            trace=[]
            for _ in range(ntrace):
                lat,lon=take('<ii'); tick,speed10=take('<HH'); elapsed=tick*(40 if magic==b'GSA3' else 100)
                pt=Point(elapsed,lat/1e7,lon/1e7,speed10/10.0,lap=number,free_recording=1 if track=='REGISTRAZIONE LIBERA' else 0)
                trace.append(pt); points.append(pt)
            laps.append({'number':number,'lap_time_ms':lap_ms,'max_speed_kmh':lmax,'average_speed_kmh':lavg,'point_count':len(trace)})
        out.append(ParsedSession(magic.decode(),source_path,date,tm,track,'FREE' if track=='REGISTRAZIONE LIBERA' else 'CIRCUIT','Legacy',25.0 if magic==b'GSA3' else 10.0,0,'',points,laps,{'session_id':sid,'duration_ms':duration,'best_lap_ms':best,'last_lap_ms':last,'max_speed_kmh':vmax,'average_speed_kmh':vavg,'average_hdop':hdop,'average_satellites':sats}))
    return out

def parse_json(path):
    p=Path(path); obj=json.loads(p.read_text(encoding='utf-8')); sessions=obj.get('sessions',[obj]) if isinstance(obj,dict) else obj; out=[]
    for s in sessions:
        points=[]; laps=[]
        for lap in s.get('laps',[]):
            n=int(lap.get('number',0) or 0); trace=lap.get('trace',[]) or []
            for t in trace: points.append(Point(int(t.get('elapsed_ms',0) or 0),float(t.get('latitude',0)),float(t.get('longitude',0)),float(t.get('speed_kmh',0)),lap=n))
            laps.append({'number':n,'lap_time_ms':int(lap.get('lap_time_ms',0) or 0),'max_speed_kmh':float(lap.get('max_speed_kmh',0) or 0),'average_speed_kmh':float(lap.get('average_speed_kmh',0) or 0),'point_count':len(trace)})
        track=str(s.get('track_name','Circuito'))
        out.append(ParsedSession('JSON',str(p),str(s.get('date','')),str(s.get('time','')),track,'FREE' if track.upper()=='REGISTRAZIONE LIBERA' else 'CIRCUIT','Legacy JSON',0,0,'',points,laps,s))
    return out


def parse_sd_csv(path):
    """Importa direttamente Sxxxxxx.CSV prodotto dalla telemetria GOATS."""
    p = Path(path)
    raw = p.read_text(encoding='utf-8-sig', errors='replace')
    lines = raw.splitlines()
    meta = {}
    data_lines = []

    # I commenti iniziali, se presenti, vengono conservati come metadati.
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith('#'):
            body = stripped[1:].strip()

            # Firmware GOATS writes metadata on one line:
            # # mode=CIRCUIT,date=26/08/2026,time=08:21,track=...
            # Parse every key=value pair, not only the first one.
            if '=' in body:
                for part in body.split(','):
                    if '=' not in part:
                        continue
                    key, value = part.split('=', 1)
                    key = key.strip().lower().replace(' ', '_')
                    if key:
                        meta[key] = value.strip()
            else:
                m = re.match(r'([^:]+)\s*:\s*(.*)$', body)
                if m:
                    meta[m.group(1).strip().lower().replace(' ', '_')] = m.group(2).strip()
            continue
        data_lines.append(line)

    if not data_lines:
        raise ValueError('CSV vuoto o senza intestazione')

    # Rileva automaticamente ; oppure ,.
    header = data_lines[0]
    delimiter = ';' if header.count(';') > header.count(',') else ','
    reader = csv.DictReader(data_lines, delimiter=delimiter)
    if not reader.fieldnames:
        raise ValueError('Intestazione CSV non riconosciuta')

    def norm(k):
        return str(k or '').strip().lower().replace(' ', '_')

    field_map = {norm(k): k for k in reader.fieldnames}

    def val(row, *names, default=''):
        for name in names:
            key = field_map.get(norm(name))
            if key is not None:
                v = row.get(key)
                if v not in (None, ''):
                    return v
        return default

    def fnum(v, default=0.0):
        try:
            return float(str(v).strip().replace(',', '.'))
        except Exception:
            return default

    points = []
    first_abs = None
    for row in reader:
        lat = fnum(val(row, 'latitude', 'lat', 'latitude_deg', 'gps_lat', 'lat_deg', 'lat_e7', 'latitude_e7'))
        lon = fnum(val(row, 'longitude', 'lon', 'lng', 'longitude_deg', 'gps_lon', 'lon_deg', 'lon_e7', 'longitude_e7'))
        # Alcuni export salvano le coordinate come interi E7.
        if abs(lat) > 90 and abs(lat) <= 900000000:
            lat /= 1e7
        if abs(lon) > 180 and abs(lon) <= 1800000000:
            lon /= 1e7
        # Scarta righe senza coordinate reali.
        if not (-90 <= lat <= 90 and -180 <= lon <= 180) or (lat == 0 and lon == 0):
            continue

        elapsed = int(fnum(val(row, 'elapsed_ms', 'elapsed', 'time_ms', 'ms')))
        if first_abs is None:
            first_abs = elapsed
        # Se il CSV contiene timestamp assoluti, normalizza la sessione a zero.
        if elapsed > 86400000 and first_abs is not None:
            elapsed -= first_abs

        lap = int(fnum(val(row, 'lap', 'giro', 'lap_number')))
        speed = fnum(val(row, 'speed_kmh', 'speed', 'velocita_kmh', 'velocity_kmh'))
        heading = fnum(val(row, 'heading_deg', 'heading', 'course_deg', 'course'))
        hdop = fnum(val(row, 'hdop'))
        sats = int(fnum(val(row, 'satellites', 'sats', 'sat')))
        fix = int(fnum(val(row, 'fix'), 1))
        free = int(fnum(val(row, 'free_recording', 'free'), 1 if lap <= 0 else 0))
        gnss_itow = int(fnum(val(row, 'gnss_itow_ms', 'itow_ms', 'itow')))
        nav_seq = int(fnum(val(row, 'nav_seq', 'nav_counter')))
        pvt_hz = fnum(val(row, 'pvt_hz'))
        laptimer_hz = fnum(val(row, 'laptimer_hz'))
        csv_hz = fnum(val(row, 'csv_hz'))
        finish_raw = val(row, 'finish_signed_m', default='')
        try:
            finish_signed = float(str(finish_raw).strip().replace(',', '.')) if str(finish_raw).strip() else float('nan')
        except Exception:
            finish_signed = float('nan')
        finish_window = int(fnum(val(row, 'finish_window'), 0))
        points.append(Point(elapsed, lat, lon, speed, heading, hdop, sats, lap, fix, free,
                            gnss_itow, nav_seq, pvt_hz, laptimer_hz, csv_hz, finish_signed, finish_window))

    if not points:
        raise ValueError('Nessun punto GPS valido trovato nel CSV')

    # Metadati: usa quelli del file quando presenti; altrimenti dati ragionevoli
    # derivati dal file stesso senza impedire l'analisi della traccia.
    date = meta.get('date') or meta.get('data') or ''
    tm = meta.get('time') or meta.get('ora') or ''
    track = (meta.get('track_name') or meta.get('track') or
             meta.get('circuito') or meta.get('circuit') or '')
    mode = (meta.get('mode') or '').strip().upper()
    firmware = meta.get('firmware') or 'GOATS RT V11 CSV'

    # Keep the date/time recorded by the laptimer. FAT file timestamps are only
    # a last-resort fallback and can be invalid (e.g. 1979 after USB copy).
    if date:
        for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d'):
            try:
                d = datetime.datetime.strptime(date, fmt)
                date = d.strftime('%d/%m/%Y')
                break
            except ValueError:
                pass
    else:
        dt = datetime.datetime.fromtimestamp(p.stat().st_mtime)
        # Reject obviously invalid FAT/USB timestamps.
        if dt.year >= 2000:
            date = dt.strftime('%d/%m/%Y')
            if not tm:
                tm = dt.strftime('%H:%M:%S')
        else:
            date = 'DATA CSV'

    if tm and len(tm) == 5:
        tm += ':00'

    positive_laps = sorted({pt.lap for pt in points if pt.lap > 0})
    is_free = (mode == 'FREE') or (not positive_laps and mode != 'CIRCUIT')
    if not track:
        track = 'REGISTRAZIONE LIBERA' if is_free else 'CIRCUITO DA CSV'

    # Per una registrazione libera assegna lap 0: il Manager visualizza comunque
    # la "Traccia completa"; per i circuiti conserva i numeri giro del firmware.
    duration = max((pt.elapsed_ms for pt in points), default=0)
    return ParsedSession(
        'SDCSV', str(p), date, tm, track,
        'FREE' if is_free else 'CIRCUIT',
        firmware, 25.0, 0, '', points, [],
        {
            'duration_ms': duration,
            'source_file': p.name,
            'csv_metadata': meta,
            'parsed_record_count': len(points),
        }
    )


def parse_any(path):
    fmt=sniff_format(path)
    if fmt=='GRT8': return [parse_grt8(path)]
    if fmt in ('GSA2','GSA3'): return _parse_gsa_blob(Path(path).read_bytes(),str(path))
    if fmt=='SDCSV': return [parse_sd_csv(path)]
    return parse_json(path)
