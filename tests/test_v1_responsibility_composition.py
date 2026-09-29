import unittest

from hcl.cognition.responsibility_composition import ResponsibilityCompositionWorkspace

STAMP='2026-01-08T00:00:00Z'
INDIVIDUAL='For this analysis, responsibility requires causal contribution and control.'
COLLECTIVE='For this analysis, collective responsibility requires each participant to satisfy the individual rule.'


def episode(actor,*,causal=True,control=True,alternative=True):
    lines=[f'{actor}: I opened the gate.','Narrator: The animals escaped.']
    if causal:lines.append(f'Narrator: {actor} opening the gate caused the animals to escape.')
    if control:lines.append(f'Narrator: At the time {actor} could have stopped the opening.')
    if alternative:lines.append(f'{actor}: At the time I could have closed the gate instead of opening the gate.')
    return '\n'.join(lines)


class ResponsibilityCompositionTests(unittest.TestCase):
    def workspace(self):
        w=ResponsibilityCompositionWorkspace()
        for actor in ('Alice','Bob'):
            w.put_episode(actor,actor.lower(),episode(actor),recorded_at=STAMP,permitted_observers=('Analyst',))
        w.put_joint_report('joint','Narrator: Alice and Bob jointly opened the gate.',recorded_at=STAMP,permitted_observers=('Analyst',))
        return w

    def prepare(self,w,question=INDIVIDUAL+' '+COLLECTIVE,**kw):
        return w.prepare(question,actors=('Alice','Bob'),observer='Analyst',**kw)

    def test_ordinary_two_actor_conditional_composition_and_actual_input(self):
        w=self.workspace();result=self.prepare(w);p=result.payload
        self.assertEqual([r['status'] for r in p['individuals']],['SOURCE_FACTORS_CHECKED']*2)
        self.assertEqual([r['checked']['premise_assessments'][0]['result'] for r in p['individuals']],['CONDITIONALLY_SUPPORTED_ON_SOURCE_CLAIMS']*2)
        self.assertEqual(p['collective']['status'],'CONDITIONALLY_SUPPORTED_ON_REPORTED_JOINT_ACTION_AND_INDIVIDUAL_CLAIMS')
        self.assertEqual(p['collective']['group_mind'],'NOT_INFERRED')
        self.assertEqual(p['outcome_alignment'],'SAME_SOURCE_WORDING_NOT_INDEPENDENT_CORROBORATION')
        self.assertEqual(p['individuals'][0]['alternatives'][0]['status'],'SOURCE_REPORTED_OPTION_NOT_VERIFIED_FEASIBILITY')
        self.assertIn('CONDITIONALLY_SUPPORTED',result.messages(w)[1]['content'])
        self.assertEqual(p['verdict'],'NO_MORAL_OR_LEGAL_TRUTH')

    def test_outcome_and_causation_do_not_infer_intention_or_knowledge(self):
        p=self.prepare(self.workspace()).payload
        for row in p['individuals']:
            factors={f['factor']:f['state'] for f in row['checked']['factors']}
            self.assertEqual(factors['STATED_INTENTION'],'UNKNOWN')
            self.assertEqual(factors['KNOWLEDGE'],'UNKNOWN')
            self.assertEqual(factors['CAUSAL_CONTRIBUTION'],'SUPPORTED_CLAIM')

    def test_control_change_only_changes_relevant_requirement(self):
        w=self.workspace()
        w.put_episode('Bob','bob',episode('Bob',control=False),recorded_at='2026-01-09T00:00:00Z',permitted_observers=('Analyst',))
        p=self.prepare(w).payload;alice,bob=p['individuals']
        self.assertEqual(alice['checked']['premise_assessments'][0]['result'],'CONDITIONALLY_SUPPORTED_ON_SOURCE_CLAIMS')
        self.assertEqual(bob['checked']['premise_assessments'][0]['result'],'UNRESOLVED')
        factors={f['factor']:f['state'] for f in bob['checked']['factors']}
        self.assertEqual(factors['CAUSAL_CONTRIBUTION'],'SUPPORTED_CLAIM')
        self.assertEqual(factors['CONTROL'],'UNKNOWN')
        self.assertEqual(p['collective']['status'],'UNRESOLVED_INDIVIDUAL_FACTORS')

    def test_later_learning_does_not_backfill_action_time_knowledge(self):
        w=ResponsibilityCompositionWorkspace()
        source='\n'.join(('Alice: I opened the gate.','Narrator: The animals escaped.',
            'Alice: I learned the gate was weak afterward.','Narrator: At the time Alice could have stopped the opening.'))
        w.put_episode('Alice','alice',source,recorded_at=STAMP,permitted_observers=('Analyst',))
        r=w.prepare('For this analysis, responsibility requires knowledge and control. Was Alice responsible?',
            actors=('Alice',),observer='Analyst')
        row=r.payload['individuals'][0]
        self.assertEqual(next(f['state'] for f in row['checked']['factors'] if f['factor']=='KNOWLEDGE'),'UNKNOWN')
        self.assertEqual(next(f['state'] for f in row['checked']['factors'] if f['factor']=='CONTROL'),'SUPPORTED_CLAIM')
        self.assertEqual(row['checked']['premise_assessments'][0]['result'],'UNRESOLVED')

    def test_explicit_at_time_knowledge_changes_knowledge_only(self):
        w=ResponsibilityCompositionWorkspace()
        source='\n'.join(('Alice: I opened the gate.','Narrator: The animals escaped.',
            'Alice: At the time I knew the gate was weak.','Narrator: At the time Alice could have stopped the opening.'))
        w.put_episode('Alice','alice',source,recorded_at=STAMP,permitted_observers=('Analyst',))
        r=w.prepare('For this analysis, responsibility requires knowledge and control. Was Alice responsible?',
            actors=('Alice',),observer='Analyst')
        row=r.payload['individuals'][0]
        states={f['factor']:f['state'] for f in row['checked']['factors']}
        self.assertEqual(states['KNOWLEDGE'],'SUPPORTED_CLAIM')
        self.assertEqual(states['CONTROL'],'SUPPORTED_CLAIM')
        self.assertEqual(states['STATED_INTENTION'],'UNKNOWN')

    def test_no_adopted_individual_or_collective_rule_does_not_guess_blame(self):
        w=self.workspace();p=self.prepare(w,'Were Alice and Bob responsible?').payload
        self.assertTrue(all(r['status']=='NO_ADOPTED_INDIVIDUAL_RULE' and r['checked'] is None for r in p['individuals']))
        self.assertEqual(p['collective']['status'],'NO_ADOPTED_COLLECTIVE_RULE')
        self.assertEqual([c['origin'] for c in p['premise_candidates']],['ANALYST_PROPOSED_UNADOPTED'])

    def test_joint_report_or_collective_rule_missing_preserves_individual_results(self):
        w=self.workspace();p=self.prepare(w,INDIVIDUAL).payload
        self.assertEqual(p['collective']['status'],'NO_ADOPTED_COLLECTIVE_RULE')
        self.assertEqual(p['individuals'][0]['checked']['premise_assessments'][0]['result'],'CONDITIONALLY_SUPPORTED_ON_SOURCE_CLAIMS')
        w.put_joint_report('joint','Narrator: Alice and Bob jointly closed the gate.',recorded_at='2026-01-09T00:00:00Z',permitted_observers=('Analyst',))
        p=self.prepare(w).payload
        self.assertEqual(p['collective']['status'],'JOINT_ACTION_DOES_NOT_MATCH_INDIVIDUAL_ACTIONS')

    def test_multiple_individual_rules_cannot_be_mixed_into_one_collective_rule(self):
        w=self.workspace()
        p=self.prepare(w,INDIVIDUAL+' For this analysis, responsibility requires knowledge. '+COLLECTIVE).payload
        self.assertEqual(len(p['premise_candidates']),2)
        self.assertEqual(p['collective']['status'],'COLLECTIVE_RULE_REQUIRES_ONE_SELECTED_INDIVIDUAL_RULE')

    def test_alternative_must_link_focal_action_and_never_proves_feasibility(self):
        w=self.workspace()
        altered=episode('Alice').replace('instead of opening the gate','instead of closing the door')
        w.put_episode('Alice','alice',altered,recorded_at='2026-01-09T00:00:00Z',permitted_observers=('Analyst',))
        p=self.prepare(w).payload
        self.assertEqual(p['individuals'][0]['alternatives'][0]['status'],'UNRESOLVED_FOCAL_ACTION_LINK')
        self.assertEqual(p['individuals'][0]['checked']['premise_assessments'][0]['result'],'CONDITIONALLY_SUPPORTED_ON_SOURCE_CLAIMS')

    def test_hidden_actor_or_joint_source_blocks_only_relevant_composition(self):
        w=self.workspace()
        w.put_episode('Bob','bob',episode('Bob'),recorded_at='2026-01-09T00:00:00Z',permitted_observers=())
        p=self.prepare(w).payload
        self.assertEqual(p['individuals'][0]['status'],'SOURCE_FACTORS_CHECKED')
        self.assertEqual(p['individuals'][1]['status'],'SOURCE_VIEW_INSUFFICIENT')
        self.assertEqual(p['collective']['status'],'INDIVIDUAL_FACTOR_VIEW_INSUFFICIENT')
        self.assertNotIn('Bob opening the gate',str(p))

    def test_hidden_joint_report_does_not_hide_individual_factor_assessments(self):
        w=self.workspace()
        w.put_joint_report('joint','Narrator: Alice and Bob jointly opened the gate.',
            recorded_at='2026-01-09T00:00:00Z',permitted_observers=())
        p=self.prepare(w).payload
        self.assertEqual(p['collective']['status'],'JOINT_PARTICIPATION_NOT_ESTABLISHED')
        self.assertIsNone(p['collective']['joint_report'])
        self.assertTrue(all(r['status']=='SOURCE_FACTORS_CHECKED' for r in p['individuals']))

    def test_source_revision_and_access_change_invalidate_final_input(self):
        w=self.workspace();prior=self.prepare(w)
        w.put_episode('Alice','alice',episode('Alice',control=False),recorded_at='2026-01-09T00:00:00Z',permitted_observers=('Analyst',))
        with self.assertRaisesRegex(ValueError,'changed'):prior.messages(w)
        current=self.prepare(w)
        w.put_joint_report('joint','Narrator: Alice and Bob jointly opened the gate.',recorded_at='2026-01-10T00:00:00Z',permitted_observers=())
        with self.assertRaisesRegex(ValueError,'access changed'):current.messages(w)

    def test_character_or_institution_rule_is_not_caller_adoption(self):
        w=self.workspace()
        w.premises.put_source('rules','Institution team policy: responsibility requires knowledge.',
            recorded_at=STAMP,permitted_observers=('Analyst',))
        p=self.prepare(w,'Was Alice responsible?').payload
        self.assertTrue(all(r['checked'] is None for r in p['individuals']))
        self.assertIn('INSTITUTION_REPORTED',[c['origin'] for c in p['premise_candidates']])


if __name__=='__main__':unittest.main()
