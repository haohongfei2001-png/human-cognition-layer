"""New authored long-input transport fixture, never independent human-cognition evidence."""
import hashlib
import json
from pathlib import Path
SOURCE_ID='authored-i02-v3-long-source-interface-calibration'
QUESTION="Across the account, how did Mina's explicitly reported view of the project change in January, April and May? Separate the later reporting date from event time, and keep Ravi's intention and the committee's normative claim uncertain."
PATH=Path('reports/HCL_I02_SOURCE_HOLDER_V3_CALIBRATION_FIXTURE.json')


def build_fixture():
    first='On 10 January, Mina said she supported the project on the limited information she had.\r\n'
    second='On 15 June, Mina reported that in April she had become uncertain after receiving a revised project notice.\r\n'
    third='On 20 May, Mina said she declined the project because the conditions were still unclear.\r\n'
    tail='Ravi did not explain his intention. The committee called Mina negligent under its own stated rule; the account does not establish that rule as moral truth.\r\n'
    # Filler is complete source text, not summarized or stripped at model entry.
    def records(start,count):
        return ''.join(f'Office record {n:04d}: blank forms were stored in the cabinet; this entry reports no person intention.\r\n' for n in range(start,start+count))
    source=first+records(1,400)+second+records(401,400)+third+tail
    return dict(schema='hcl-i02-v3-authored-long-calibration-fixture-v1',source_id=SOURCE_ID,
        source_text=source,ordinary_question=QUESTION,source_sha256=hashlib.sha256(source.encode()).hexdigest(),
        question_sha256=hashlib.sha256(QUESTION.encode()).hexdigest(),source_characters=len(source),
        source_origin='HCL_AUTHORED_SYNTHETIC_TRANSPORT_FIXTURE',rights='HCL_AUTHORED_PUBLIC_FIXTURE_NO_PRIVATE_OWNER_MATERIAL',
        expected_episode_lines=[1,402,803],expected_boundary_line=804,
        expectation_scope='FROZEN_MECHANICAL_ANCHOR_WITNESS_NOT_SEMANTIC_TRUTH_OR_INDEPENDENT_GOLD',
        confirmation_qualified=False,h_efficacy='NOT_TESTED',longmemeval='SEALED_NOT_ACCESSED')


def load_fixture():
    got=json.loads(PATH.read_text())
    if got!=build_fixture():raise ValueError('fixed authored fixture/question/expectations drift')
    return got


def fixture_anchor_witness(resolved,fixture):
    # Gold line numbers never enter the model request. This only checks whether
    # returned evidence spans include the declared literal episode anchors.
    selected={(row['start_line'],row['end_line']) for row in resolved['episodes']}
    present=all(any(a<=line<=z for a,z in selected) for line in fixture['expected_episode_lines'])
    return dict(all_declared_literal_episode_anchors_present=present,
        semantic_time_actor_normative_review_verified=False,independent_evidence=False,
        source_origin=fixture['source_origin'])

if __name__=='__main__':
    PATH.write_text(json.dumps(build_fixture(),indent=2,ensure_ascii=False)+'\n')
