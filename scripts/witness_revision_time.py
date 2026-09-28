"""B03 ordinary dialogue distinguishes two kinds of revision; no provider."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hcl.cognition import RevisionTimeline


def witness():
    stamp = lambda n: f'2026-01-{n:02d}T12:00:00+00:00'
    timeline = RevisionTimeline('authored-b03-scene')
    timeline.record('initial', 'Mira said, "I believe the gate is open."', event_time=stamp(1), recorded_at=stamp(1))
    timeline.record('unrelated', 'Noor said, "I believe the road is safe."', event_time=stamp(1), recorded_at=stamp(1))
    timeline.record('change', 'Mira said, "I now believe the gate is closed instead of the gate is open."', event_time=stamp(2), recorded_at=stamp(2))
    early = timeline.snapshot(event_time=stamp(1), known_at=stamp(2))
    changed = timeline.snapshot(event_time=stamp(2), known_at=stamp(2))
    timeline.record('initial', 'Mira said, "I am unsure whether the gate is open."', event_time=stamp(1), recorded_at=stamp(3))
    revised_past = timeline.snapshot(event_time=stamp(1), known_at=stamp(3))
    revised_current = timeline.snapshot(event_time=stamp(2), known_at=stamp(3))
    assert timeline.snapshot(event_time=stamp(1), known_at=stamp(2)) == early
    def status(snapshot, actor, proposition):
        return next(r['status'] for r in snapshot.payload['estimates']
            if r['subject_agent_id'] == actor and r['proposition_key'] == proposition)
    assert status(early, 'Mira', 'the gate is open') == 'AFFIRMED'
    assert status(changed, 'Mira', 'the gate is open') == 'SUPERSEDED'
    assert status(revised_past, 'Mira', 'the gate is open') == 'CHARACTER_UNCERTAIN'
    assert status(revised_current, 'Mira', 'the gate is open') == 'CHARACTER_UNCERTAIN'
    assert status(revised_current, 'Mira', 'the gate is closed') == 'AFFIRMED'
    assert [r for r in early.payload['estimates'] if r['subject_agent_id'] == 'Noor'] == [r for r in revised_past.payload['estimates'] if r['subject_agent_id'] == 'Noor']
    return dict(schema='hcl-b03-positive-witness-v1',
        capability_delta='Explicit character revision supersedes an anchored earlier expression; a later source correction instead revises the analyst interpretation of the past, preserves the earlier known-at snapshot, removes an unsupported revision anchor, and leaves Noor unchanged.',
        snapshots={name: dict(cognition=snap.payload, actual_final_messages=snap.messages('What changed for Mira, and what was known then?'))
            for name, snap in [('earlier_knowledge', early), ('reported_character_revision', changed),
                ('corrected_past_interpretation', revised_past), ('corrected_current_interpretation', revised_current)]},
        implementation='CORRECTNESS_VERIFIED', ordinary_input='REPLAY_VERIFIED', efficacy='UNTESTED', activation='OPT_IN',
        provider_calls=0, provider_spend_usd=0, longmemeval='SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('reports/HCL_WAVE_B03_WITNESS.json')
    target.write_text(json.dumps(witness(), ensure_ascii=False, indent=2) + '\n')
    print(target)
