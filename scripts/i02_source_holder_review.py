"""Generic pre-output source holder contract; metadata validation is not semantic truth."""
import json
from scripts.i02_gilman_protected_candidate import QUESTION

INSTRUCTION = '''You are a source-first task auditor. You receive only a complete original source and a predeclared ordinary question, no model-arm answer or cognition architecture. This is a preliminary automated audit, not moral truth, independent human expert certification, or proof of difficulty. Do not invent events, diagnoses or private intentions. Assess whether this task requires temporally differentiated understanding of a person, beyond isolated fact retrieval. Keep narrator report, reported speech, hypothesis and objectively established event separate. Source order does not by itself prove story-time order. Retain uncertainty about intentions and narrator reliability. Do not change the question or select a task favorable to any system. Do not assess baseline saturation or any system's benefit.
Return a single JSON object with exactly: family_judgment, answerability_judgment (each PASS, REJECT or UNRESOLVED); episodes (array of objects with exactly id, quote, evidence_kind, time_basis, analysis); obligations (array of objects with exactly id, expectation, quote, audit_question); serious_unsupported_upgrades (array of strings); unresolved_limits (array of strings); judge_limits (string).
Use globally unique ids across episodes and obligations. For PASS family_judgment, provide at least three distinct source-supported episodes involving differing views across the source. Each quote must be one exact nonempty substring of the supplied source, preferably a short SINGLE LINE of 12-120 characters, occurring once; preserve spelling, punctuation and whitespace. Never paraphrase a quote. Sort episodes by their source position. evidence_kind is NARRATOR_REPORT, REPORTED_SPEECH, INFERENCE_OR_UNCERTAIN or EXPLICIT_EVENT; time_basis is SOURCE_ORDER_ONLY, EXPLICIT_STORY_TIME or UNRESOLVED. analysis must explain support and uncertainty without upgrading the narrator's report to objective fact. If the source does not support the fixed question/family, use REJECT or UNRESOLVED instead of inventing support. Provide 3-6 pre-output source-led obligations including STATE, QUALIFY and AVOID, each anchored by an exact quote; allow defensible competing interpretations rather than one value verdict. Include serious errors such as unsupported private intention, automatic clinical diagnosis or treating a narrative belief as unquestioned reality. A structural checker will verify quotes, not semantic accuracy. No reference answers, hidden mental-state labels or system-specific labels are available. All judgments remain preliminary.'''


def messages(source_id, source):
    return [dict(role='system', content=INSTRUCTION), dict(role='user', content=json.dumps(
        dict(question=QUESTION, sources=[dict(source_id=source_id, text=source)]), ensure_ascii=False))]


def validate_review(value, source):
    required = {'family_judgment', 'answerability_judgment', 'episodes', 'obligations',
                'serious_unsupported_upgrades', 'unresolved_limits', 'judge_limits'}
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError('source review shape mismatch')
    if any(value[k] not in {'PASS', 'REJECT', 'UNRESOLVED'} for k in ('family_judgment', 'answerability_judgment')):
        raise ValueError('unknown preliminary judgment')
    if (not isinstance(value['episodes'], list) or len(value['episodes']) > 8 or
            (value['family_judgment'] == 'PASS' and len(value['episodes']) < 3)):
        raise ValueError('source episode coverage incomplete')
    positions = []; ids = set()
    def anchor(row, fields):
        if (not isinstance(row, dict) or set(row) != fields or
                any(not isinstance(row[k], str) or not row[k].strip() for k in fields)):
            raise ValueError('source anchor row incomplete')
        quote = row['quote']
        if not 1 <= len(quote) <= 500 or source.count(quote) != 1 or row['id'] in ids:
            raise ValueError('source quote absent, repeated, overlong or duplicate ID')
        ids.add(row['id'])
        return source.index(quote)
    for row in value['episodes']:
        positions.append(anchor(row, {'id', 'quote', 'evidence_kind', 'time_basis', 'analysis'}))
        if (row['evidence_kind'] not in {'NARRATOR_REPORT', 'REPORTED_SPEECH', 'INFERENCE_OR_UNCERTAIN', 'EXPLICIT_EVENT'} or
                row['time_basis'] not in {'SOURCE_ORDER_ONLY', 'EXPLICIT_STORY_TIME', 'UNRESOLVED'}):
            raise ValueError('source/time category invalid')
    if positions != sorted(set(positions)):
        raise ValueError('distinct source order required; not automatic story chronology')
    if not isinstance(value['obligations'], list) or not 3 <= len(value['obligations']) <= 6:
        raise ValueError('pre-output obligations incomplete')
    expectations = set()
    for row in value['obligations']:
        anchor(row, {'id', 'expectation', 'quote', 'audit_question'})
        expectations.add(row['expectation'])
    if expectations != {'STATE', 'QUALIFY', 'AVOID'}:
        raise ValueError('all supported content, qualification and inference boundaries required')
    for k in ('serious_unsupported_upgrades', 'unresolved_limits'):
        if not isinstance(value[k], list) or any(not isinstance(x, str) or not x.strip() for x in value[k]):
            raise ValueError('reasoned error/limit list required')
    if not value['serious_unsupported_upgrades'] or not isinstance(value['judge_limits'], str) or not value['judge_limits'].strip():
        raise ValueError('judge limitations and critical inference errors required')
    return dict(status='STRUCTURE_AND_EXACT_QUOTES_VALID_PRELIMINARY_ONLY',
        family_judgment=value['family_judgment'], answerability_judgment=value['answerability_judgment'],
        episode_count=len(positions), obligation_count=len(value['obligations']),
        distinct_source_order_verified=True, story_time_semantics_verified=False,
        semantic_truth_verified=False, independent_human_review=False,
        confirmation_qualified=False, h_efficacy='NOT_TESTED')
