"""F02 positive witness: late disclosure, recall, challenge and explicit receipt."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from hcl.cognition.narrative_time import NarrativeTimeline

SOURCE='\n'.join((
    'Narrator: On 2026-01-02, Mira said, "I believe the bridge is closed."',
    'Narrator: On 2026-01-05, Noor disclosed a recollection from 2026-01-03 of Mira saying on 2026-01-01, "I believe the bridge is open."',
    "Narrator: On 2026-01-06, Kai challenged Noor's recollection from 2026-01-03 of Mira's statement on 2026-01-01.",
    "Narrator: On 2026-01-07, Mira heard Noor's disclosure from 2026-01-05."))


def witness():
    timeline=NarrativeTimeline()
    timeline.put_chapter('authored-f02-chapter',SOURCE,recorded_at='2026-01-08T00:00:00Z',permitted_observers=('Analyst',))
    def view(disclosed,character=None):
        return timeline.snapshot(story_through='2026-01-03',disclosed_through=disclosed,
            known_at='2026-01-08T00:00:00Z',observer='Analyst',character=character)
    early=view('2026-01-03');late=view('2026-01-05');challenged=view('2026-01-06')
    no_receipt=view('2026-01-06','Mira');received=view('2026-01-07','Mira')
    assert len(early.payload['narrative_order_events'])==1
    assert [r['story_time'] for r in late.payload['narrative_order_events']]==['2026-01-02','2026-01-01']
    assert challenged.payload['narrative_order_events'][1]['challenge_status']=='CONTESTED_SOURCE_RECOLLECTION_NOT_FALSIFIED'
    assert no_receipt.payload['narrative_order_events']==[]
    assert received.payload['narrative_order_events'][0]['receipt_source']['quote']==SOURCE.splitlines()[-1]
    messages={name:snapshot.messages(timeline,'What was reported about the bridge?') for name,snapshot in
        (('early',early),('late',late),('challenged',challenged),('Mira_before_receipt',no_receipt),('Mira_after_receipt',received))}
    return dict(schema='hcl-f02-positive-witness-v1',
        capability_delta='An old remembered event disclosed later enters only the later source view; a challenge marks it contested and explicit receipt changes Mira\'s information view without proving belief.',
        actual_final_messages=messages,source=SOURCE,implementation='CORRECTNESS_VERIFIED',ordinary_input='REPLAY_VERIFIED',
        efficacy='UNTESTED',activation='OPT_IN',provider_calls=0,provider_spend_usd=0,longmemeval='SEALED_NOT_ACCESSED')


if __name__=='__main__':
    target=Path(sys.argv[1] if len(sys.argv)>1 else 'reports/HCL_WAVE_F02_WITNESS.json')
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(witness(),ensure_ascii=False,indent=2)+'\n')
