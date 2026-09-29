"""Pinned MuSR source grouping and gold firewall for provider-free calibration."""
import ast
import csv
import hashlib
import io
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.serious_eval_contract import ARMS, FIELDS


UPSTREAM = ('https://huggingface.co/datasets/TAUR-Lab/MuSR/resolve/'
    '7c365b439a222150f317764d4f16ae6c96d7d94a/object_placements.csv')
SOURCE_SHA256 = '98cd17d2c9ea53664e274365e901c90dfcaa40d17547dfbd369f1cd26fd2a81c'
FIRST_GROUP_SHA256 = 'bd0aacf84d7bc7d7fd1fa4114dd05b17aa0c5f2c433d452dfd01b06f7b562d96'


def parse_pinned(raw):
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError('MuSR source bytes differ from pinned distribution')
    rows = list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
    if len(rows) != 256 or set(rows[0]) != {
            'narrative', 'question', 'choices', 'answer_index', 'answer_choice'}:
        raise ValueError('MuSR native row count or schema changed')
    groups = {}
    for i, row in enumerate(rows):
        if not row['narrative'].strip() or not row['question'].strip():
            raise ValueError('empty native narrative/question')
        key = hashlib.sha256(row['narrative'].encode()).hexdigest()
        groups.setdefault(key, []).append(i)
    if len(groups) != 64 or sorted(map(len, groups.values())) != [4] * 64:
        raise ValueError('MuSR rows are not 64 four-question source groups')
    return rows, groups


def calibration_candidate(row, *, source_group_id):
    """Expose only source, native question and choices; labels stay outside arms.

    Only the first inspected source group is eligible for this calibration path.
    Confirmation selection must use a separate frozen procedure after I02.
    """
    if not isinstance(row, dict) or not isinstance(source_group_id, str):
        raise ValueError('typed calibration row and source group required')
    if source_group_id != hashlib.sha256(row['narrative'].encode()).hexdigest() or (
            source_group_id != FIRST_GROUP_SHA256):
        raise ValueError('only the inspected calibration source group is allowed')
    try:
        choices = ast.literal_eval(row['choices'])
    except (SyntaxError, TypeError, ValueError) as exc:
        raise ValueError('native choices not parseable') from exc
    if not isinstance(choices, list) or not 2 <= len(choices) <= 8 or (
            not all(isinstance(c, str) and c.strip() for c in choices)):
        raise ValueError('native choices invalid')
    question = row['question'] + '\nChoices: ' + json.dumps(choices, ensure_ascii=False)
    ordinary = dict(question=question, source_text=row['narrative'])
    candidate = dict(case_id=hashlib.sha256((source_group_id + '\0' + row['question']).encode()).hexdigest(),
        task_family='MULTIPARTY_INFORMATION_STRATEGY', split='CALIBRATION',
        source_origin='INDEPENDENT_NON_HCL_AUTHOR',
        source_license_status='VERIFIED_FOR_THIS_EVALUATION',
        source_access_status='AUTHORIZED_FOR_EVERY_ARM', longmemeval='NOT_USED',
        writing_system_id='TAUR_MUSR_OBJECT_PLACEMENT_GENERATED_NARRATIVE',
        author_id='TAUR_LAB_MUSR', template_id='MUSR_OBJECT_PLACEMENT',
        source_group_id=source_group_id, question=question,
        source_text=row['narrative'],
        arm_inputs={arm: ordinary.copy() for arm in ARMS}, answer_fields=list(FIELDS))
    # The I01 shape guard is necessary but not sufficient for source validity.
    return candidate


def audit_file(path):
    raw = Path(path).read_bytes()
    rows, groups = parse_pinned(raw)
    first = hashlib.sha256(rows[0]['narrative'].encode()).hexdigest()
    if first != FIRST_GROUP_SHA256 or groups[first] != [0, 1, 2, 3]:
        raise ValueError('first inspected narrative is not one complete source group')
    return dict(schema='hcl-i02-musr-calibration-source-audit-v1',
        upstream=UPSTREAM, sha256=SOURCE_SHA256, bytes=len(raw), rows=len(rows),
        independent_narrative_groups=len(groups), questions_per_group=4,
        first_group_source_sha256=first, calibration_exposed_row_indices=groups[first],
        native_labels_in_provider_input=False, confirmation_rows_semantically_inspected=False,
        provider_calls=0, longmemeval='SEALED_NOT_ACCESSED',
        source_semantic_status='FIRST_GROUP_PARTIAL_SECOND_QUESTION_UNCERTAIN',
        source_use='CALIBRATION_ONLY_NOT_CONFIRMATION')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('source_file')
    parser.add_argument('--output')
    args = parser.parse_args()
    result = audit_file(args.source_file)
    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2) + '\n')
    else:
        print(json.dumps(result))
