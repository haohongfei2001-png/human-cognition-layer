import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts import i02_gilman_protected_candidate as holder


RDF = b'''<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:d="http://purl.org/dc/terms/" xmlns:pg="http://www.gutenberg.org/2009/pgterms/"><pg:ebook><d:title>The Yellow Wallpaper</d:title><d:rights>Public domain in the USA.</d:rights><d:creator><pg:agent><pg:name>Gilman, Charlotte Perkins</pg:name><pg:deathdate>1935</pg:deathdate></pg:agent></d:creator></pg:ebook></rdf:RDF>'''


class ProtectedNarrativeTests(unittest.TestCase):
    def fixture(self):
        # Authored parser fixture only, not an independent literary source.
        body = ' '.join('independentword' + str(i) for i in range(1500))
        body += ' ' + 'x' * (31497 - len(body) - 1)
        raw = ('Wrapper\n*** START OF THE PROJECT GUTENBERG EBOOK 1952 ***\n' +
               body + '\n*** END OF THE PROJECT GUTENBERG EBOOK 1952 ***\nWrapper').encode()
        return body, raw

    def test_full_unit_ordinary_task_preserved_and_wrong_edition_refused(self):
        body, raw = self.fixture()
        with patch.object(holder, 'RAW_SHA256', hashlib.sha256(raw).hexdigest()), \
             patch.object(holder, 'BODY_SHA256', hashlib.sha256(body.encode()).hexdigest()):
            self.assertEqual(holder.original_body(raw), body)
            self.assertEqual(holder.ordinary_input(body), {'question': holder.QUESTION, 'source_text': body})
            with self.assertRaises(ValueError): holder.original_body(raw + b'Added premise')
        with self.assertRaises(ValueError): holder.original_body(b'wrong publisher version')

    def test_metadata_is_not_inferred_from_length_or_rights_label(self):
        self.assertEqual(holder.publisher_metadata(RDF)['deathdates'], ['1935'])
        for before, after in [(b'1935', b'2025'), (b'Public domain in the USA.', b'Unknown'),
                              (b'The Yellow Wallpaper', b'Unrelated source')]:
            with self.assertRaises(ValueError): holder.publisher_metadata(RDF.replace(before, after))

    def test_protected_package_cannot_become_paid_or_confirmation_by_edit(self):
        self.assertFalse(holder.load_package()['confirmation_qualified'])
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'p.json'; mutated = json.loads(holder.PACKAGE.read_text())
            mutated['provider_input_allowed'] = True; p.write_text(json.dumps(mutated))
            with patch.object(holder, 'PACKAGE', p):
                with self.assertRaises(ValueError): holder.load_package()

    def test_history_and_snapshot_composition_only_yields_pending_review(self):
        body, raw = self.fixture()
        history = {'status': 'REACHABLE_HISTORY_NO_TEXT_MATCH', 'checkout_head': 'current', 'matches': []}
        snap = {'status': 'TEXT_SNAPSHOT_NO_MATCH', 'repository_commit': 'current', 'matches': []}
        with patch.object(holder, 'original_body', return_value=body), \
             patch.object(holder, 'audit_history', return_value=history) as hist, \
             patch.object(holder, 'audit_snapshot', return_value=snap) as snapshot:
            receipt = holder.screen('.', raw, RDF)
            self.assertEqual(receipt['status'], 'READY_FOR_SOURCE_FIRST_HOLDER_REVIEW')
            self.assertFalse(receipt['confirmation_qualified'])
            self.assertFalse(receipt['provider_input_allowed'])
            self.assertFalse(receipt['h_entry_executed'])
            self.assertFalse(receipt['source_text_displayed'])
            self.assertNotIn(body, json.dumps(receipt))
            self.assertEqual(receipt['provider_calls'], 0)
            hist.assert_called_once_with('.', body)
            snapshot.assert_called_once_with('.', 'HEAD', body)
            history['status'] = 'REVIEW_REQUIRED'
            self.assertEqual(holder.screen('.', raw, RDF)['status'], 'EXPOSURE_REVIEW_REQUIRED')
            history['status'] = 'REACHABLE_HISTORY_NO_TEXT_MATCH'; snap['status'] = 'REVIEW_REQUIRED'
            self.assertEqual(holder.screen('.', raw, RDF)['status'], 'EXPOSURE_REVIEW_REQUIRED')

    def test_local_revision_does_not_reuse_pinned_source_and_legacy_exposure_rules(self):
        body, raw = self.fixture()
        edited = raw.replace(b'independentword100', b'actor-intends-harm')
        with patch.object(holder, 'RAW_SHA256', hashlib.sha256(edited).hexdigest()), \
             patch.object(holder, 'BODY_SHA256', hashlib.sha256(body.encode()).hexdigest()):
            with self.assertRaises(ValueError): holder.original_body(edited)
        from scripts.i02_source_qualification_v9 import require_obp_disjoint
        with self.assertRaises(ValueError): require_obp_disjoint({'author_id': 'mark-dimmock'})


if __name__ == '__main__': unittest.main()
