import json
import unittest
from hcl.cognition.agency_chain import SemanticWorkspace
from hcl.cognition.contextual_values import prepare_contextual_values

QUERY = "Compare Mira's contextual preferences in team."
SOURCE = '\n'.join((
    'Mira said, "As reviewer in team, I prefer safety over speed if urgent is false."',
    'Mira said, "As reviewer in team, I prefer speed over safety if urgent is true."',
    'Narrator: In team, Mira serves as reviewer.',
    'Narrator: In team, urgent is true.',
    'Narrator: In team, Mira chose speed as reviewer.',
    'Narrator: In team, urgent is now false instead of true.',
    'Narrator: In team, Mira chose safety as reviewer.'))


class ContextualValueTests(unittest.TestCase):
    def prepare(self, source=SOURCE, observer=None):
        w=SemanticWorkspace();w.put_source('scene',source)
        return w,prepare_contextual_values(w,QUERY,source_id='scene',observer=observer)

    def test_context_change_explains_different_choices(self):
        w,r=self.prepare();p=r.payload
        self.assertEqual([c['alignment'] for c in p['choices']],['SUPPORTED_BY_LOCAL_COMPARISON']*2)
        self.assertEqual(p['choice_comparisons'][0]['explanation'],'CONTEXT_CHANGE_SUPPORTED_WITHOUT_PREFERENCE_REVISION')
        self.assertEqual(p['current_role_identity_views']['reviewer']['role_status'],'REPORTED_OCCUPANT')
        self.assertEqual(p['private_values'],'NOT_ESTABLISHED')
        self.assertIn('CONTEXT_CHANGE_SUPPORTED',r.messages(w)[1]['content'])

    def test_later_condition_does_not_rewrite_prior_choice(self):
        _,r=self.prepare('\n'.join([*SOURCE.splitlines()[:3],SOURCE.splitlines()[4],SOURCE.splitlines()[3]]))
        self.assertEqual(r.payload['choices'][0]['alignment'],'PARTIAL_OR_UNKNOWN')
        self.assertEqual(r.payload['role_preferences']['reviewer']['order']['strict_comparisons'][0]['preferred'],'speed')

    def test_partial_order_paths_and_incomparability(self):
        source='\n'.join(f'Mira said, "As reviewer in team, I prefer {a} over {b}."' for a,b in [('safety','speed'),('speed','comfort'),('fairness','cost')])
        _,r=self.prepare(source);o=r.payload['role_preferences']['reviewer']['order']
        path=next(p for p in o['strict_comparisons'] if (p['preferred'],p['over'])==('safety','comfort'))
        self.assertEqual(len(path['statement_path']),2)
        self.assertEqual(path['authority'],'CONDITIONAL_TRANSITIVE_PATH')
        self.assertIn(['fairness','safety'],o['incomparable_pairs'])

    def test_cycle_does_not_become_total_order(self):
        source='\n'.join(f'Mira said, "As reviewer in team, I prefer {a} over {b}."' for a,b in [('safety','speed'),('speed','comfort'),('comfort','safety')])
        _,r=self.prepare(source);o=r.payload['role_preferences']['reviewer']['order']
        self.assertEqual(o['status'],'CONFLICTING_DIRECTED_RELATION')
        self.assertEqual(o['strict_comparisons'],[])

    def test_role_tension_not_global_incoherence_or_occupancy(self):
        source='Mira said, "As reviewer in team, I prefer safety over speed."\nMira said, "As editor in team, I prefer speed over safety."'
        _,r=self.prepare(source)
        self.assertEqual(len(r.payload['cross_role_tensions']),1)
        self.assertEqual(r.payload['current_role_identity_views']['editor']['role_status'],'UNKNOWN')

    def test_explicit_revision_reuses_native_checker(self):
        source='Mira said, "As reviewer in team, I prefer safety over speed."\nMira said, "As reviewer in team, I now prefer speed over safety instead of safety over speed."'
        _,r=self.prepare(source)
        rows=r.payload['role_preferences']['reviewer']['native_check']['statements']
        self.assertEqual([x['state'] for x in rows],['SUPERSEDED_LOCAL','APPLICABLE_SOURCE_CLAIM'])

    def test_bad_revision_anchor_unresolved(self):
        _,r=self.prepare(SOURCE.replace('instead of true','instead of false'))
        self.assertEqual(r.payload['choices'][-1]['alignment'],'PARTIAL_OR_UNKNOWN')
        self.assertEqual(r.payload['role_preferences']['reviewer']['status'],'UNRESOLVED_CONDITION_REVISION')

    def test_conflicting_condition_unresolved(self):
        _,r=self.prepare(SOURCE.replace('is now false instead of true','is false'))
        self.assertEqual(r.payload['choices'][-1]['alignment'],'PARTIAL_OR_UNKNOWN')

    def test_other_actor_context_and_third_party_not_self_values(self):
        source=SOURCE.replace('Mira said','Noor said').replace('In team, urgent','In club, urgent')
        _,r=self.prepare(source)
        self.assertEqual(r.payload['choices'][0]['alignment'],'PARTIAL_OR_UNKNOWN')
        self.assertEqual(r.payload['private_values'],'NOT_ESTABLISHED')

    def test_behavior_alone_not_preference(self):
        _,r=self.prepare('Narrator: In team, Mira chose safety as reviewer.')
        self.assertEqual(r.payload['role_preferences']['reviewer']['status'],'NO_EXPLICIT_PREFERENCE')

    def test_hidden_source_not_leaked(self):
        w,r=self.prepare(observer='Kai')
        self.assertEqual(r.payload['original_source'],'')
        self.assertEqual(r.payload['choices'],[])

    def test_stale_source_support_and_budget(self):
        w,r=self.prepare()
        with self.assertRaisesRegex(ValueError,'budget'):r.messages(w,max_chars=1000)
        w.core.withdraw(r.claim_ids[0])
        with self.assertRaisesRegex(ValueError,'support changed'):r.messages(w)
        w,r=self.prepare();w.put_source('scene',SOURCE+'\nNoor said, "Okay."')
        with self.assertRaisesRegex(ValueError,'source changed'):r.messages(w)

    def test_conditional_speech_not_preference(self):
        _,r=self.prepare('If Mira said, "As reviewer in team, I prefer safety over speed."')
        self.assertEqual(r.payload['role_preferences'],{})
