"""Pinned publisher edition match fails closed without seeing case content."""

import unittest
from unittest.mock import patch

from scripts.i02_fairytale_blind_match import blind_match


def fixture(story='A moon child left. ', book='Before A moon child left. After'):
    raw = ('section,text\n1,"' + story + '"\n').encode()
    return raw, book.encode()


class BlindEditionMatchTests(unittest.TestCase):
    def test_exact_normalized_containment_has_no_text_in_receipt(self):
        story, book = fixture()
        import hashlib
        with patch('scripts.i02_fairytale_blind_match.STORY_SHA256',
                   hashlib.sha256(story).hexdigest()), patch(
                   'scripts.i02_fairytale_blind_match.STORY_GIT_BLOB',
                   hashlib.sha1(f'blob {len(story)}\0'.encode() + story).hexdigest()), patch(
                   'scripts.i02_fairytale_blind_match.BOOK_SHA256',
                   hashlib.sha256(book).hexdigest()), patch(
                   'scripts.i02_fairytale_blind_match.STORY_SECTIONS', 1), patch(
                   'scripts.i02_fairytale_blind_match.STORY_WORDS', 4), patch(
                   'scripts.i02_fairytale_blind_match.BOOK_WORDS', 6), patch(
                   'scripts.i02_fairytale_blind_match.validate_metadata_only'):
            result = blind_match(story, book)
        self.assertTrue(result['exact_normalized_contiguous_match'])
        self.assertFalse(result['story_text_returned'])
        self.assertFalse(result['confirmation_qualified'])
        self.assertNotIn('moon child', str(result))

    def test_wrong_pinned_source_fails_before_content_parsing(self):
        story, book = fixture()
        with self.assertRaisesRegex(ValueError, 'story bytes differ'):
            blind_match(story, book)


if __name__ == '__main__':
    unittest.main()
