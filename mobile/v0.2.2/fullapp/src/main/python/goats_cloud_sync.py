"""File-only session/track exchange shared by Windows and Android.

Session files and track revisions are immutable in the shared folder. SQLite,
settings and credentials remain local. Concurrent track edits remain separate.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import tempfile

FORMAT = 'GOATS_TRACK_SYNC_V1'
SESSION_EXTENSIONS = {'.csv', '.grt', '.gsa', '.bin', '.json'}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(256 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def _slug(value):
    return re.sub(r'_+', '_', ''.join(c if c.isalnum() or c == '_' else '_' for c in str(value).lower())).strip('_')[:100] or 'circuito'


def _atomic_json(path, value):
    path = Path(path);path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():raise ValueError('Percorso simbolico non consentito: '+path.name)
    handle, temp = tempfile.mkstemp(prefix='.goats_', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(handle, 'wb') as stream:stream.write(_canonical(value))
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)


def _state(cache):
    path = Path(cache) / 'state.json'
    if not path.exists():return {'version':1, 'tracks':{}, 'imported_sessions':[]}
    value = json.loads(path.read_text(encoding='utf-8'))
    if value.get('version') != 1 or not isinstance(value.get('tracks'), dict):
        raise ValueError('Stato sincronizzazione non valido. Conservare una copia prima di ripristinarlo.')
    return value


def mark_sessions_imported(cache, hashes):
    value = _state(cache)
    value['imported_sessions'] = sorted(set(value['imported_sessions']) | set(hashes))
    _atomic_json(Path(cache) / 'state.json', value)


def _publish(source, destination):
    """Create a new file; never truncate an existing shared/local file."""
    source = Path(source);destination = Path(destination)
    expected = digest(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    original = destination;index = 2
    while destination.exists() or destination.is_symlink():
        if not destination.is_symlink() and destination.is_file() and digest(destination) == expected:
            return destination, False
        destination = original.with_name(original.stem+'_'+str(index)+original.suffix);index += 1
    created = False
    try:
        with destination.open('xb') as target, source.open('rb') as stream:
            created = True;shutil.copyfileobj(stream, target, 256 * 1024)
        if digest(destination) != expected:
            raise ValueError('File modificato durante la copia: '+source.name)
    except Exception:
        if created:destination.unlink(missing_ok=True)
        raise
    return destination, True


def _session(path):
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.suffix.lower() not in SESSION_EXTENSIONS:return False
    if path.suffix.lower() == '.json':
        try:
            value = json.loads(path.read_text(encoding='utf-8'))
            entries = value.get('sessions', [value]) if isinstance(value, dict) else value
            return isinstance(entries, list) and bool(entries) and all(isinstance(x, dict) and 'laps' in x for x in entries)
        except (ValueError, OSError):return False
    with path.open('rb') as stream:magic = stream.read(4)
    return path.suffix.lower() == '.csv' or magic in (b'GRT8', b'GSA2', b'GSA3')


def _track(value):
    if not isinstance(value, dict) or not str(value.get('name', '')).strip():raise ValueError('Circuito senza nome.')
    lines = [value.get('start_line')] + list(value.get('sectors') or [])
    if len(lines) > 13:raise ValueError('Massimo 12 linee settore.')
    for line in lines:
        if not isinstance(line, dict):raise ValueError('Linea circuito non valida.')
        for key, limit in (('lat1',90),('lon1',180),('lat2',90),('lon2',180)):
            number = float(line[key])
            if not math.isfinite(number) or abs(number) > limit:raise ValueError('Coordinate circuito non valide.')
    value = json.loads(_canonical(value))
    value['id'] = _slug(value.get('id') or value['name'])
    return value


def _revision(track, parents):
    value = {'format':FORMAT, 'track':_track(track), 'parents':sorted(set(parents))}
    value['revision'] = hashlib.sha256(_canonical(value)).hexdigest()
    return value


def _read_revision(path):
    value = json.loads(Path(path).read_text(encoding='utf-8'))
    if value.get('format') != FORMAT or not isinstance(value.get('parents'), list):raise ValueError('Revisione circuito non riconosciuta.')
    if any(not isinstance(p,str) or not re.fullmatch('[0-9a-f]{64}',p) for p in value['parents']):raise ValueError('Parent circuito non valido.')
    expected = _revision(value['track'], value['parents'])
    if value != expected:raise ValueError('Integrità revisione circuito non valida.')
    return value


def _track_hash(track):return hashlib.sha256(_canonical(track)).hexdigest()


def sync_folder(cloud, archive, tracks, cache, known_sessions=()):
    """Synchronize a filesystem folder or a local staging copy of a SAF tree.

    Caller imports returned session_files into its own SQLite database, then
    calls mark_sessions_imported only for successful imports. No deletions sync.
    """
    cloud, archive, tracks, cache = map(Path, (cloud, archive, tracks, cache))
    for folder in (cloud, archive, tracks, cache, cache/'events', cloud/'circuiti'):
        if folder.is_symlink():raise ValueError('Cartella simbolica non consentita: '+folder.name)
        folder.mkdir(parents=True, exist_ok=True)
    state = _state(cache)
    result = dict(session_files=[], downloaded=0, uploaded=0, tracks_imported=0,
                  conflicts=0, errors=[], tracks_published=0)
    imported = set(state['imported_sessions'])
    known_sources = state.setdefault('known_sources', {})
    local_sessions = {}
    # Existing database sources keep their paths and are already imported.
    for path in sorted(set(map(str, known_sessions))):
        p = Path(path)
        if _session(p):
            h = digest(p);local_sessions[h] = p
            if str(p) not in known_sources:imported.add(h)
            known_sources[str(p)] = h
    for path in sorted(archive.iterdir()):
        if not _session(path):continue
        h = digest(path)
        named_hash = re.search(r'--([0-9a-f]{64})', path.stem)
        if named_hash and named_hash[1] != h:
            result['errors'].append('File archivio incompleto: '+path.name);continue
        local_sessions.setdefault(h, path)
    shared_sessions = {}
    for path in sorted(cloud.iterdir()):
        if not _session(path):continue
        h = digest(path)
        # Content-addressed names also reject a cloud upload still in progress.
        named_hash = re.search(r'--([0-9a-f]{64})', path.stem)
        if named_hash and named_hash[1] != h:
            result['errors'].append('File sessione incompleto: '+path.name);continue
        shared_sessions.setdefault(h, path)
        if h not in local_sessions:
            stem = _slug(path.stem.split('--')[0])[:64]
            target, created = _publish(path, archive/(stem+'--'+h+path.suffix.lower()))
            local_sessions[h] = target;result['downloaded'] += int(created)
    for h, path in local_sessions.items():
        if h not in shared_sessions:
            stem = _slug(path.stem.split('--')[0])[:64]
            target, created = _publish(path, cloud/(stem+'--'+h+path.suffix.lower()))
            shared_sessions[h] = target;result['uploaded'] += int(created)
        if h not in imported:result['session_files'].append({'path':str(path), 'sha256':h})

    events = {}
    for folder in (cache/'events', cloud/'circuiti'):
        for path in sorted(folder.glob('*.json')):
            try:
                if path.is_symlink():raise ValueError('Revisione simbolica non consentita.')
                event = _read_revision(path);events[event['revision']] = event
                if folder == cloud/'circuiti':
                    _atomic_json(cache/'events'/(event['revision']+'.json'), event)
            except (ValueError, KeyError, TypeError, OSError) as exc:
                result['errors'].append(path.name+': '+str(exc))
    shared_ids = set()
    for path in (cloud/'circuiti').glob('*.json'):
        try:shared_ids.add(_read_revision(path)['revision'])
        except (ValueError, KeyError, TypeError, OSError):pass
    local_tracks = {}
    for path in sorted(tracks.glob('*.json')):
        try:
            if path.is_symlink():raise ValueError('Circuito simbolico non consentito.')
            track = _track(json.loads(path.read_text(encoding='utf-8')));tid = track['id']
            if tid in local_tracks:raise ValueError('ID circuito duplicato: '+tid)
            local_tracks[tid] = (path, track)
        except (ValueError, KeyError, TypeError, OSError) as exc:
            result['errors'].append(path.name+': '+str(exc))
    # Publish edits against the heads seen at the PREVIOUS sync. Unseen remote
    # edits therefore stay concurrent, even when clock times differ.
    for tid, (path, track) in list(local_tracks.items()):
        h = _track_hash(track);previous = state['tracks'].get(tid)
        if previous and previous['hash'] == h:continue
        matching = [eid for eid,e in events.items() if e['track']['id']==tid and _track_hash(e['track'])==h]
        if not previous and matching:
            state['tracks'][tid] = {'hash':h, 'heads':matching};continue
        event = _revision(track, previous.get('heads', []) if previous else [])
        events[event['revision']] = event
        _atomic_json(cache/'events'/(event['revision']+'.json'), event)
        state['tracks'][tid] = {'hash':h, 'heads':[event['revision']]}
        result['tracks_published'] += 1
    groups = {}
    for eid,event in events.items():groups.setdefault(event['track']['id'], {})[eid] = event
    for tid, versions in groups.items():
        parents = {parent for event in versions.values() for parent in event['parents']}
        heads = sorted(set(versions)-parents)
        if not heads:continue
        local = local_tracks.get(tid)
        current_hash = _track_hash(local[1]) if local else None
        chosen = next((eid for eid in heads if _track_hash(versions[eid]['track'])==current_hash), heads[0])
        track = versions[chosen]['track'];h = _track_hash(track)
        path = local[0] if local else tracks/(tid+'.json')
        if h != current_hash:
            _atomic_json(path, track);result['tracks_imported'] += 1
        state['tracks'][tid] = {'hash':h, 'heads':heads}
        if len(heads)>1:
            result['conflicts'] += 1
            for eid in heads:
                if eid==chosen:continue
                copy = dict(versions[eid]['track'])
                copy['id'] = tid[:70]+'_conflitto_'+eid[:16]
                copy['name'] = copy['name']+' (conflitto '+eid[:8]+')'
                conflict_path = tracks/(copy['id']+'.json')
                previous = state['tracks'].get(copy['id'])
                if not conflict_path.exists():
                    _atomic_json(conflict_path, copy);result['tracks_imported'] += 1
                elif _track_hash(_track(json.loads(conflict_path.read_text(encoding='utf-8')))) != _track_hash(copy):
                    # User-edited conflict copies are never overwritten.
                    continue
                state['tracks'][copy['id']] = {'hash':_track_hash(copy), 'heads':[], 'conflict':True}
    for eid,event in events.items():
        if eid not in shared_ids:
            _publish(cache/'events'/(eid+'.json'), cloud/'circuiti'/(eid+'.json'))
            result['uploaded'] += 1
    state['imported_sessions'] = sorted(imported)
    _atomic_json(cache/'state.json', state)
    return result
