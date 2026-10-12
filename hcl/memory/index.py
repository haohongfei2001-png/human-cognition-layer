"""Rebuildable lexical indexes over exact original source regions.

Sparse TF-IDF is a real corpus-derived vector representation, not a semantic
embedding or an open-language entailment model. Corpus statistics are computed
by the retrieval layer only AFTER current-principal ACL filtering.
"""
from collections import Counter
from collections.abc import Mapping
from hashlib import sha256
import re

from hcl.kernel.types import freeze, thaw
from hcl.semantics.segments import iter_segments

INDEX_SCHEMA = "hcl-retrieval-source-index-1"
INDEX_VERSION = "mechanical-regions-bm25-tfidf-2"
TOKENIZER = "unicode-casefold-words-cjk-planes-bigrams-2"
# Explicit code-point ranges, rather than the interpreter's Unicode character
# categories. Supplementary CJK runs must survive even on an older Python UCD.
# Reserved points in these ranges are lexical symbols, not a semantic claim
# that a particular Unicode release assigns every point to an ideograph.
_CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"
                  r"\U00020000-\U0002fffd\U00030000-\U0003fffd]+")
_WORDS = re.compile(r"[^\W_]+(?:['’][^\W_]+)?", re.UNICODE)


def terms(text):
    """Deterministic words plus CJK unigrams/bigrams; no inferred synonyms."""
    if type(text) is not str:
        raise ValueError("Unicode query text required")
    text.encode("utf-8")
    output = []
    text = text.casefold()
    start = 0
    for match in _CJK.finditer(text):
        output.extend(_WORDS.findall(text[start:match.start()]))
        run = match.group()
        output.extend(run)
        output.extend(run[n:n+2] for n in range(len(run)-1))
        start = match.end()
    output.extend(_WORDS.findall(text[start:]))
    return tuple(output)


def build_index(source, *, max_regions=65536):
    """Pure, exact source-version index; bounded prefix exposes its unread tail.

    A mechanical region does not invent chapter/event/viewpoint/topic labels.
    Such semantic indexes must retain their separate source-bound provenance.
    """
    if type(max_regions) is not int or not 0 <= max_regions <= 65536:
        raise ValueError("bounded region count required")
    rows, read_end = [], 0
    for segment in iter_segments(source.text, source.handle.source_id, source.handle.version, "SOURCE"):
        if len(rows) == max_regions:
            break
        rows.append(dict(segment_id=segment.segment_id, start=segment.start, end=segment.end,
                         byte_start=segment.byte_start, byte_end=segment.byte_end,
                         counts=dict(sorted(Counter(terms(segment.text)).items()))))
        read_end = segment.end
    return freeze(dict(schema=INDEX_SCHEMA, version=INDEX_VERSION, tokenizer=TOKENIZER,
                       source_id=source.handle.source_id, source_version=source.handle.version,
                       source_sha256=sha256(source.text.encode()).hexdigest(),
                       character_count=len(source.text), byte_count=len(source.text.encode()),
                       regions=rows, indexed_end=read_end, complete=read_end == len(source.text),
                       semantic_coverage="NOT_ESTABLISHED"))


def validate_index(index, source):
    """A cached projection never certifies its own source binding or tokenization."""
    if not isinstance(index, Mapping) or type(index.get("regions")) not in (list, tuple):
        raise ValueError("typed source index required")
    expected = build_index(source, max_regions=len(index["regions"]))
    if expected != freeze(index):
        raise ValueError("source index differs from exact mechanical rebuild")
    return expected


def index_identity(index):
    from hcl.memory.codec import canonical
    return sha256(canonical(thaw(index)).encode()).hexdigest()
