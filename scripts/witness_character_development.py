"""F04 ordinary source to rival explanations and actual final model input."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from hcl.cognition.character_development import compare_character_development
from hcl.cognition.narrative_time import NarrativeTimeline

SOURCE='''Narrator: On 2026-01-01, Mira said, "I did not know that the report was ready."
Narrator: On 2026-01-01, Mira said, "I want to protect the report."
Narrator: On 2026-01-01, Mira said, "As reviewer in team, I prefer safety over speed."
Narrator: On 2026-01-02, Mira did not submit the report.
Narrator: On 2026-01-03, Mira said, "I now know that the report was ready."
Narrator: On 2026-01-03, Mira became reviewer in team.
Narrator: On 2026-01-04, Mira said, "As reviewer in team, I faced pressure to submit the report."
Narrator: On 2026-01-04, Mira said, "I now want to submit the report instead of protect the report."
Narrator: On 2026-01-04, Mira said, "As reviewer in team, I now prefer speed over safety instead of safety over speed."
Narrator: On 2026-01-04, Mira said, "I told Noor I wanted to submit the report so Noor would approve my plan."
Narrator: On 2026-01-05, Mira did submit the report.'''


def witness():
    timeline=NarrativeTimeline()
    timeline.put_chapter('ordinary-chapter',SOURCE,recorded_at='2026-01-08T00:00:00Z',permitted_observers=('Analyst',))
    early=compare_character_development(timeline,'ordinary-chapter','Mira','submit the report',
        through_date='2026-01-02',known_at='2026-01-08T00:00:00Z',observer='Analyst')
    later=compare_character_development(timeline,'ordinary-chapter','Mira','submit the report',
        through_date='2026-01-05',known_at='2026-01-08T00:00:00Z',observer='Analyst')
    assert early.payload['status']=='NO_UNAMBIGUOUS_COMPARABLE_ACTION_CHANGE'
    assert len(later.payload['candidates'])==5
    assert later.payload['recorded_evidence_closure']['selection']=='FULL_RECORDED_GRAPH_CLOSURE'
    return dict(schema='hcl-f04-positive-witness-v1',capability_delta='Ordinary dated source yields five simultaneous, source-anchored conditional explanations of an apparent action change without guessing private motive or moral character.',
        ordinary_source=SOURCE,early=early.payload,later=later.payload,
        actual_final_model_messages=later.messages(timeline,'What source-conditioned explanations could account for the apparent change in Mira?'),
        implementation='CORRECTNESS_VERIFIED',ordinary_input='REPLAY_VERIFIED',efficacy='UNTESTED',activation='OPT_IN',
        provider_calls=0,provider_spend_usd=0,longmemeval='SEALED_NOT_ACCESSED')


if __name__=='__main__':
    target=Path(sys.argv[1] if len(sys.argv)>1 else 'reports/HCL_WAVE_F04_WITNESS.json')
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(witness(),ensure_ascii=False,indent=2)+'\n')
