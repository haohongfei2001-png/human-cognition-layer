"""Explicit host conversion and current-ACL reads of exact legacy originals.

No recompile, inference promotion, source-text instruction or automatic erasure.
The split is resumable before its atomic root publication. Opaque records remain
retained and explicitly unresolved, rather than guessed to belong to one source.
"""
import json

from hcl.kernel.scope import failure, identifier
from hcl.kernel.types import freeze
from hcl.memory import codec
from hcl.memory.governance import require_governed, owner_key, verify_inventory
from hcl.memory.lineage import source_token
from hcl.memory.migrations.capsules import split_legacy_package, validate_root
from hcl.memory.migrations.control import read_control
from hcl.memory.store import denied


def _namespace(store, db, session_id, principal):
    store._session(db, session_id, principal)
    require_governed(store)
    if store._schema != 4:
        raise failure('INVALID_REQUEST', 'LEGACY_NAMESPACE_REQUIRED', 'store',
                      'This maintenance operation requires a migrated legacy namespace.', 'governance')
    row = read_control(db)
    if (row['session_id'], row['tenant'], row['owner']) != (session_id, principal.tenant_id, principal.subject_id):
        raise denied()
    root = db.execute('SELECT object_hash FROM legacy_roots WHERE session_id=?', (session_id,)).fetchone()
    if root and root[0] != row['package_hash']:
        raise ValueError('legacy capsule root identity mismatch')
    return row


def _root(store, db, session_id):
    control = read_control(db)
    row = db.execute('SELECT * FROM legacy_roots WHERE session_id=?', (session_id,)).fetchone()
    if row is None or row['object_hash'] != control['package_hash']:
        raise ValueError('legacy capsule root identity mismatch')
    validate_root(store._get_object(row['object_hash']), control['namespace_id'], row['import_hash'])
    return dict(row)


def prepare(store, session_id, principal):
    """Copy originals into durable scoped owners, then atomically switch root."""
    with store._transaction(True, maintenance=True) as db:
        control = _namespace(store, db, session_id, principal)
        session = store._session(db, session_id, principal, owner=True)
        existing = db.execute('SELECT * FROM legacy_roots WHERE session_id=?', (session_id,)).fetchone()
        if existing:
            if existing['object_hash'] != control['package_hash']:
                raise ValueError('legacy capsule root identity mismatch')
            verify_inventory(db)
            _root(store, db, session_id)
            return dict(status='SCOPED_CAPSULES_PREPARED', import_hash=existing['import_hash'])
        # A previous erasure may already have removed related originals. Never
        # reconstruct or classify by reopening its retained mixed package.
        if db.execute('SELECT 1 FROM source_tombstones LIMIT 1').fetchone():
            raise failure('DENIED', 'ERASED_HISTORICAL_EXPORT', 'legacy_capsules',
                          'Scoped conversion must precede source erasure.', 'governance')
        package = store._get_object(control['package_hash'])
        if any(principal.subject_id not in readers for readers in package['host_readers'].values()):
            raise denied()
        if any(principal.subject_id not in json.loads(row[0]) for row in db.execute(
                'SELECT readers FROM sources WHERE session_id=?', (session_id,))):
            raise denied()
        prepared = split_legacy_package(package, session_id=session_id, import_hash=control['package_hash'])
        revision = session['revision'] + 1
        entries = list(prepared['entries'])
        # The mixed package is no longer a delivery root, but remains a tracked
        # closure member until explicit source erasure can safely remove it.
        entries.append(dict(key=('mixed',), kind='MIXED_ORIGINAL', source_id=None, versions=[], readers=[],
                            bindings=prepared['package_bindings'], value=package))
        sizes = [len(codec.dumps(entry['value'])) for entry in entries]
        if max(sizes, default=0) > 4 * 1024 * 1024 or sum(sizes) > 128 * 1024 * 1024:
            raise failure('BUDGET_EXHAUSTED', 'LEGACY_CAPSULE_STORAGE_BOUND', 'legacy_capsules',
                          'Scoped originals exceed the bounded migration object inventory.', 'governance')
        for entry in entries:
            capsule_id = owner_key(db, ('legacy_capsule_identity', session_id, entry['key']))
            digest = store._put_content(entry['value'], session_id=session_id, bindings=entry['bindings'])
            store._record(db, 'legacy_capsules', dict(session_id=session_id, capsule_id=capsule_id,
                kind=entry['kind'], source_id=entry['source_id'], versions=codec.canonical(entry['versions']),
                readers=codec.canonical(entry['readers']), reader_ceiling=codec.canonical(entry['readers']),
                bindings=codec.canonical(entry['bindings']), object_hash=digest), revision)
        root_hash = store._put_content(prepared['root'], session_id=session_id)
        store._record(db, 'legacy_roots', dict(session_id=session_id, import_hash=control['package_hash'],
                                             object_hash=root_hash), revision)
        db.execute('UPDATE namespace_control SET package_hash=? WHERE singleton=1', (root_hash,))
        session['revision'] = revision
        store._record(db, 'sessions', session, revision)
        verify_inventory(db)
        store._checkpoint('legacy_capsules_before_commit')
    store._checkpoint('legacy_capsules_committed')
    return dict(status='SCOPED_CAPSULES_PREPARED', import_hash=control['package_hash'])


def _select(store, db, session_id, principal, source_ids):
    _namespace(store, db, session_id, principal)
    if not db.execute('SELECT 1 FROM legacy_roots WHERE session_id=?', (session_id,)).fetchone():
        raise failure('INVALID_REQUEST', 'LEGACY_CAPSULE_PREPARATION_REQUIRED', 'legacy_capsules',
                      'Scoped legacy originals have not been prepared.', 'governance')
    salt = bytes.fromhex(store._revision_control['governance_salt'])
    selected, bindings = [], set()
    for source_id in source_ids:
        row = db.execute("SELECT * FROM legacy_capsules WHERE session_id=? AND source_id=? AND kind='SOURCE'",
                         (session_id, source_id)).fetchone()
        token = source_token(salt, session_id, source_id)
        if (row is None or principal.subject_id not in json.loads(row['readers'])
                or principal.subject_id not in json.loads(row['reader_ceiling'])
                or db.execute('SELECT 1 FROM source_tombstones WHERE session_id=? AND source_token=?',
                              (session_id, token)).fetchone()):
            raise denied()
        current = db.execute('SELECT readers FROM sources WHERE session_id=? AND source_id=?',
                             (session_id, source_id)).fetchone()
        if current and principal.subject_id not in json.loads(current[0]):
            raise denied()
        selected.append(dict(row))
        bindings.update(map(tuple, json.loads(row['bindings'])))
    for row in db.execute("SELECT * FROM legacy_capsules WHERE session_id=? AND kind='SOURCE_SPAN' ORDER BY capsule_id",
                          (session_id,)):
        if set(map(tuple, json.loads(row['bindings']))) <= bindings:
            selected.append(dict(row))
    return tuple(selected)


def source_view(store, session_id, principal, source_ids):
    if type(source_ids) not in (tuple, list) or not 0 < len(source_ids) <= 4096:
        raise ValueError('bounded explicit legacy source identities required')
    source_ids = tuple(identifier(value) for value in source_ids)
    if len(set(source_ids)) != len(source_ids):
        raise ValueError('duplicate legacy source identity')
    with store._transaction(maintenance=True) as db:
        selected = _select(store, db, session_id, principal, source_ids)
        root = _root(store, db, session_id)
        values = tuple(store._get_object(row['object_hash']) for row in selected)
        result = freeze(dict(scope='HISTORICAL_ORIGINAL_NOT_CURRENT_INFERENCE',
                             source_capsules=codec.encode([value for row, value in zip(selected, values) if row['kind'] == 'SOURCE']),
                             span_capsules=codec.encode([value for row, value in zip(selected, values) if row['kind'] == 'SOURCE_SPAN']),
                             unknown_provenance='RETAINED_NOT_INCLUDED', truth='NOT_ESTABLISHED'))
    with store._transaction(maintenance=True) as db:
        if _select(store, db, session_id, principal, source_ids) != selected:
            raise failure('DENIED', 'LEGACY_CAPSULE_DELIVERY_CHANGED', 'legacy_capsules',
                          'The scoped original references changed before delivery.', 'governance')
        if _root(store, db, session_id) != root:
            raise ValueError('legacy capsule root changed before delivery')
    return result


def set_readers(store, session_id, principal, source_id, readers):
    """Host ACL for historical/quarantined sources, bounded by import authority."""
    identifier(source_id)
    readers = sorted({identifier(value) for value in readers})
    with store._transaction(True, maintenance=True) as db:
        _namespace(store, db, session_id, principal)
        session = store._session(db, session_id, principal, owner=True)
        row = db.execute("SELECT * FROM legacy_capsules WHERE session_id=? AND source_id=? AND kind='SOURCE'",
                         (session_id, source_id)).fetchone()
        if row is None or not set(readers) <= set(json.loads(row['reader_ceiling'])):
            raise denied()
        row = dict(row)
        if json.loads(row['readers']) == readers:
            return
        row['readers'] = codec.canonical(readers)
        session['revision'] += 1
        store._record(db, 'legacy_capsules', row, session['revision'])
        store._record(db, 'sessions', session, session['revision'])
