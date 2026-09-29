"""F05 ordinary multi-source replay, branch contrast, revision and scale smoke."""
from hashlib import sha256
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from hcl.cognition.long_narrative import NarrativeCorpus

STAMP='2026-01-08T00:00:00Z'
SOURCES={
    'main-a':'Narrator: On 2026-01-02, Mira said, "I believe the gate is open."',
    'main-b':'Narrator: On 2026-01-02, Mira said, "I do not believe the gate is open."',
    'change':'\n'.join([
        'Narrator: On 2026-01-01, Mira said, "I did not know that the report was ready."',
        'Narrator: On 2026-01-02, Mira did not submit the report.',
        'Narrator: On 2026-01-03, Mira said, "I now know that the report was ready."',
        'Narrator: On 2026-01-05, Mira did submit the report.']),
    'alternative':'Narrator: On 2026-01-02, Mira said, "I do not believe the gate is open."',
}


def witness():
    corpus=NarrativeCorpus()
    for source_id,text in SOURCES.items():
        corpus.put_chapter(source_id,text,branch='alternate' if source_id=='alternative' else 'main',
            recorded_at=STAMP,permitted_observers=('Analyst',))
    def replay(day):
        return corpus.replay('Mira',branch='main',story_through=day,disclosed_through=day,
            known_at=STAMP,observer='Analyst',development_source='change',development_action='submit the report')
    early,middle,late=(replay(day) for day in ('2026-01-02','2026-01-03','2026-01-05'))
    assert [len(v.payload['events']) for v in (early,middle,late)]==[4,5,6]
    assert len(late.payload['source_conflicts'])==1
    assert len(late.payload['development']['candidates'])==1
    branches=corpus.compare_branches('Mira','main','alternate',story_through='2026-01-05',
        disclosed_through='2026-01-05',known_at=STAMP,observer='Analyst')
    assert len(branches.payload['divergences'])==1
    corpus.put_chapter('main-a',SOURCES['main-a'].replace('open','closed'),branch='main',
        recorded_at='2026-01-09T00:00:00Z',permitted_observers=('Analyst',))
    corrected=corpus.replay('Mira',branch='main',story_through='2026-01-05',
        disclosed_through='2026-01-05',known_at='2026-01-09T00:00:00Z',observer='Analyst')
    assert corrected.payload['source_conflicts']==[]

    scale=NarrativeCorpus();filler=' '.join(f'detail{n}' for n in range(160));manifest=[]
    for actor_index in range(12):
        actor=f'Actor{actor_index}'
        chapter='\n'.join(f'Narrator: On 2026-01-{day:02d}, {actor} said, "I believe event {day} for {actor} is recorded with {filler}."'
            for day in range(1,11))
        source_id=f'chapter-{actor_index}'
        scale.put_chapter(source_id,chapter,branch='main',recorded_at=STAMP,permitted_observers=('Analyst',))
        manifest.append(dict(source_id=source_id,sha256=sha256(chapter.encode()).hexdigest(),characters=len(chapter),
            whitespace_words=len(chapter.split()),events=10))
    scale_view=scale.replay('Actor0',branch='main',story_through='2026-01-10',
        disclosed_through='2026-01-10',known_at=STAMP,observer='Analyst')
    assert sum(row['events'] for row in manifest)==120 and len(scale_view.payload['events'])==10
    return dict(schema='hcl-f05-positive-witness-v1',
        capability_delta='An authorized, branch-specific multi-chapter projection replays a named actor over separate time axes, preserves opposing source reports with full evidence and keeps an alternate story path separate.',
        ordinary_sources=SOURCES,early=early.payload,middle=middle.payload,late=late.payload,
        branch_comparison=branches.payload,after_source_correction=corrected.payload,
        actual_final_model_messages=late.messages(corpus,'How do the reports about Mira differ across this story path?'),
        scale_smoke=dict(active_actors=12,source_chapters=12,events=120,total_characters=sum(row['characters'] for row in manifest),
            whitespace_words=sum(row['whitespace_words'] for row in manifest),source_manifest=manifest,
            selected_events=len(scale_view.payload['events']),
            actual_selected_model_messages=scale_view.messages(scale,'What was reported by Actor0?')),
        implementation='CORRECTNESS_VERIFIED',ordinary_input='REPLAY_VERIFIED',efficacy='UNTESTED',activation='OPT_IN',
        provider_calls=0,provider_spend_usd=0,longmemeval='SEALED_NOT_ACCESSED')


if __name__=='__main__':
    target=Path(sys.argv[1] if len(sys.argv)>1 else 'reports/HCL_WAVE_F05_WITNESS.json')
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(witness(),ensure_ascii=False,indent=2)+'\n')
