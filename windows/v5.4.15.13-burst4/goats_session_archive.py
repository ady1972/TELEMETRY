"""Managed originals for Windows imports; user source files are never removed."""
from pathlib import Path
from goats_cloud_sync import digest, _publish, _slug, delete_session_files
from goats_formats import parse_any


def archive_source(source, archive):
    source, archive = Path(source), Path(archive)
    h = digest(source)
    name = _slug(source.stem.split('--')[0])[:64]+'--'+h+source.suffix.lower()
    target, created = _publish(source, archive/name)
    if digest(target) != h:
        if created: target.unlink()
        raise RuntimeError('Sorgente modificata durante la copia: '+source.name)
    return target, h


def adopt_existing(store, archive):
    """Relink available legacy originals without replacing session IDs/notes."""
    report = dict(copied=0, missing=0, errors=[])
    groups = {}
    for row in store.sessions():
        if row['source_path']: groups.setdefault(row['source_path'], []).append(row)
        else: report['missing'] += 1
    for source, rows in groups.items():
        try:
            if not Path(source).is_file():
                report['missing'] += len(rows)
                continue
            if all(row['source_sha256'] for row in rows) and Path(source).resolve().parent == Path(archive).resolve():
                continue
            target, h = archive_source(source, archive)
            status = store.conn.execute('SELECT complete FROM session_file_imports WHERE sha256=?', (h,)).fetchone()
            if status is not None and not status['complete']: continue
            with store.conn:
                for row in rows:
                    store.conn.execute('UPDATE sessions SET source_path=?,source_sha256=? WHERE id=?',
                                       (str(target), h, row['id']))
                store.conn.execute('INSERT OR REPLACE INTO session_file_imports VALUES(?,1)', (h,))
            report['copied'] += int(str(target) != source)
        except Exception as exc:
            report['errors'].append(Path(source).name+': '+str(exc))
    return report


def import_file(store, source, archive):
    target, h = archive_source(source, archive)
    complete = store.conn.execute('SELECT complete FROM session_file_imports WHERE sha256=?', (h,)).fetchone()
    exists = store.conn.execute('SELECT 1 FROM sessions WHERE source_sha256=? LIMIT 1', (h,)).fetchone()
    if complete is not None and complete['complete'] and exists: return 0
    sessions = list(parse_any(str(target)))
    if not sessions: raise ValueError('Nessuna sessione riconosciuta: '+target.name)
    with store.conn:
        store.conn.execute('INSERT OR REPLACE INTO session_file_imports VALUES(?,0)', (h,))
    ids = [store.import_session(session) for session in sessions]
    with store.conn:
        store.conn.executemany('UPDATE sessions SET source_sha256=? WHERE id=?', [(h, sid) for sid in ids])
        store.conn.execute('UPDATE session_file_imports SET complete=1 WHERE sha256=?', (h,))
    return len(ids)


def deletion_group(store, sid):
    row = store.session(sid)
    if row is None: return [], ''
    h = row['source_sha256']
    if h:
        return [int(r['id']) for r in store.sessions() if r['source_sha256'] == h], h
    return [int(sid)], ''


def apply_deletions(store, hashes, source_paths=()):
    hashes, source_paths = set(hashes), set(source_paths)
    ids = [int(r['id']) for r in store.sessions()
           if r['source_sha256'] in hashes or r['source_path'] in source_paths]
    with store.conn:
        store.conn.executemany('DELETE FROM sessions WHERE id=?', [(sid,) for sid in ids])
    return len(ids)


def delete_session(store, sid, archive, cloud, cache):
    ids, h = deletion_group(store, sid)
    errors = delete_session_files(cloud, archive, cache, h) if h else []
    with store.conn:
        store.conn.executemany('DELETE FROM sessions WHERE id=?', [(value,) for value in ids])
    return dict(deleted=len(ids), errors=errors, missing_source=not bool(h))
