import json
import unittest
from hcl.cognition.agency_chain import SemanticWorkspace
from hcl.cognition.identity_roles import prepare_identity_roles
from hcl.cognition.semantic import AuthorizedText, _local_candidates, prepare_semantics

SOURCE = '\n'.join(('Mira said, "In team, I see myself as careful."',
    'Noor said, "In team, I see Mira as careless."',
    'Narrator: In team, Mira serves as reviewer.',
    'Narrator: In team, a reviewer is required to check every patch.',
    'Narrator: In team, Mira did not check every patch.',
    'Mira said, "In team, I reject the requirement for a reviewer to check every patch."'))
QUERY = "How does Mira's self-description relate to the reviewer role in team?"


class IdentityRoleTests(unittest.TestCase):
    def prepare(self, source=SOURCE, observer=None, backend=None):
        w = SemanticWorkspace(semantic_backend=backend)
        w.put_source('scene', source)
        return w, prepare_identity_roles(w, QUERY, source_id='scene', observer=observer)

    def test_positive_separate_identity_role_norm_behavior_endorsement(self):
        w, result = self.prepare()
        p = result.payload
        self.assertEqual(p['current_self_descriptions'][0]['label'], 'careful')
        self.assertEqual(p['other_identity_attributions'][0]['label'], 'careless')
        self.assertEqual(p['role_status'], 'REPORTED_OCCUPANT')
        self.assertEqual(p['requirement_endorsements'][0]['endorsement'], 'REJECTS')
        self.assertEqual(p['behavior_checks'][0]['status'], 'DOES_NOT_MEET_DECLARED_REQUIREMENT')
        self.assertTrue(p['local_tension'])
        self.assertFalse(p['identity_rewritten_from_behavior'])
        self.assertIn('actual_identity', result.messages(w)[1]['content'])

    def test_occupancy_and_compliance_not_endorsement(self):
        source = '\n'.join(SOURCE.splitlines()[:-1]).replace('did not check', 'did check')
        _, result = self.prepare(source)
        self.assertEqual(result.payload['requirement_endorsements'][0]['endorsement'], 'NOT_REPORTED')
        self.assertEqual(result.payload['behavior_checks'][0]['status'], 'MEETS_DECLARED_REQUIREMENT')

    def test_role_exit_not_identity_erasure_or_retroactive_behavior_change(self):
        _, result = self.prepare(SOURCE + '\nNarrator: In team, Mira no longer serves as reviewer.')
        self.assertEqual(result.payload['role_status'], 'REPORTED_NOT_OCCUPANT')
        self.assertEqual(result.payload['current_self_descriptions'][0]['label'], 'careful')
        self.assertEqual(result.payload['behavior_checks'][0]['status'], 'DOES_NOT_MEET_DECLARED_REQUIREMENT')

    def test_explicit_self_revision_and_bad_anchor(self):
        _, result = self.prepare(SOURCE + '\nMira said, "In team, I now see myself as learning instead of careful."')
        self.assertEqual(result.payload['current_self_descriptions'][0]['label'], 'learning')
        self.assertEqual(result.payload['historical_self_descriptions'][0]['label'], 'careful')
        _, bad = self.prepare(SOURCE + '\nMira said, "In team, I now see myself as learning instead of expert."')
        self.assertEqual(bad.payload['current_self_descriptions'][0]['label'], 'careful')
        self.assertTrue(bad.payload['diagnostics'])

    def test_later_role_rule_not_backfilled(self):
        lines = SOURCE.splitlines()
        source = '\n'.join([lines[4], *lines[:4], lines[5]])
        _, result = self.prepare(source)
        self.assertEqual(result.payload['behavior_checks'][0]['status'], 'ROLE_OR_REQUIREMENT_UNRESOLVED_AT_BEHAVIOR')

    def test_third_party_endorsement_not_personal(self):
        _, result = self.prepare(SOURCE.replace('Mira said, "In team, I reject', 'Noor said, "In team, I reject'))
        self.assertEqual(result.payload['requirement_endorsements'][0]['endorsement'], 'NOT_REPORTED')

    def test_other_context_and_role_not_merged(self):
        _, result = self.prepare(SOURCE.replace('a reviewer is required', 'an editor is required').replace('In team, Mira serves', 'In club, Mira serves'))
        self.assertEqual(result.payload['role_status'], 'UNKNOWN')
        self.assertEqual(result.payload['source_requirements'], [])

    def test_uncertain_or_conflicting_endorsement(self):
        _, result = self.prepare(SOURCE.replace('I reject', 'I am unsure about'))
        self.assertEqual(result.payload['requirement_endorsements'][0]['endorsement'], 'CHARACTER_UNCERTAIN')
        _, result = self.prepare(SOURCE + '\n' + SOURCE.splitlines()[-1].replace('I reject', 'I endorse'))
        self.assertEqual(result.payload['requirement_endorsements'][0]['endorsement'], 'CONFLICTING_REPORTED_POSITIONS')

    def test_hidden_stale_support_and_budget(self):
        w, result = self.prepare(observer='Kai')
        self.assertNotIn('Mira said', json.dumps(result.messages(w)))
        w, result = self.prepare()
        with self.assertRaisesRegex(ValueError, 'budget'):
            result.messages(w, max_chars=1000)
        w.core.withdraw(result.claim_ids[0])
        with self.assertRaisesRegex(ValueError, 'support changed'):
            result.messages(w)
        w, result = self.prepare()
        w.put_source('scene', SOURCE + '\nNoor said, "Okay."')
        with self.assertRaisesRegex(ValueError, 'source changed'):
            result.messages(w)

    def test_minimal_backend_event_contract_feeds_runtime(self):
        class Replay:
            calls = 0
            def complete_json(self, messages, **kwargs):
                self.calls += 1
                sources = json.loads(messages[1]['content'])['sources']
                return json.dumps(dict(candidates=[dict(source_id=r['source_id'], quote=r['quote'], kind='event', content={k:r['content'][k] for k in ('speaker_surface','utterance')})
                    for s in sources for r in _local_candidates(AuthorizedText(**s)) if r['kind'] == 'event']))
        backend = Replay()
        w, result = self.prepare(backend=backend)
        self.assertEqual(backend.calls, 1)
        self.assertEqual(result.payload['role_status'], 'REPORTED_OCCUPANT')
        self.assertEqual(result.payload['requirement_endorsements'][0]['endorsement'], 'REJECTS')
        receipt = next(iter(w.semantic_cache.values()))
        self.assertTrue(all('source_derived_event_envelope' in w.core.claims[c].content for c in receipt.candidate_ids))

    def test_backend_cannot_supply_spoofed_metadata_or_private_state(self):
        class Backend:
            def complete_json(self, *args, **kwargs):
                return json.dumps(dict(candidates=[dict(source_id='scene', quote=SOURCE.splitlines()[0], kind='event',
                    content=dict(speaker_surface='Mira', utterance='In team, I see myself as careful.', event_time='2099-01-01', private_identity='careful'))]))
        w, result = self.prepare(backend=Backend())
        self.assertEqual(result.payload['current_self_descriptions'], [])
        candidate = next(iter(w.semantic_cache.values())).candidate_ids[0]
        self.assertEqual(w.core.claims[candidate].content['validation']['semantic_support'], 'UNVERIFIED_CANDIDATE')

    def test_minimal_schema_does_not_escape_conditional_source(self):
        source = 'If Mira said, "In team, I see myself as careful."'
        class Backend:
            def complete_json(self, *args, **kwargs):
                return json.dumps(dict(candidates=[dict(source_id='scene', quote=source[3:], kind='event',
                    content=dict(speaker_surface='Mira', utterance='In team, I see myself as careful.'))]))
        _, result = self.prepare(source, backend=Backend())
        self.assertEqual(result.payload['current_self_descriptions'], [])


if __name__ == '__main__':
    unittest.main()
