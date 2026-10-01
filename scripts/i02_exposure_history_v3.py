"""Current v3 history screen: full object IDs and merge-aware sealed metadata.

Legacy v1/v2 helpers remain immutable for consumed package replay.

Object names and metadata identify sealed LongMemEval blobs before content
reads. A clean result never proves deleted-ref, provider-training or semantic
independence and cannot by itself qualify a confirmation source.
"""

import hashlib
import subprocess
from pathlib import Path

from scripts.i02_exposure_snapshot import MAX_TEXT_BYTES, _windows


def _git(repo, *args, input_bytes=None):
    return subprocess.run(['git', '-C', str(repo), *args], input=input_bytes,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout


def _sealed_object_ids(repo):
    """Collect old and new blob IDs from every sealed-path change without reading them."""
    raw = _git(repo, 'log', '--all', '--root', '--raw', '--full-history', '-m', '--no-abbrev', '--no-renames', '--format=')
    sealed = set()
    for line in raw.splitlines():
        if not line.startswith(b':') or b'\t' not in line:
            continue
        header, path = line.split(b'\t', 1)
        if b'longmemeval' not in path.lower():
            continue
        fields = header.split()
        if len(fields) < 4:
            raise ValueError('unparseable sealed Git metadata')
        sealed.update(oid.decode() for oid in fields[2:4] if oid.strip(b'0'))
    return sealed


def audit_history(repo, source):
    """Compare 12-word fingerprints without returning candidate or repo text."""
    repo = Path(repo)
    if not isinstance(source, str) or not source.strip():
        raise ValueError('nonempty candidate source required')
    candidate = _windows(source)
    if not candidate:
        raise ValueError('candidate has fewer than 12 words')
    head = _git(repo, 'rev-parse', '--verify', 'HEAD^{commit}').decode().strip()
    sealed = _sealed_object_ids(repo)
    raw = _git(repo, 'rev-list', '--objects', '--all')
    entries = [line.split(b' ', 1) for line in raw.splitlines()]
    oids = [row[0] for row in entries]
    checks = _git(repo, 'cat-file', '--batch-check=%(objectname) %(objecttype) %(objectsize)',
                  input_bytes=b'\n'.join(oids) + b'\n').splitlines()
    if len(checks) != len(entries):
        raise ValueError('incomplete Git object inventory')
    matches, skipped_large = [], []
    sealed_skips = scanned = skipped_nontext = 0
    source_bytes = source.encode()
    for entry, check in zip(entries, checks):
        oid = entry[0].decode()
        path = entry[1].decode('utf-8', errors='surrogateescape') if len(entry) > 1 else ''
        got_oid, kind, size = check.split()
        if got_oid.decode() != oid:
            raise ValueError('Git object inventory mismatch')
        if kind != b'blob':
            continue
        if oid in sealed or 'longmemeval' in path.casefold():
            sealed_skips += 1
            continue
        if int(size) > MAX_TEXT_BYTES:
            skipped_large.append(path or oid)
            continue
        body = _git(repo, 'cat-file', 'blob', oid)
        try:
            text = body.decode('utf-8')
        except UnicodeDecodeError:
            skipped_nontext += 1
            continue
        scanned += 1
        overlap = candidate & _windows(text)
        if body == source_bytes or overlap:
            matches.append(dict(object_sha=oid, first_reachable_path=path,
                                shared_12_word_windows=len(overlap),
                                exact_blob_match=body == source_bytes))
    return dict(schema='hcl-i02-reachable-git-history-exposure-v1',
        checkout_head=head, candidate_source_sha256=hashlib.sha256(source_bytes).hexdigest(),
        status='REVIEW_REQUIRED' if matches or skipped_large else 'REACHABLE_HISTORY_NO_TEXT_MATCH',
        matches=matches, unique_utf8_blobs_scanned=scanned,
        sealed_blob_ids_not_opened=sealed_skips, skipped_nontext_blobs=skipped_nontext,
        skipped_large_paths=skipped_large,
        scope='CURRENTLY_REACHABLE_GIT_OBJECTS_NOT_DELETED_REFS_OR_MODEL_TRAINING',
        confirmation_qualified=False, longmemeval='SEALED_NOT_ACCESSED')
