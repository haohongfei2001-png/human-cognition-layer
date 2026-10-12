"""Exact synthetic old originals, never a regrading or deletion assertion."""
from copy import deepcopy
from hashlib import sha256
import unittest

from hcl.memory import codec
from hcl.memory.migrations.capsules import split_legacy_package, validate_root
from hcl.memory.migrations.compile import compile_snapshot, source_key
from hcl.memory.migrations.types import LegacyRecord, LegacySnapshot, LegacySource


class LegacyCapsuleTests(unittest.TestCase):
    @staticmethod
    def package(sources, records=(), origin='CALLER_SUPPLIED_TYPED_SNAPSHOT'):
        result = compile_snapshot(LegacySnapshot(tuple(sources), tuple(records), origin), 'capsules')
        result['host_readers'] = {row.source_id: ['owner'] for row in sources}
        result['owner'] = dict(tenant='t', subject='owner')
        return result

    @staticmethod
    def split(package):
        return split_legacy_package(package, session_id='s', import_hash=sha256(codec.dumps(package)).hexdigest())

    def test_all_source_lifecycles_and_quarantine_are_byte_exact(self):
        sources = (LegacySource('A', 1, 'OLD\r\n秘密𝄞', 'HISTORICAL'),
                   LegacySource('A', 2, 'current-one'), LegacySource('A', 3, 'current-two'),
                   LegacySource('B', 1, None, 'WITHDRAWN'),
                   LegacySource('C', 1, '\ud800', 'HISTORICAL'))
        package = self.package(sources)
        before = codec.dumps(package)
        split = self.split(package)
        self.assertEqual(codec.dumps(package), before)
        entries = {entry['source_id']: entry for entry in split['entries']}
        for original in package['original']['sources']:
            mapped = package['source_mapping'][original['old_key']]
            entry = entries[mapped['source_id']]
            copied = next(row for row in entry['value']['originals'] if row['old_key'] == original['old_key'])
            self.assertEqual(codec.dumps(copied), codec.dumps(original))
            descriptor = next(row for row in package['records'] if row['old_key'] == original['old_key'])
            copied_descriptor = next(row for row in entry['value']['descriptors'] if row['old_key'] == original['old_key'])
            self.assertEqual(codec.dumps(descriptor), codec.dumps(copied_descriptor))
            self.assertIn(('s', mapped['source_id'], mapped['version']), entry['bindings'])
        self.assertEqual(len(entries), 3)
        self.assertEqual(len(split['package_bindings']), 5)
        self.assertIn('AMBIGUOUS_CURRENT_VERSION', str(split))

    def test_exact_span_only_has_source_retention_and_old_disposition_unchanged(self):
        text = 'ORIGINAL'
        payload = dict(source_id='A', version=1, start=0, end=8, quote=text,
                       document_sha256=sha256(text.encode()).hexdigest())
        records = (LegacyRecord('span', 'SOURCE_SPAN', payload),
                   LegacyRecord('extra', 'SOURCE_SPAN', dict(payload, freeform='UNBOUND_PRIVATE')),
                   LegacyRecord('wrong', 'SOURCE_SPAN', dict(payload, quote='WRONG')))
        package = self.package((LegacySource('A', 1, text),), records)
        entries = {entry['key']: entry for entry in self.split(package)['entries']}
        self.assertEqual(entries['record', 'span']['kind'], 'SOURCE_SPAN')
        self.assertEqual(len(entries['record', 'span']['bindings']), 1)
        for name in ('extra', 'wrong'):
            self.assertEqual(entries['record', name]['kind'], 'UNKNOWN_PROVENANCE')
            self.assertFalse(entries['record', name]['bindings'])
            descriptor = next(row for row in package['records'] if row['old_key'] == name)
            self.assertEqual(entries['record', name]['value']['descriptor'], descriptor)

    def test_logical_support_edges_never_guess_exclusive_byte_origin(self):
        records = (LegacyRecord('report', 'SOURCE_REPORT', dict(supports=[], challenges=[], content='opaque')),
                   LegacyRecord('interpretation', 'SYSTEM_INTERPRETATION', dict(supports=[['report']], challenges=[])),
                   LegacyRecord('unknown', 'CUSTOM_OLD_KIND', dict(secret='unknown')))
        package = self.package((LegacySource('A', 1, 'A'), LegacySource('B', 1, 'B')), records)
        result = self.split(package)
        for entry in result['entries']:
            if entry['key'][0] == 'record':
                self.assertEqual(entry['kind'], 'UNKNOWN_PROVENANCE')
                self.assertFalse(entry['bindings'])
                original = next(row for row in package['original']['records'] if row['old_id'] == entry['key'][1])
                self.assertEqual(codec.dumps(entry['value']['original']), codec.dumps(original))
                self.assertEqual(entry['value']['descriptor']['truth'], 'NOT_ESTABLISHED')

    def test_custom_origin_is_retained_outside_content_free_root(self):
        package = self.package((LegacySource('A', 1, 'A'),), origin='PRIVATE_ORIGIN')
        result = self.split(package)
        self.assertNotIn('PRIVATE_ORIGIN', str(result['root']))
        entry = next(row for row in result['entries'] if row['key'] == ('origin',))
        self.assertEqual(entry['value']['original'], 'PRIVATE_ORIGIN')
        self.assertEqual(entry['kind'], 'UNKNOWN_PROVENANCE')

    def test_unknown_record_kind_and_id_can_overlap_source_labels_without_regrading(self):
        key = source_key('A', 1)
        package = self.package((LegacySource('A', 1, 'A'),),
                               (LegacyRecord(key, 'SOURCE_DOCUMENT', dict(extra='opaque')),))
        result = self.split(package)
        self.assertEqual(len(result['entries']), 2)
        record = next(row for row in result['entries'] if row['key'][0] == 'record')
        self.assertEqual(record['kind'], 'UNKNOWN_PROVENANCE')
        self.assertEqual(record['value']['descriptor']['reasons'], ['UNSUPPORTED_LEGACY_KIND'])

    def test_identity_and_mapping_membership_are_required(self):
        package = self.package((LegacySource('A', 1, 'A'),))
        with self.assertRaises(ValueError):
            split_legacy_package(package, session_id='s', import_hash='0' * 64)
        for field in ('records', 'source_mapping', 'host_readers'):
            other = deepcopy(package)
            other[field] = [] if field == 'records' else {}
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.split(other)
        other = deepcopy(package)
        other['source_mapping'][source_key('A', 1)]['version'] = 2
        with self.assertRaises(ValueError):
            self.split(other)

    def test_source_record_and_descriptor_global_ordinals_survive_split(self):
        package = self.package((LegacySource('A', 1, 'old', 'HISTORICAL'),
                                LegacySource('B', 1, 'other'), LegacySource('A', 2, 'current')),
                               (LegacyRecord('z', 'CUSTOM_KIND', {}), LegacyRecord('a', 'CUSTOM_KIND', {})))
        result = self.split(package)
        sources, records, descriptors = {}, {}, {}
        for entry in result['entries']:
            value = entry['value']
            if value['kind'] == 'SOURCE':
                sources.update(zip(value['original_ordinals'], value['originals']))
                descriptors.update(zip(value['descriptor_ordinals'], value['descriptors']))
            elif value['kind'] == 'RECORD':
                records[value['original_ordinal']] = value['original']
                descriptors[value['descriptor_ordinal']] = value['descriptor']
        for actual, expected in ((sources, package['original']['sources']),
                                 (records, package['original']['records']), (descriptors, package['records'])):
            self.assertEqual(codec.dumps([actual[key] for key in sorted(actual)]), codec.dumps(expected))
        root = result['root']
        validate_root(root, package['namespace'], sha256(codec.dumps(package)).hexdigest())
        for key in root:
            changed = dict(root, **{key: 'CORRUPT'})
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_root(changed, package['namespace'], sha256(codec.dumps(package)).hexdigest())


if __name__ == '__main__':
    unittest.main()
