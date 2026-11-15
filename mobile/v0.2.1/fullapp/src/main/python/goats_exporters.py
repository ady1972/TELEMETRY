import csv,json
from pathlib import Path
from xml.sax.saxutils import escape

def export_csv(session,points,path):
    with open(path,'w',newline='',encoding='utf-8') as f:
        w=csv.writer(f,delimiter=';'); w.writerow(['elapsed_ms','latitude','longitude','speed_kmh','heading_deg','hdop','satellites','lap','fix','free_recording'])
        for p in points:w.writerow([p['elapsed_ms'],f"{p['latitude']:.7f}",f"{p['longitude']:.7f}",f"{p['speed_kmh']:.1f}",f"{p['heading_deg']:.1f}",f"{p['hdop']:.2f}",p['satellites'],p['lap'],p['fix'],p['free_recording']])
def export_json(session,points,path):
    d=dict(session); d['points']=[dict(p) for p in points]; Path(path).write_text(json.dumps(d,indent=2,ensure_ascii=False),encoding='utf-8')
def export_gpx(session,points,path):
    name=escape(session['track_name'] or 'GOATS RT')
    with open(path,'w',encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<gpx version="1.1" creator="GOATS RT Manager V5" xmlns="http://www.topografix.com/GPX/1/1" xmlns:goats="https://goats-rt.local/gpx/1">\n<trk><name>'+name+'</name><trkseg>\n')
        for p in points:f.write(f'<trkpt lat="{p["latitude"]:.7f}" lon="{p["longitude"]:.7f}"><extensions><goats:elapsed_ms>{p["elapsed_ms"]}</goats:elapsed_ms><goats:speed_kmh>{p["speed_kmh"]:.1f}</goats:speed_kmh><goats:lap>{p["lap"]}</goats:lap></extensions></trkpt>\n')
        f.write('</trkseg></trk></gpx>\n')
