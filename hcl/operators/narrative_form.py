"""Literal form measurements for original passages or explicit variants.

Counts are Unicode code-point/byte and literal-pattern facts, not aesthetic
scores, prosody, semantic imagery detection or a claim about reader emotions.
Callers bind these texts to authorized sources or marked hypothetical variants.
"""

from hashlib import sha256

from hcl.memory import codec

VERSION = "narrative-form-1"
PUNCTUATION = ".!?。！？,，;；:：—–-…()（）[]【】“”\"'‘’"


def measure_form(passages, motifs, max_work):
    """Bounded left-to-right measurements with exact incomplete-range evidence.

    Motifs are finite literal strings proposed by a source-bound compiler. KMP
    matchers retain overlapping occurrences; there is no case/Unicode rewriting.
    Each transition/comparison is charged before execution. A partial scan does
    not certify the absence of a pattern in its remaining text.
    """
    if (
        type(max_work) is not int
        or max_work < 0
        or len(passages) > 4096
        or len(motifs) > 64
        or len({row["id"] for row in passages}) != len(passages)
        or any(
            type(row["id"]) is not str or not row["id"] or type(row["text"]) is not str
            for row in passages
        )
        or any(
            type(key) is not str
            or not key
            or type(pattern) is not str
            or not 0 < len(pattern) <= 256
            for key, pattern in motifs.items()
        )
    ):
        raise ValueError("bounded explicit passage and literal-motif inputs required")
    if sum(len(row["text"]) for row in passages) > 4 * 1024 * 1024:
        raise ValueError("bounded narrative source size required")
    for row in passages:
        row["text"].encode("utf-8")
    for pattern in motifs.values():
        pattern.encode("utf-8")
    work = 0

    class Exhausted(Exception):
        pass

    def charge():
        nonlocal work
        if work >= max_work:
            raise Exhausted()
        work += 1

    tables = {}
    rows = []
    frontier = []
    try:
        for key, pattern in sorted(motifs.items()):
            prefix, size = [0] * len(pattern), 0
            for position in range(1, len(pattern)):
                while size:
                    charge()
                    if pattern[position] == pattern[size]:
                        break
                    size = prefix[size - 1]
                charge()
                if pattern[position] == pattern[size]:
                    size += 1
                prefix[position] = size
            tables[key] = prefix
    except Exhausted:
        frontier.append("FORM_PATTERN_PREPARATION_FRONTIER")
    for passage in passages:
        text = passage["text"]
        output = dict(
            id=passage["id"],
            text_sha256=sha256(text.encode()).hexdigest(),
            total_characters=len(text),
            total_utf8_bytes=len(text.encode()),
            scanned_characters=0,
            punctuation={},
            linebreak_positions=[],
            motif_positions={key: [] for key in sorted(motifs)},
            status="UNCOMPUTED",
        )
        states = {key: 0 for key in tables}
        if not frontier:
            try:
                for position, char in enumerate(text):
                    # Complete a code point atomically in this receipt: if a
                    # motif step exhausts, don't publish half-updated counts.
                    new_states, found = {}, []
                    charge()
                    for key, pattern in sorted(motifs.items()):
                        state = states[key]
                        while state:
                            charge()
                            if char == pattern[state]:
                                break
                            state = tables[key][state - 1]
                        charge()
                        if char == pattern[state]:
                            state += 1
                        if state == len(pattern):
                            found.append((key, position - len(pattern) + 1))
                            state = tables[key][state - 1]
                        new_states[key] = state
                    states = new_states
                    if char in PUNCTUATION:
                        output["punctuation"][char] = (
                            output["punctuation"].get(char, 0) + 1
                        )
                    if char == "\n":
                        output["linebreak_positions"].append(position)
                    for key, start in found:
                        output["motif_positions"][key].append(start)
                    output["scanned_characters"] = position + 1
                output["status"] = "COMPLETE_LITERAL_SCAN"
            except Exhausted:
                frontier.append("FORM_SCAN_FRONTIER")
                output["status"] = "PARTIAL_LITERAL_SCAN"
        output["unread_range"] = (output["scanned_characters"], len(text))
        rows.append(output)
    result = dict(
        schema=VERSION,
        work=work,
        passages=rows,
        motifs=dict(sorted(motifs.items())),
        frontier=tuple(sorted(set(frontier))),
        qualifications=("LITERAL_FORM_NOT_SEMANTIC_OR_AESTHETIC_VERDICT",),
    )
    result["input_identity"] = sha256(codec.dumps([passages, motifs])).hexdigest()
    return result
