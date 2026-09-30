"""Reconstruct one pinned, development-exposed native concept question.

This is source preparation for I02 comparator calibration, never confirmation.
It does not turn the publisher's interpretation into philosophical truth.
"""

import hashlib
from html.parser import HTMLParser


PINNED_HTML_SHA256 = 'fd71952183ba87a7940fa9c46e8d14e0e5e16629d3f5122967cabee54bc688fb'
SOURCE_SECTIONS = ('the-lovelace-objection', 'turings-reply')
QUESTION_ORDINAL = 3


class _NativeCaseParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.section = None
        self.depth = 0
        self.in_question_list = False
        self.in_question = False
        self.in_blockquote = False
        self.parts = {key: [] for key in SOURCE_SECTIONS}
        self.questions = []
        self.blockquotes = 0
        self.license_marker = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'section' and attrs.get('id') in (*SOURCE_SECTIONS, 'discussion-questions'):
            self.section, self.depth = attrs['id'], 1
            return
        if self.section is None:
            return
        if tag == 'section':
            self.depth += 1
        if tag == 'blockquote' and self.section in SOURCE_SECTIONS:
            self.blockquotes += 1
            self.in_blockquote = True
        if self.section == 'discussion-questions':
            if tag == 'ol':
                self.in_question_list = True
            elif tag == 'li' and self.in_question_list:
                self.in_question = True
                self.questions.append([])
        if tag in ('p', 'h2', 'h3', 'li', 'br') and self.section in SOURCE_SECTIONS:
            self.parts[self.section].append(' ')

    def handle_endtag(self, tag):
        if self.section is None:
            return
        if tag == 'blockquote':
            self.in_blockquote = False
        if tag == 'li':
            self.in_question = False
        if tag == 'ol':
            self.in_question_list = False
        if tag == 'section':
            self.depth -= 1
            if self.depth == 0:
                self.section = None
        if tag in ('p', 'h2', 'h3', 'li', 'br') and self.section in SOURCE_SECTIONS:
            self.parts[self.section].append(' ')

    def handle_data(self, data):
        if 'CC BY 4.0' in data:
            self.license_marker = True
        if self.section in SOURCE_SECTIONS and not self.in_blockquote:
            self.parts[self.section].append(data)
        if self.section == 'discussion-questions' and self.in_question:
            self.questions[-1].append(data)


def _normalize(value):
    return ' '.join(value.split())


def build_development_case(html_bytes):
    """Fail closed on source drift, missing native structure or quoted blocks."""
    if not isinstance(html_bytes, bytes) or hashlib.sha256(html_bytes).hexdigest() != PINNED_HTML_SHA256:
        raise ValueError('pinned publisher HTML changed')
    parser = _NativeCaseParser()
    parser.feed(html_bytes.decode('utf-8'))
    if not parser.license_marker or parser.blockquotes or len(parser.questions) != 5:
        raise ValueError('native license, section or question structure changed')
    sections = [_normalize(''.join(parser.parts[key])) for key in SOURCE_SECTIONS]
    question = _normalize(''.join(parser.questions[QUESTION_ORDINAL - 1]))
    if any(len(section) < 400 for section in sections) or len(question) < 50:
        raise ValueError('empty or incomplete native source/question')
    source = '\n\n'.join(sections)
    return {
        'source_text': source,
        'question': question,
        'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
        'question_sha256': hashlib.sha256(question.encode()).hexdigest(),
        'status': 'DEVELOPMENT_EXPOSED_NOT_CONFIRMATION',
        'source_sections': SOURCE_SECTIONS,
        'native_question_ordinal': QUESTION_ORDINAL,
        'native_question_count': len(parser.questions),
    }
