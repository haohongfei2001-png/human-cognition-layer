"""Check a proposed I02 source against one exact repository text snapshot.

This is a negative screen, not a confirmation qualification. It never opens
LongMemEval paths and cannot establish model-training or historical disjointness.
"""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


WINDOW = 12
MAX_TEXT_BYTES = 1_000_000


def _git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def _windows(value):
    words = re.findall(r'\w+', value.casefold(), flags=re.UNICODE)
    return {hashlib.sha256('\x1f'.join(words[i:i + WINDOW]).encode()).hexdigest()
            for i in range(len(words) - WINDOW + 1)}


def audit_snapshot(repo, revision, source):
    """Return exposure evidence without copying source text into the receipt."""
    repo = Path(repo)
    commit = _git(repo, 'rev-parse', '--verify', f'{revision}^{{commit}}').decode().strip()
    if not isinstance(source, str) or not source.strip():
        raise ValueError('nonempty candidate source required')
    candidate = _windows(source)
    if not candidate:
        raise ValueError('candidate has fewer than 12 words')
    source_bytes = source.encode()
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    entries = _git(repo, 'ls-tree', '-r', '-z', commit).split(b'\0')
    matches = []
    skipped_nontext = []
    skipped_large = []
    skipped_sealed = []
    scanned = 0
    for entry in entries:
        if not entry:
            continue
        header, raw_path = entry.split(b'\t', 1)
        mode, kind, oid = header.split(b' ')
        path = raw_path.decode('utf-8', errors='surrogateescape')
        if 'longmemeval' in path.casefold():
            skipped_sealed.append(path)
            continue
        if kind != b'blob' or mode == b'120000':
            skipped_nontext.append(path)
            continue
        size = int(_git(repo, 'cat-file', '-s', oid.decode()))
        if size > MAX_TEXT_BYTES:
            skipped_large.append(path)
            continue
        content = _git(repo, 'cat-file', 'blob', oid.decode())
        try:
            body = content.decode('utf-8')
        except UnicodeDecodeError:
            skipped_nontext.append(path)
            continue
        scanned += 1
        overlap = candidate & _windows(body)
        if hashlib.sha256(content).hexdigest() == source_hash or overlap:
            matches.append({'path': path, 'shared_12_word_windows': len(overlap),
                            'exact_file_match': content == source_bytes})
    return {
        'schema': 'hcl-i02-current-snapshot-exposure-screen-v1',
        'repository_commit': commit,
        'candidate_source_sha256': source_hash,
        'status': 'TEXT_SNAPSHOT_NO_MATCH' if not matches and not skipped_large else 'REVIEW_REQUIRED',
        'utf8_files_scanned': scanned,
        'matches': matches,
        'skipped_nontext_paths': skipped_nontext,
        'skipped_large_paths': skipped_large,
        'sealed_paths_not_opened': len(skipped_sealed),
        'scope': 'EXACT_COMMIT_UTF8_TEXT_ONLY_NOT_GIT_HISTORY_OR_MODEL_TRAINING',
        'confirmation_qualified': False,
        'longmemeval': 'SEALED_NOT_ACCESSED',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--source-file', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    target = Path(args.output)
    if target.exists():
        raise ValueError('refusing to overwrite existing exposure receipt')
    receipt = audit_snapshot(args.repo, args.revision,
                             Path(args.source_file).read_text())
    target.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(receipt['status'])


if __name__ == '__main__':
    main()
