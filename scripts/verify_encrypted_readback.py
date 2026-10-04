"""Offline, bounded artifact readback. Never returns or writes decrypted contents."""
import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import zipfile

from scripts.universal_encrypted_result import SCHEMA, decrypt_result

MAX_RECEIPT = 16 * 1024 * 1024
MAX_ENVELOPE = 24 * 1024 * 1024
MAX_ARCHIVE = MAX_ENVELOPE + 1024 * 1024
EXPECTATION_FIELDS = {
    'schema', 'repository', 'artifact_id', 'artifact_name', 'run_id', 'head_sha',
    'archive_sha256', 'member_name', 'package_sha256', 'recipient_sha256',
    'receipt_sha256',
}
ENVELOPE_FIELDS = {
    'schema', 'algorithm', 'recipient_sha256', 'package_sha256', 'nonce_b64',
    'wrapped_key_b64', 'ciphertext_b64',
}


class ReadbackError(ValueError):
    """Only fixed, non-sensitive codes cross the CLI error boundary."""


def require(condition, code):
    if not condition:
        raise ReadbackError(code)


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def strict_json(raw):
    def pairs(rows):
        result = {}
        for key, value in rows:
            require(key not in result, 'DUPLICATE_JSON_KEY')
            result[key] = value
        return result

    def reject_constant(_value):
        raise ReadbackError('NONFINITE_JSON_VALUE')

    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=reject_constant)
    except ReadbackError:
        raise
    except (ValueError, UnicodeError, RecursionError):
        raise ReadbackError('INVALID_JSON') from None


def read_bounded(path, maximum, *, private=False):
    """Read one regular file; do not follow a final symlink or open a FIFO."""
    flags = os.O_RDONLY | os.O_NONBLOCK | getattr(os, 'O_NOFOLLOW', 0)
    with os.fdopen(os.open(path, flags), 'rb') as handle:
        info = os.fstat(handle.fileno())
        require(stat.S_ISREG(info.st_mode), 'REGULAR_FILE_REQUIRED')
        if private:
            require(os.name == 'posix' and info.st_uid == os.geteuid() and
                    info.st_nlink == 1 and not info.st_mode & 0o077,
                    'PRIVATE_KEY_OWNER_ONLY_PERMISSIONS_REQUIRED')
        require(info.st_size <= maximum, 'INPUT_SIZE_LIMIT')
        raw = handle.read(maximum + 1)
        require(len(raw) <= maximum, 'INPUT_SIZE_LIMIT')
        return raw


def validate_expectations(expected):
    require(isinstance(expected, dict) and set(expected) == EXPECTATION_FIELDS,
            'EXACT_EXPECTATION_SCHEMA_REQUIRED')
    require(expected['schema'] == 'hcl-encrypted-readback-expectations-v1',
            'EXACT_EXPECTATION_SCHEMA_REQUIRED')
    for field in ('archive_sha256', 'package_sha256', 'recipient_sha256', 'receipt_sha256'):
        require(isinstance(expected[field], str) and
                re.fullmatch('[0-9a-f]{64}', expected[field]), 'EXACT_SHA256_REQUIRED')
    require(isinstance(expected['head_sha'], str) and
            re.fullmatch('[0-9a-f]{40}', expected['head_sha']), 'EXACT_HEAD_SHA_REQUIRED')
    for field in ('artifact_id', 'run_id'):
        require(type(expected[field]) is int and expected[field] > 0, 'EXACT_POSITIVE_ID_REQUIRED')
    require(isinstance(expected['repository'], str) and
            re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', expected['repository']),
            'EXACT_REPOSITORY_REQUIRED')
    for field in ('artifact_name', 'member_name'):
        require(isinstance(expected[field], str) and
                re.fullmatch(r'[A-Za-z0-9_-][A-Za-z0-9_.-]{0,199}', expected[field]),
                'FLAT_EXACT_ARTIFACT_NAME_REQUIRED')
    return expected


def inspect_archive(archive, metadata, expected):
    """Metadata must come from the authenticated GitHub API, not the ZIP itself.

    The digest links the supplied metadata to the exact ZIP. This offline function
    cannot authenticate the metadata's origin or a caller-authored expectations file.
    """
    validate_expectations(expected)
    require(isinstance(archive, bytes) and len(archive) <= MAX_ARCHIVE, 'INPUT_SIZE_LIMIT')
    require(isinstance(metadata, dict), 'ARTIFACT_METADATA_REQUIRED')
    require(sha256(archive) == expected['archive_sha256'], 'ARCHIVE_SHA256_MISMATCH')
    url = ('https://api.github.com/repos/' + expected['repository'] +
           '/actions/artifacts/' + str(expected['artifact_id']))
    for field in ('id', 'name'):
        require(type(metadata.get(field)) is type(expected['artifact_' + field]) and
                metadata[field] == expected['artifact_' + field], 'ARTIFACT_IDENTITY_MISMATCH')
    require(metadata.get('url') == url and metadata.get('archive_download_url') == url + '/zip' and
            metadata.get('digest') == 'sha256:' + expected['archive_sha256'],
            'ARTIFACT_METADATA_DIGEST_OR_REPOSITORY_MISMATCH')
    run = metadata.get('workflow_run')
    require(isinstance(run, dict) and type(run.get('id')) is int and
            run['id'] == expected['run_id'] and run.get('head_sha') == expected['head_sha'],
            'RUN_OR_HEAD_MISMATCH')
    try:
        with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
            members = bundle.infolist()
            require(len(members) == 1, 'ONE_ENVELOPE_MEMBER_REQUIRED')
            member = members[0]
            mode = member.external_attr >> 16
            require(member.filename == expected['member_name'] and
                    member.orig_filename == member.filename and not member.is_dir() and
                    stat.S_IFMT(mode) in (0, stat.S_IFREG), 'UNSAFE_OR_UNEXPECTED_ZIP_MEMBER')
            require(not member.flag_bits & 1 and
                    member.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED),
                    'UNSUPPORTED_ZIP_ENCODING')
            require(member.file_size <= MAX_ENVELOPE, 'ENVELOPE_SIZE_LIMIT')
            with bundle.open(member) as stream:
                raw = stream.read(MAX_ENVELOPE + 1)
            require(len(raw) <= MAX_ENVELOPE, 'ENVELOPE_SIZE_LIMIT')
    except ReadbackError:
        raise
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile, NotImplementedError):
        raise ReadbackError('INVALID_ARTIFACT_ZIP') from None
    envelope = strict_json(raw)
    require(isinstance(envelope, dict) and set(envelope) == ENVELOPE_FIELDS and
            envelope['schema'] == SCHEMA and envelope['algorithm'] == 'RSA-OAEP-SHA256+AES-256-GCM',
            'EXACT_ENVELOPE_SCHEMA_REQUIRED')
    require(envelope['package_sha256'] == expected['package_sha256'] and
            envelope['recipient_sha256'] == expected['recipient_sha256'],
            'PACKAGE_OR_RECIPIENT_MISMATCH')
    try:
        decoded = {name: base64.b64decode(envelope[name], validate=True)
                   for name in ('nonce_b64', 'wrapped_key_b64', 'ciphertext_b64')}
        require(len(decoded['nonce_b64']) == 12 and
                384 <= len(decoded['wrapped_key_b64']) <= 2048 and
                16 <= len(decoded['ciphertext_b64']) <= MAX_RECEIPT + 16,
                'ENVELOPE_CIPHERTEXT_BOUNDS')
    except (TypeError, ValueError):
        raise ReadbackError('INVALID_ENVELOPE_ENCODING_OR_BOUNDS') from None
    evidence = dict(schema='hcl-encrypted-readback-evidence-v1',
                    status='CIPHERTEXT_IDENTITY_VERIFIED_PRIVATE_READBACK_NOT_RUN',
                    **{k: expected[k] for k in EXPECTATION_FIELDS - {'schema', 'receipt_sha256'}},
                    expected_receipt_sha256=expected['receipt_sha256'],
                    envelope_sha256=sha256(raw),
                    run_head_binding='MATCHED_SUPPLIED_GITHUB_METADATA_NOT_AEAD_FIELDS',
                    metadata_origin_independently_authenticated=False,
                    private_readback_verified=False, durable_key_custody_verified=False,
                    provider_calls=0, authorized_calls=0)
    return envelope, evidence


def verify_readback(envelope, private, expected, evidence):
    """Called only with inspect_archive output. Plaintext stays within this scope."""
    try:
        plaintext = decrypt_result(envelope, private, expected['package_sha256'])
    except Exception:
        raise ReadbackError('PRIVATE_READBACK_AUTHENTICATION_FAILED') from None
    require(len(plaintext) <= MAX_RECEIPT, 'RECEIPT_SIZE_LIMIT')
    require(sha256(plaintext) == expected['receipt_sha256'], 'RECEIPT_SHA256_MISMATCH')
    receipt = strict_json(plaintext)
    require(isinstance(receipt, dict) and receipt.get('package_sha256') == expected['package_sha256'],
            'RECEIPT_PACKAGE_MISMATCH')
    return dict(evidence, status='EXACT_PRIVATE_RECEIPT_READBACK_VERIFIED',
                private_readback_verified=True, receipt_sha256=sha256(plaintext))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('inspect', 'verify'))
    parser.add_argument('--archive', required=True)
    parser.add_argument('--metadata', required=True, help='One GitHub artifact metadata object')
    parser.add_argument('--expected', required=True, help='Independently reviewed exact expectations')
    parser.add_argument('--private-key', help='Existing authorized owner-only PEM; never created or modified')
    args = parser.parse_args(argv)
    try:
        require(bool(args.private_key) == (args.mode == 'verify'), 'VERIFY_ONLY_PRIVATE_KEY_REQUIRED')
        expected = strict_json(read_bounded(args.expected, 16 * 1024))
        metadata = strict_json(read_bounded(args.metadata, 64 * 1024))
        archive = read_bounded(args.archive, MAX_ARCHIVE)
        envelope, evidence = inspect_archive(archive, metadata, expected)
        if args.mode == 'verify':
            # Reject wrong public identity before touching the private key.
            private = read_bounded(args.private_key, 64 * 1024, private=True)
            evidence = verify_readback(envelope, private, expected, evidence)
        print(json.dumps(evidence, sort_keys=True))
        return 0
    except Exception as error:
        # Never emit paths, parser snippets, plaintext, private PEM or library errors.
        code = str(error) if isinstance(error, ReadbackError) else 'READBACK_INPUT_OR_IO_FAILURE'
        print(json.dumps(dict(status='READBACK_REFUSED', failure_code=code,
                              private_readback_verified=False, authorized_calls=0), sort_keys=True))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
