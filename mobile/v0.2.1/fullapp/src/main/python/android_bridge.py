from __future__ import annotations

import base64
import json
import math
import os
import re
import shutil
import struct
import zlib
from pathlib import Path

from goats_formats import parse_any
from goats_store import SessionStore

_APP_DIR: Path | None = None
_TRACKS_DIR: Path | None = None
_STORE: SessionStore | None = None


def _j(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _safe(v, default=0.0):
    try:
        x = float(v)
        return x if math.isfinite(x) else default
    except Exception:
        return default


def _fmt_ms(ms):
    try:
        ms = int(ms or 0)
    except Exception:
        ms = 0
    if ms <= 0:
        return "--:--.---"
    return f"{ms//60000:02d}:{(ms//1000)%60:02d}.{ms%1000:03d}"


def _fmt_dur(ms):
    try:
        sec = int(ms or 0) // 1000
    except Exception:
        sec = 0
    return f"{sec//3600:02d}:{(sec//60)%60:02d}:{sec%60:02d}"


def _need_init():
    if _STORE is None or _APP_DIR is None:
        raise RuntimeError("Motore GOATS Android non inizializzato")


def init_app(base_dir: str):
    global _APP_DIR, _TRACKS_DIR, _STORE
    root = Path(base_dir) / "goats_rt_manager"
    root.mkdir(parents=True, exist_ok=True)
    _APP_DIR = root
    _TRACKS_DIR = root / "tracks"
    _TRACKS_DIR.mkdir(parents=True, exist_ok=True)
    _STORE = SessionStore(root / "goats_rt_sessions.sqlite3")

    # Inserisce il circuito di esempio solo in un'installazione nuova.
    if not any(_TRACKS_DIR.glob("*.json")):
        try:
            sample = Path(__file__).resolve().parent / "default_tracks" / "esempio.json"
            if sample.exists():
                shutil.copyfile(sample, _TRACKS_DIR / "esempio.json")
        except Exception:
            pass
    return _j({"ok": True, "data_dir": str(root)})


def health_json():
    _need_init()
    return _j({"ok": True, "version": "0.2.1", "engine": "GOATS V5.4.13.8 track editor + Wi-Fi + Cloud Sync"})


def dashboard_json():
    _need_init()
    rows = [dict(r) for r in _STORE.sessions()]
    sessions = len(rows)
    points = sum(int(r.get("point_count") or 0) for r in rows)
    duration = sum(int(r.get("duration_ms") or 0) for r in rows)
    best_values = [int(r.get("best_lap_ms") or 0) for r in rows if int(r.get("best_lap_ms") or 0) > 0]
    best = min(best_values) if best_values else 0
    return _j({
        "sessions": sessions,
        "points": points,
        "hours": round(duration / 3600000.0, 1),
        "best_ms": best,
        "best": _fmt_ms(best),
    })


def sessions_json(search: str = ""):
    _need_init()
    out = []
    for r in _STORE.sessions(search or ""):
        d = dict(r)
        out.append({
            "id": int(d["id"]),
            "date": d.get("date") or "",
            "time": d.get("time") or "",
            "track": d.get("track_name") or "Circuito",
            "type": d.get("session_type") or "",
            "laps": int(d.get("lap_count") or 0),
            "points": int(d.get("point_count") or 0),
            "best_ms": int(d.get("best_lap_ms") or 0),
            "best": _fmt_ms(d.get("best_lap_ms")),
            "duration": _fmt_dur(d.get("duration_ms")),
            "vmax": round(_safe(d.get("max_speed_kmh")), 1),
            "vavg": round(_safe(d.get("avg_speed_kmh")), 1),
            "notes": d.get("notes") or "",
            "format": d.get("source_format") or "",
        })
    return _j(out)


def import_file(path: str):
    _need_init()
    p = Path(path)
    imported = []
    sessions = parse_any(p)
    for s in sessions:
        sid = _STORE.import_session(s)
        imported.append({"id": sid, "track": s.track_name, "format": s.source_format})
    return _j({"ok": True, "count": len(imported), "sessions": imported})


def delete_session(session_id: int):
    _need_init()
    _STORE.delete(int(session_id))
    return _j({"ok": True})


def set_session_notes(session_id: int, notes: str):
    _need_init()
    _STORE.update_notes(int(session_id), notes or "")
    return _j({"ok": True})


def _downsample(rows, limit=60000, per_lap_limit=2500):
    """Preserva la forma della traiettoria: niente decimazione aggressiva globale.

    A 25 Hz un giro kart tipico resta quasi sempre sotto 2500 campioni, quindi
    viene inviato integralmente ad Android. Solo sessioni molto lunghe vengono
    ridotte, separatamente per giro, così non si creano corde/rettilinei artificiali.
    """
    rows = list(rows)
    if not rows:
        return rows

    groups = {}
    order = []
    for r in rows:
        lap = int(r.get("lap") or 0)
        if lap not in groups:
            groups[lap] = []
            order.append(lap)
        groups[lap].append(r)

    reduced = []
    for lap in order:
        grp = groups[lap]
        if len(grp) <= per_lap_limit:
            reduced.extend(grp)
            continue
        step = max(1, math.ceil(len(grp) / per_lap_limit))
        part = grp[::step]
        if part and part[-1]["seq"] != grp[-1]["seq"]:
            part.append(grp[-1])
        reduced.extend(part)

    if len(reduced) <= limit:
        return sorted(reduced, key=lambda r: int(r.get("seq") or 0))

    # Secondo limite di sicurezza per endurance molto lunghe, sempre per giro.
    factor = max(1, math.ceil(len(reduced) / limit))
    final = []
    by_lap = {}
    order2 = []
    for r in reduced:
        lap = int(r.get("lap") or 0)
        if lap not in by_lap:
            by_lap[lap] = []
            order2.append(lap)
        by_lap[lap].append(r)
    for lap in order2:
        grp = by_lap[lap]
        part = grp[::factor]
        if part and part[-1]["seq"] != grp[-1]["seq"]:
            part.append(grp[-1])
        final.extend(part)
    return sorted(final, key=lambda r: int(r.get("seq") or 0))


def analysis_json(session_id: int, lap: int = 0):
    _need_init()
    sid = int(session_id)
    srow = _STORE.session(sid)
    if srow is None:
        return _j({"ok": False, "error": "Sessione non trovata"})
    s = dict(srow)
    laps = [dict(r) for r in _STORE.laps(sid)]
    chosen_lap = int(lap or 0)
    points = [dict(r) for r in _STORE.points(sid, chosen_lap if chosen_lap > 0 else None)]
    points = _downsample(points)

    pdata = []
    for p in points:
        pdata.append({
            "t": int(p.get("elapsed_ms") or 0),
            "lat": _safe(p.get("latitude")),
            "lon": _safe(p.get("longitude")),
            "v": round(_safe(p.get("speed_kmh")), 2),
            "lap": int(p.get("lap") or 0),
        })

    ldata = []
    for l in laps:
        ldata.append({
            "lap": int(l.get("lap") or 0),
            "time_ms": int(l.get("lap_time_ms") or 0),
            "time": _fmt_ms(l.get("lap_time_ms")),
            "vmax": round(_safe(l.get("max_speed_kmh")), 1),
            "vavg": round(_safe(l.get("avg_speed_kmh")), 1),
            "points": int(l.get("point_count") or 0),
        })

    return _j({
        "ok": True,
        "session": {
            "id": sid,
            "track": s.get("track_name") or "Circuito",
            "date": s.get("date") or "",
            "time": s.get("time") or "",
            "notes": s.get("notes") or "",
            "best": _fmt_ms(s.get("best_lap_ms")),
            "best_ms": int(s.get("best_lap_ms") or 0),
            "vmax": round(_safe(s.get("max_speed_kmh")), 1),
            "vavg": round(_safe(s.get("avg_speed_kmh")), 1),
            "duration": _fmt_dur(s.get("duration_ms")),
            "laps": int(s.get("lap_count") or 0),
            "sample_hz": round(_safe(s.get("sample_rate_hz")), 1),
        },
        "selected_lap": chosen_lap,
        "laps": ldata,
        "points": pdata,
    })


def compare_json(ids_json: str):
    _need_init()
    ids = [int(x) for x in json.loads(ids_json or "[]")]
    out = []
    for sid in ids[:8]:
        s = _STORE.session(sid)
        if s is None:
            continue
        d = dict(s)
        out.append({
            "id": sid,
            "track": d.get("track_name") or "Circuito",
            "date": d.get("date") or "",
            "best": _fmt_ms(d.get("best_lap_ms")),
            "best_ms": int(d.get("best_lap_ms") or 0),
            "vmax": round(_safe(d.get("max_speed_kmh")), 1),
            "vavg": round(_safe(d.get("avg_speed_kmh")), 1),
            "laps": int(d.get("lap_count") or 0),
        })
    return _j(out)


# ---------------- Circuiti / GTC3 ----------------

def _slugify(value: str):
    chars = []
    for ch in str(value or "").lower().strip():
        if ch.isalnum():
            chars.append(ch)
        elif ch in " -_":
            chars.append("_")
    result = "".join(chars)
    while "__" in result:
        result = result.replace("__", "_")
    return result.strip("_") or "nuovo_circuito"


def _track_files():
    _need_init()
    return sorted(_TRACKS_DIR.glob("*.json"))


def tracks_json():
    out = []
    for p in _track_files():
        try:
            t = json.loads(p.read_text(encoding="utf-8"))
            splits = len(t.get("sectors", []) or [])
            out.append({
                "id": t.get("id") or p.stem,
                "name": t.get("name") or p.stem,
                "country": t.get("country") or "",
                "direction": t.get("direction") or "unspecified",
                "trigger_radius_m": _safe(t.get("trigger_radius_m"), 20.0),
                "split_lines": splits,
                "real_sectors": splits + 1,
                "file": p.name,
            })
        except Exception:
            continue
    return _j(out)


def import_track_file(path: str):
    _need_init()
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    tracks = obj.get("tracks", [obj]) if isinstance(obj, dict) else obj
    saved = []
    for t in tracks:
        if not isinstance(t, dict) or "start_line" not in t:
            continue
        tid = _slugify(t.get("id") or t.get("name") or "circuito")
        t["id"] = tid
        dest = _TRACKS_DIR / f"{tid}.json"
        dest.write_text(json.dumps(t, indent=2, ensure_ascii=False), encoding="utf-8")
        saved.append(tid)
    return _j({"ok": True, "count": len(saved), "ids": saved})


def track_json(track_id: str):
    _need_init()
    tid = _slugify(track_id)
    p = _TRACKS_DIR / f"{tid}.json"
    if not p.exists():
        return _j({"ok": False, "error": "Circuito non trovato"})
    try:
        t = json.loads(p.read_text(encoding="utf-8"))
        t["ok"] = True
        return _j(t)
    except Exception as exc:
        return _j({"ok": False, "error": str(exc)})


def save_track_json(payload_json: str):
    _need_init()
    t = json.loads(payload_json or "{}")
    name = str(t.get("name") or "").strip()
    if not name:
        raise ValueError("Inserire il nome del circuito")
    start = t.get("start_line") or {}
    required = ("lat1", "lon1", "lat2", "lon2")
    if any(k not in start for k in required):
        raise ValueError("Disegnare la linea del traguardo")
    coords = [float(start[k]) for k in required]
    if not (-90 <= coords[0] <= 90 and -180 <= coords[1] <= 180 and -90 <= coords[2] <= 90 and -180 <= coords[3] <= 180):
        raise ValueError("Coordinate traguardo non valide")
    sectors = list(t.get("sectors") or [])
    if len(sectors) > 12:
        raise ValueError("Sono supportate al massimo 12 linee settore")
    clean_sectors = []
    for i, sec in enumerate(sectors, start=1):
        if not isinstance(sec, dict):
            continue
        vals = [float(sec[k]) for k in required]
        clean_sectors.append({
            "id": f"sector_{i}",
            "name": str(sec.get("name") or f"Settore {i}").strip() or f"Settore {i}",
            "lat1": vals[0], "lon1": vals[1], "lat2": vals[2], "lon2": vals[3],
        })
    tid = _slugify(t.get("id") or name)
    clean = {
        "schema_version": 3,
        "id": tid,
        "name": name,
        "country": str(t.get("country") or "IT").strip().upper() or "IT",
        "direction": str(t.get("direction") or "unspecified"),
        "start_line": {"lat1": coords[0], "lon1": coords[1], "lat2": coords[2], "lon2": coords[3]},
        "trigger_radius_m": float(t.get("trigger_radius_m") or 20.0),
        "sectors": clean_sectors,
    }
    dest = _TRACKS_DIR / f"{tid}.json"
    dest.write_text(json.dumps(clean, indent=2, ensure_ascii=False), encoding="utf-8")
    return _j({"ok": True, "id": tid, "file": dest.name, "real_sectors": len(clean_sectors)+1})


def delete_track(track_id: str):
    _need_init()
    tid = _slugify(track_id)
    p = _TRACKS_DIR / f"{tid}.json"
    if p.exists():
        p.unlink()
    return _j({"ok": True})


def _load_tracks_by_ids(ids):
    wanted = set(str(x) for x in ids)
    out = []
    for p in _track_files():
        try:
            t = json.loads(p.read_text(encoding="utf-8"))
            if (t.get("id") or p.stem) in wanted:
                out.append(t)
        except Exception:
            pass
    return out


def _encode_text(value, max_bytes=63):
    encoded = str(value).encode("utf-8")[:max_bytes]
    return struct.pack("<B", len(encoded)) + encoded


def _build_catalog(tracks):
    tracks = list(tracks)
    if not tracks:
        raise ValueError("Non ci sono circuiti da inviare")
    if len(tracks) > 50:
        raise ValueError("Il catalogo supporta al massimo 50 circuiti")
    payload = bytearray(b"GTC3")
    payload += struct.pack("<HH", 1, len(tracks))
    dirs = {"unspecified": 0, "clockwise": 1, "counterclockwise": 2}
    for t in tracks:
        start = t["start_line"]
        sectors = t.get("sectors", []) or []
        if len(sectors) > 12:
            raise ValueError(f"{t.get('name','Circuito')}: massimo 12 linee settore")
        payload += _encode_text(t.get("name", "Circuito"))
        payload += struct.pack(
            "<ddddfBB",
            float(start["lat1"]), float(start["lon1"]),
            float(start["lat2"]), float(start["lon2"]),
            float(t.get("trigger_radius_m", 20.0)),
            dirs.get(t.get("direction", "unspecified"), 0), len(sectors),
        )
        for s in sectors:
            payload += _encode_text(s.get("name", "Settore"))
            payload += struct.pack("<dddd", float(s["lat1"]), float(s["lon1"]), float(s["lat2"]), float(s["lon2"]))
    return bytes(payload)


def _decode_text(payload, offset):
    if offset >= len(payload):
        raise ValueError("Catalogo circuiti incompleto")
    n = payload[offset]
    offset += 1
    if offset + n > len(payload):
        raise ValueError("Testo circuito troncato")
    return payload[offset:offset+n].decode("utf-8", errors="replace"), offset + n


def _parse_catalog(payload: bytes):
    if len(payload) < 8 or payload[:4] != b"GTC3":
        raise ValueError("Formato catalogo circuiti non valido")
    version, count = struct.unpack_from("<HH", payload, 4)
    if version != 1 or count > 50:
        raise ValueError(f"Catalogo non supportato v{version}, {count} circuiti")
    names = {0: "unspecified", 1: "clockwise", 2: "counterclockwise"}
    off = 8
    out = []
    for _ in range(count):
        name, off = _decode_text(payload, off)
        size = struct.calcsize("<ddddfBB")
        lat1, lon1, lat2, lon2, radius, dcode, scount = struct.unpack_from("<ddddfBB", payload, off)
        off += size
        sectors = []
        for __ in range(scount):
            sname, off = _decode_text(payload, off)
            slat1, slon1, slat2, slon2 = struct.unpack_from("<dddd", payload, off)
            off += struct.calcsize("<dddd")
            sectors.append({"name": sname, "lat1": slat1, "lon1": slon1, "lat2": slat2, "lon2": slon2})
        out.append({
            "schema_version": 3,
            "id": _slugify(name),
            "name": name,
            "country": "",
            "direction": names.get(dcode, "unspecified"),
            "start_line": {"lat1": lat1, "lon1": lon1, "lat2": lat2, "lon2": lon2},
            "trigger_radius_m": float(radius),
            "sectors": sectors,
        })
    if off != len(payload):
        raise ValueError(f"Catalogo con {len(payload)-off} byte extra")
    return out


def _merge_key(t):
    return _slugify(t.get("name") or t.get("id") or "")


def prepare_merged_catalog(existing_b64: str, selected_ids_json: str):
    selected_ids = json.loads(selected_ids_json or "[]")
    selected = _load_tracks_by_ids(selected_ids)
    existing = []
    if existing_b64:
        existing = _parse_catalog(base64.b64decode(existing_b64))
    merged = list(existing)
    pos = {_merge_key(t): i for i, t in enumerate(merged) if _merge_key(t)}
    added = updated = 0
    for t in selected:
        key = _merge_key(t)
        if key in pos:
            merged[pos[key]] = t
            updated += 1
        else:
            pos[key] = len(merged)
            merged.append(t)
            added += 1
    payload = _build_catalog(merged)
    return _j({
        "ok": True,
        "payload_b64": base64.b64encode(payload).decode("ascii"),
        "crc32": f"{zlib.crc32(payload)&0xffffffff:08X}",
        "bytes": len(payload),
        "selected": len(selected),
        "existing": len(existing),
        "added": added,
        "updated": updated,
        "preserved": max(0, len(existing)-updated),
        "total": len(merged),
    })


def save_catalog_from_laptimer(payload_b64: str):
    _need_init()
    tracks = _parse_catalog(base64.b64decode(payload_b64))
    saved = 0
    for t in tracks:
        tid = _slugify(t.get("id") or t.get("name"))
        t["id"] = tid
        (_TRACKS_DIR / f"{tid}.json").write_text(json.dumps(t, indent=2, ensure_ascii=False), encoding="utf-8")
        saved += 1
    return _j({"ok": True, "count": saved})
