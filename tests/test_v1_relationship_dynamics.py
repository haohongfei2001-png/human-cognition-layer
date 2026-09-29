import unittest
from hcl.cognition.relationship_dynamics import RelationshipDynamicsWorkspace

SOURCE='\n'.join((
    'Noor said, "I failed to deliver the report in team."',
    'Noor said, "For the attempt to deliver the report in team, at the time I did not know the requirements."',
    'Noor said, "For the attempt to deliver the report in team, at the time I could not prevent the failure."',
    'Noor said, "For the attempt to deliver the report in team, at the time I did not intend to fail to deliver the report."',
    'Mira said, "In team, I distrust Noor\'s reliability because Noor failed to deliver the report."',
    'Noor said, "In team, I see myself as careful."',
    'Narrator: In team, Noor serves as reviewer.',
    'Narrator: In team, a reviewer is required to deliver the report.',
    'Narrator: In team, Noor did not deliver the report.',
    "Narrator: In team, Noor's failure to deliver the report was the reviewer episode.",
    'Noor said, "As reviewer in team, I prefer safety over speed."'))
QUERY="Explain how Mira's view of Noor relates to the reviewer role and preferences in team after the failure to deliver the report."
CHANGED=SOURCE.replace('did not know','knew').replace('could not prevent','could prevent').replace('did not intend','intended')


class RelationshipDynamicsTests(unittest.TestCase):
    def prepare(self,source=SOURCE,observer=None):
        w=RelationshipDynamicsWorkspace();w.put_source('team',source)
        return w,w.prepare_dynamics(QUERY,source_id='team',observer=observer)

    def test_positive_same_factor_change_updates_two_interpretations(self):
        w,old=self.prepare()
        self.assertEqual(old.payload['role_evaluation']['conditional_alternatives'],['INFORMATION_GAP','CONTROL_CONSTRAINT'])
        w.revise_source('team',CHANGED,kind='ANALYST_SOURCE_CORRECTION')
        new=w.prepare_dynamics(QUERY,source_id='team')
        self.assertEqual(new.payload['role_evaluation']['conditional_alternatives'],['INFORMED_CONTROLLABLE_STATED_CHOICE'])
        self.assertEqual(new.payload['relationship_interpretation']['conditional_alternatives'],['INFORMED_CONTROLLABLE_STATED_CHOICE'])
        comparison=new.payload['source_revision_comparison']
        self.assertEqual(set(comparison['changed_channels']),{'relationship_alternatives','role_alternatives'})
        self.assertEqual(new.payload['relationship_interpretation']['reported_regard'],'DISTRUST')
        self.assertEqual(new.payload['role_evaluation']['reported_self_description'],['careful'])
        self.assertIn('PRIOR_ANALYST_SNAPSHOT',new.messages(w)[1]['content'])

    def test_unrelated_domain_stays_cached(self):
        w,old=self.prepare();w.put_source('club',SOURCE.replace('team','club'))
        query=QUERY.replace('team','club');other=w.prepare_dynamics(query,source_id='club')
        w.revise_source('team',CHANGED,kind='ANALYST_SOURCE_CORRECTION')
        w.prepare_dynamics(QUERY,source_id='team')
        self.assertIs(other,w.prepare_dynamics(query,source_id='club'))
        self.assertEqual(w.dynamics_executions[('club',query,None)],1)

    def test_missing_episode_link_not_guessed(self):
        w,r=self.prepare('\n'.join(x for x in SOURCE.splitlines() if 'was the reviewer episode' not in x))
        self.assertEqual(r.payload['role_evaluation']['status'],'UNRESOLVED_EPISODE_OR_FACTORS')
        self.assertEqual(r.payload['role_evaluation']['conditional_alternatives'],[])
        self.assertEqual(r.payload['relationship_interpretation']['status'],'SOURCE_CITED_FAILURE_CONDITIONALLY_EXPLAINED')

    def test_another_episode_role_or_actor_cannot_bind(self):
        _,r=self.prepare(SOURCE.replace('was the reviewer episode','was the editor episode'))
        self.assertEqual(r.payload['role_evaluation']['conditional_alternatives'],[])

    def test_no_reason_match_no_relationship_cause(self):
        _,r=self.prepare(SOURCE.replace('because Noor failed to deliver the report','because Noor missed a call'))
        self.assertEqual(r.payload['relationship_interpretation']['conditional_alternatives'],[])
        self.assertTrue(r.payload['role_evaluation']['conditional_alternatives'])

    def test_new_disclosure_is_not_private_character_change(self):
        w,_=self.prepare();text=SOURCE+'\nNoor said, "As reviewer in team, I now prefer speed over safety instead of safety over speed."'
        w.revise_source('team',text,kind='NEW_SOURCE_DISCLOSURE')
        r=w.prepare_dynamics(QUERY,source_id='team')
        self.assertEqual(r.payload['source_revision_comparison']['kind'],'NEW_SOURCE_DISCLOSURE')
        self.assertIn('reported_preference_pairs',r.payload['source_revision_comparison']['changed_channels'])
        self.assertEqual(r.payload['source_revision_comparison']['character_change'],'NOT_INFERRED')
        self.assertEqual(r.payload['value_change_explanation']['failure_binding'],'NOT_ESTABLISHED')

    def test_disclosure_cannot_rewrite_source(self):
        w,_=self.prepare()
        with self.assertRaisesRegex(ValueError,'append'):w.revise_source('team',CHANGED,kind='NEW_SOURCE_DISCLOSURE')

    def test_access_revocation_never_resurrects_prior_view(self):
        w=RelationshipDynamicsWorkspace();w.put_source('team',SOURCE,permitted_observers=('Mira',))
        w.prepare_dynamics(QUERY,source_id='team',observer='Mira')
        w.revise_source('team',CHANGED,kind='ANALYST_SOURCE_CORRECTION',permitted_observers=())
        r=w.prepare_dynamics(QUERY,source_id='team',observer='Mira')
        self.assertNotIn('source_revision_comparison',r.payload)
        self.assertNotIn('Noor said',r.messages(w)[1]['content'])

    def test_unknown_factors_remain_unknown_not_trait(self):
        _,r=self.prepare('\n'.join(x for x in SOURCE.splitlines() if 'For the attempt' not in x))
        self.assertEqual(r.payload['role_evaluation']['conditional_alternatives'],[])
        self.assertFalse(r.payload['role_evaluation']['identity_rewritten'])

    def test_stale_support_version_and_budget(self):
        w,r=self.prepare()
        with self.assertRaisesRegex(ValueError,'budget'):r.messages(w,max_chars=1000)
        w.core.withdraw(r.claim_ids[-1])
        with self.assertRaisesRegex(ValueError,'support changed'):r.messages(w)
        w,r=self.prepare();w.revise_source('team',CHANGED,kind='ANALYST_SOURCE_CORRECTION')
        with self.assertRaisesRegex(ValueError,'source changed'):r.messages(w)

    def test_conflicting_factors_remain_competing_and_unresolved(self):
        _,r=self.prepare(SOURCE+'\nNoor said, "For the attempt to deliver the report in team, at the time I knew the requirements."')
        information=next(h for h in r.payload['failure']['explanations'] if h['hypothesis']=='INFORMATION_GAP')
        self.assertEqual(information['status'],'CONFLICTING_PREMISES')
        self.assertNotIn('INFORMATION_GAP',r.payload['role_evaluation']['conditional_alternatives'])
        self.assertIn('CONTROL_CONSTRAINT',r.payload['role_evaluation']['conditional_alternatives'])

    def test_third_party_factor_claim_not_actor_intention(self):
        _,r=self.prepare(CHANGED.replace('Noor said, "For the attempt','Kai said, "For the attempt'))
        self.assertEqual(r.payload['role_evaluation']['conditional_alternatives'],[])
