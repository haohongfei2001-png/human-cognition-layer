"""Explicit v3 joins: actual packets to one M09 computation and M11 answers."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json
import unittest
from unittest.mock import patch

from hcl import HCL, ExecutionIssue
from hcl.kernel.types import HCLFailure, Issue, thaw
from hcl.memory import codec
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.runtime.answer import AnswerAssembler
from hcl.runtime.context import ContextCompiler
from hcl.semantics.literature_compiler import LiteratureCompiler
from hcl.semantics.cross_packet_characters import SCHEMA, paths, collection
from tests import test_unified_narrative_characters as old_fixtures


def bind(value, refs):
    if isinstance(value, dict):
        for key, item in value.items():
            if key == 'segment_ids' and isinstance(item,list): value[key] = list(refs)
            else: bind(item, refs)
    elif isinstance(value, list):
        for item in value: bind(item, refs)


def split_model(model, chunks, *, late=False):
    """Test proposal builder, deliberately independent of the witness port."""
    original = deepcopy(model)
    if late: original['observations'][-1]['action'] = 'wait'
    episode_time = {e['id']: e['at'] for e in original['affect']['episodes']}
    static = deepcopy(original)
    for path, _ in paths(): collection(static, path).clear()
    packets = []
    # Chunks can group the same exact source segments differently. Each source
    # paragraph contributes its own evidence; only packet locators change.
    owners = {segment.start: chunk.ordinal for chunk in chunks for segment in chunk.segments}
    paragraphs = sorted(owners)
    frame = dict(fragment=owners[paragraphs[0]], id='story-frame')
    location = {}
    for chapter, start in enumerate(paragraphs):
        for at in ((0, 1, 2), (3,), (4, 5))[chapter]: location[at] = owners[start]
    for chunk in chunks:
        packet = dict(schema=SCHEMA, assumptions=[], active_assumptions=[], frames=[], events=[],
            mentions=[], orders=[], queries=[], motifs=[], variants=[], comparisons=[], analogies=[],
            unmodeled_segments=[], character_models=[], character_contributions=[])
        for chapter, segment in enumerate(sorted((s for c in chunks for s in c.segments), key=lambda s:s.start)):
            if segment not in chunk.segments: continue
            times = ((0, 1, 2), (3,), (4, 5))[chapter]
            refs = [segment.segment_id]
            if chapter == 0:
                bind(static, refs)
                packet['frames'].append(dict(id='story-frame', parent=None, kind='INTERPRETATION',
                    narrator='explicit analyst', focalizer='b', segment_ids=refs))
                packet['character_models'].append(dict(id='b-history', source_id=static['mental']['source_id'],
                    actor='b', frame=frame, assumptions=[], segment_ids=refs, model=static))
            additions = {}
            for path, _ in paths():
                rows = collection(original, path)
                def time(row):
                    return episode_time[row['episode_id']] if path[0] in ('observations','forecasts') else row.get('at', 1)
                selected = [deepcopy(r) for r in rows if time(r) in times]
                if len(path) == 1: additions[path[0]] = selected
                else: additions.setdefault(path[0], {})[path[1]] = selected
            bind(additions, refs)
            bindings=[]
            for episode in additions['affect']['episodes']:
                packet['events'].append(dict(id=episode['id'], frame=frame, description='Source character event',
                    assumptions=[], segment_ids=refs))
                bindings.append(dict(episode_id=episode['id'],event=dict(fragment=chunk.ordinal,id=episode['id']),at=episode['at']))
            packet['character_contributions'].append(dict(id='chapter-'+str(chapter),
                source_id=static['mental']['source_id'],actor='b',frame=frame,assumptions=[],segment_ids=refs,
                declaration=dict(fragment=frame['fragment'],id='b-history'),bindings=bindings,additions=additions))
        packets.append(packet)
    return packets


class CrossPacketCharacterTests(unittest.TestCase):
    def setUp(self):
        self.fixture = old_fixtures.NarrativeCharacterTests(); self.fixture.setUp()
        self.store, self.owner = self.fixture.store, self.fixture.owner
        paragraphs = [
            'Early behaviour: B waits at closure 1 and crosses at opening 2; A and B are source-local actors; safety, duty and coping are competing hypotheses ',
            'Late explanation: at event time 3 B receives and understands a closure report; narrating this later does not give B this knowledge at event time 1 ',
            'Counterevidence: at event time 4 an open passage is observed but B waits; at time 5 the next choice is hypothetical ',
        ]
        self.text='\n'.join(p + 'declared context ' * 200 for p in paragraphs)
        self.model=self.fixture.f.candidate()['models'][0]
        handle=self.store.put_source('scene',self.owner,'story',self.text)
        self.request=replace(self.fixture.request,source_handles=(handle,),question='Compare the conditional character arc.',
            budget=replace(self.fixture.request.budget,max_request_bytes=10000,max_context_tokens=10000,max_feedback=0))
        self.snapshot=self.store.snapshot('scene',self.owner,(handle,))
        self.chunks=ContextCompiler().chunks(self.snapshot,self.request.question,'literature_compile',self.request.budget,OfflineModelPort().describe())
        self.assertEqual(len(self.chunks),3)
        # Delayed explanation is a message received only at its explicit time.
        self.model['mental']['events'][2].update(kind='message',seen_by=[],received_by=['b'],understood_by=['b'],trusted_by=['b'])

    def tearDown(self): self.fixture.tearDown()

    def candidates(self,late=False,chunks=None): return split_model(self.model,chunks or self.chunks,late=late)

    def compile(self,candidates, chunks=None):
        return LiteratureCompiler().compose(self.snapshot,tuple(zip(chunks or self.chunks,map(json.dumps,candidates))),self.request.budget)

    def run_candidates(self,candidates=None,request=None,stream=False):
        request=request or self.request
        port=OfflineModelPort(responses=tuple(map(json.dumps,candidates or self.candidates())))
        client=HCL(self.store,principal=self.owner,gateway=ModelGateway(self.store,port))
        if stream:
            async def collect(): return [e async for e in client.stream(request)]
            result=asyncio.run(collect())[-1].result
        else: result=client.run_sync(request)
        self.assertEqual(result.status,'PARTIAL',result.diagnostics)
        proof=next(r for r in self.store.inferences('scene',self.owner) if r.result_id in result.execution_receipt['result_ids'] and r.kind=='CONDITIONAL_NARRATIVE_MODEL')
        return result,proof,port

    def test_three_actual_packets_change_one_model_and_stream_answer(self):
        before,proof,port=self.run_candidates(stream=True)
        self.assertEqual(port.attempts,3)
        read=''.join(s['text'] for wire in port.contexts for s in json.loads(wire)['segments'] if s['kind']=='SOURCE')
        self.assertEqual(read,self.text)
        self.assertTrue(all(json.loads(wire)['candidate_schema']=='hcl-literature-fragment-1' for wire in port.contexts))
        self.assertEqual(len(proof.values['character_arcs']),1)
        self.assertEqual(len(proof.values['character_arcs'][0]['composition']['contributions']),3)
        late,changed,_=self.run_candidates(self.candidates(late=True),replace(self.request,request_id='counterevidence'))
        left=proof.values['character_arcs'][0]['values']['models'][0]
        right=changed.values['character_arcs'][0]['values']['models'][0]
        self.assertEqual(left['prediction_matrix'],right['prediction_matrix'])
        self.assertNotEqual(left['longitudinal']['pareto_explored'],right['longitudinal']['pareto_explored'])
        self.assertTrue(any(t['change_points'] for t in right['preferred_forecasts']))
        self.assertNotEqual(before.answer,late.answer)
        self.assertIn('Explicit cross-packet character reading',late.answer)
        self.assertIn('EXPLICIT_CHARACTER_JOINS_ONLY',late.answer)
        self.assertNotIn('CROSS_PACKET_CHARACTER_COMPOSITION_UNCOMPUTED',late.answer)
        self.assertEqual(left['identity_narratives'],right['identity_narratives'])
        self.assertTrue(any(f.field=='character_arcs' for c in late.claim_records for f in c.used_result_fields))
        again,_,replay=self.run_candidates()
        self.assertEqual(replay.attempts,0);self.assertEqual(before.answer,again.answer)

    def test_packet_grouping_preserves_compiled_m09_and_computation(self):
        chunks=ContextCompiler().chunks(self.snapshot,self.request.question,'literature_compile',replace(self.request.budget,max_request_bytes=16000,max_context_tokens=16000),OfflineModelPort().describe())
        self.assertLess(len(chunks),3)
        three=self.compile(self.candidates())['character_arcs'][0]
        grouped=self.compile(self.candidates(chunks=chunks),chunks)['character_arcs'][0]
        self.assertEqual(three['program'],grouped['program'])
        self.assertEqual(three['id'],grouped['id'])
        from hcl.operators.relationship_model import RelationshipModelOperator
        a=RelationshipModelOperator().run(self.snapshot,Issue('same','relationship.evaluate'),self.request.budget,three['program'])
        b=RelationshipModelOperator().run(self.snapshot,Issue('same','relationship.evaluate'),self.request.budget,grouped['program'])
        self.assertEqual(codec.dumps(a),codec.dumps(b))

    def test_missing_link_source_actor_frame_time_and_inactive_assumption_rejected(self):
        changes=(lambda r:r['declaration'].update(id='unlinked'),lambda r:r.update(source_id='other-source'),
            lambda r:r.update(actor='a'),lambda r:r['frame'].update(id='other-frame'),
            lambda r:r['bindings'][0].update(at=0),lambda r:r.update(assumptions=['inactive']),
            lambda r:r['bindings'].pop())
        for change in changes:
            candidates=deepcopy(self.candidates());change(candidates[2]['character_contributions'][0])
            with self.subTest(change=change),self.assertRaises(HCLFailure):self.compile(candidates)
        candidates=self.candidates();candidates[1]['character_contributions'][0]['additions']['mental']['events'][0]['assumptions']=['inactive']
        with self.assertRaises(HCLFailure):self.compile(candidates)
        with self.assertRaises(HCLFailure):self.compile(self.candidates()[:-1],self.chunks[:-1])

    def test_late_report_does_not_backfill_past_knowledge(self):
        _,proof,_=self.run_candidates()
        candidate=self.candidates()
        event=candidate[1]['character_contributions'][0]['additions']['mental']['events'][0]
        event.update(received_by=['a'],understood_by=['a'],trusted_by=['a'])
        _,changed,_=self.run_candidates(candidate,replace(self.request,request_id='undelivered'))
        left=proof.values['character_arcs'][0]['values']['models'][0]
        right=changed.values['character_arcs'][0]['values']['models'][0]
        for mechanism in left['prediction_matrix']:
            self.assertEqual([r['values'] for r in left['prediction_matrix'][mechanism][:2]],
                [r['values'] for r in right['prediction_matrix'][mechanism][:2]])
        self.assertNotEqual({m: [r['values'] for r in rows] for m,rows in left['prediction_matrix'].items()},
            {m: [r['values'] for r in rows] for m,rows in right['prediction_matrix'].items()})

    def test_cross_packet_duplicate_reports_have_one_evidence_factor(self):
        _,proof,_=self.run_candidates()
        candidates=self.candidates();first=candidates[0]['character_contributions'][0];last=candidates[2]['character_contributions'][0]
        repeat=deepcopy(first['additions']['observations'][0]);repeat.update(id='retold',context_id='retelling',segment_ids=last['segment_ids'])
        last['additions']['observations'].append(repeat);last['bindings'].append(deepcopy(first['bindings'][0]))
        _,changed,_=self.run_candidates(candidates,replace(self.request,request_id='retold'))
        a=proof.values['character_arcs'][0]['values']['models'][0]['longitudinal']
        b=changed.values['character_arcs'][0]['values']['models'][0]['longitudinal']
        self.assertEqual(a['evidence_factor_ids'],b['evidence_factor_ids'])
        self.assertEqual({codec.canonical(thaw(t['profile'])) for t in a['trajectories']},{codec.canonical(thaw(t['profile'])) for t in b['trajectories']})

    def test_nested_certificate_binding_source_result_and_allowance_forgery_rejected(self):
        _,proof,_=self.run_candidates()
        changes=(lambda v:v['character_arcs'][0]['composition']['contributions'].pop(),
            lambda v:v['character_arcs'][0]['composition'].update(model_id='other'),
            lambda v:v['character_arcs'][0]['bindings'][0].update(at=90),
            lambda v:v['character_arcs'][0]['values'].update(execution_allowance=1),
            lambda v:v['character_arcs'][0]['values']['models'][0]['longitudinal'].update(pareto_explored=[]),
            lambda v:v['character_arcs'][0].update(source_versions={}),
            lambda v:v['character_arcs'][0]['resource_usage'].update(local_evaluations=0))
        for change in changes:
            value=thaw(proof.values);change(value)
            with self.subTest(change=change),self.assertRaises(HCLFailure):AnswerAssembler()._claim(replace(proof,values=value))

    def test_budget_frontier_and_missing_packet_never_global_completion(self):
        result,proof,_=self.run_candidates(request=replace(self.request,budget=replace(self.request.budget,max_local_evaluations=8)))
        self.assertLessEqual(result.usage['local_evaluations'],8)
        self.assertIn('NOT_ESTABLISHED',result.answer);self.assertIn('FRONTIER',result.answer)
        self.assertEqual(proof.values['coverage']['semantic_completeness'],'NOT_ESTABLISHED')
        req=replace(self.request,request_id='missing',budget=replace(self.request.budget,max_mock_calls=2))
        port=OfflineModelPort(responses=tuple(map(json.dumps,self.candidates())))
        result=HCL(self.store,principal=self.owner,gateway=ModelGateway(self.store,port)).run_sync(req)
        self.assertNotEqual(result.status,'COMPLETED');self.assertFalse(result.claim_records)
        self.assertEqual(port.attempts,2)

    def test_unrelated_packet_leaves_joint_result_unchanged_and_unlinked_evidence_drops(self):
        # The same supplied original has a third packet. Making it unmodeled
        # removes its contribution, rather than inferring identity from names.
        candidates=self.candidates(late=True)
        full=self.compile(candidates)['character_arcs'][0]
        disconnected=deepcopy(candidates)
        disconnected[2]['character_contributions']=[]
        disconnected[2]['events']=[]
        disconnected[2]['unmodeled_segments']=[s.segment_id for s in self.chunks[2].segments]
        partial=self.compile(disconnected)['character_arcs'][0]
        self.assertEqual(len(full['program']['models'][0]['observations']),4)
        self.assertEqual(len(partial['program']['models'][0]['observations']),3)
        before,isolated,_=self.run_candidates(disconnected)
        after,joint,_=self.run_candidates(candidates,replace(self.request,request_id='linked'))
        def selected_turns(proof):
            actual=proof.values['character_arcs'][0]['values']['models'][0]['longitudinal']
            return [t['change_points'] for t in actual['trajectories'] if t['trajectory_id'] in actual['pareto_explored']]
        self.assertFalse(any(selected_turns(isolated)))
        self.assertTrue(any(selected_turns(joint)))
        self.assertNotEqual(before.answer,after.answer)
        altered=deepcopy(disconnected)
        refs=[s.segment_id for s in self.chunks[2].segments]
        altered[2]['motifs']=[dict(id='unrelated',literal='Counterevidence',segment_ids=refs)]
        again=self.compile(altered)['character_arcs'][0]
        self.assertEqual(partial,again)
        self.assertIn('NARRATIVE_UNMODELED_SOURCE',before.answer)

    def test_same_label_different_declared_people_never_merge(self):
        candidates=self.candidates()
        declaration=candidates[0]['character_models'][0]
        # A second explicit source-local actor carries the same display label.
        other=deepcopy(declaration);other['id']='other-b';other['model']['mental']['id']='other-b-model'
        other['model']['mental']['agents'][1]['id']='different-b'
        other['actor']='different-b'
        def rename(value):
            if isinstance(value,dict):
                for k,v in value.items():
                    if k in ('actor','speaker','agent') and v=='b':value[k]='different-b'
                    elif k in ('seen_by','received_by','understood_by','trusted_by','observed_by'):
                        value[k]=['different-b' if x=='b' else x for x in v]
                    else:rename(v)
            elif isinstance(value,list):
                for i,v in enumerate(value):
                    rename(v)
        rename(other)
        candidates[0]['character_models'].append(other)
        for packet in candidates:
            new=deepcopy(packet['character_contributions'][0]);new['id']+='-other'
            new['declaration']['id']='other-b';rename(new)
            # Each person's episode has its own explicit event, even at equal time.
            for b in new['bindings']:b['event']['id']+='-other'
            events=deepcopy(packet['events'])
            for e in events:e['id']+='-other'
            packet['events'].extend(events);packet['character_contributions'].append(new)
        arcs=self.compile(candidates)['character_arcs']
        self.assertEqual(len(arcs),2)
        self.assertNotEqual(arcs[0]['id'],arcs[1]['id'])
        self.assertEqual({a['actor'] for a in arcs},{'b','different-b'})

    def test_indirect_cross_packet_clock_conflict_and_over_cap_rejected(self):
        candidates=self.candidates();refs=candidates[2]['character_contributions'][0]['segment_ids']
        candidates[2]['events'].append(dict(id='middle',frame=dict(fragment=0,id='story-frame'),description='middle',assumptions=[],segment_ids=refs))
        candidates[2]['orders']=[dict(id=str(i),left=l,right=r,strict=True,assumptions=[],segment_ids=refs)
            for i,(l,r) in enumerate(((dict(fragment=2,id='episode-4'),dict(fragment=2,id='middle')),
                                    (dict(fragment=2,id='middle'),dict(fragment=0,id='episode-1'))))]
        with self.assertRaises(HCLFailure):self.compile(candidates)
        candidates=self.candidates();obs=candidates[2]['character_contributions'][0]['additions']['observations']
        for n in range(13):obs.append(dict(obs[0],id='duplicate-'+str(n)))
        with self.assertRaises(HCLFailure):self.compile(candidates)

    def test_current_v3_interruptions_recover_without_resending_old_packets(self):
        from hcl.memory.store import StateStore
        from hcl.runtime.recovery import RecoveryManager
        class Crash(BaseException):pass
        for seam in ('return_persisted','execution_computed','execution_effects_committed'):
            request=replace(self.request,request_id=seam,issue=ExecutionIssue('root',goals=(Issue(seam,'literature.analyze'),)))
            owner_id,path=self.store.owner_id,self.store.path
            count=0
            def stop(stage):
                nonlocal count
                if stage==seam:
                    count+=1
                    if seam!='return_persisted' or count==3:raise Crash()
            with patch.object(self.store,'_checkpoint',stop),self.assertRaises(Crash):self.run_candidates(request=request)
            self.store.close();self.store=StateStore.sqlite(path)
            self.fixture.store=self.fixture.f.store=self.fixture.f.f.store=self.fixture.f.f.fixture.store=self.fixture.f.f.fixture.scene.store=self.store
            RecoveryManager(self.store).resume_execution(request,expected_owner_id=owner_id)
            result,_,port=self.run_candidates(request=request)
            self.assertEqual(port.attempts,0);self.assertEqual(result.usage['mock_calls'],3)
            self.assertIn('Explicit cross-packet character reading',result.answer)

    def test_acl_withdrawal_blocks_cached_joint_delivery(self):
        self.run_candidates()
        self.store.set_readers('scene',self.owner,'story',frozenset({'bob'}))
        port=OfflineModelPort('MUST_NOT_SEND')
        result=HCL(self.store,principal=self.owner,gateway=ModelGateway(self.store,port)).run_sync(self.request)
        self.assertFalse(result.answer or result.claim_records);self.assertEqual(port.attempts,0)
        self.assertEqual(result.status,'DENIED')

    def test_early_return_resume_reads_only_remaining_packets_and_unknown_stays_closed(self):
        from hcl.memory.store import StateStore
        from hcl.runtime.recovery import RecoveryManager
        class Crash(BaseException):pass
        for state,seam in (('early-return','return_persisted'),('unknown','send_started')):
            request=replace(self.request,request_id=state,issue=ExecutionIssue('root',goals=(Issue(state,'literature.analyze'),)))
            owner_id,path=self.store.owner_id,self.store.path
            def stop(stage):
                if stage==seam:raise Crash()
            with patch.object(self.store,'_checkpoint',stop),self.assertRaises(Crash):self.run_candidates(request=request)
            self.store.close();self.store=StateStore.sqlite(path)
            self.fixture.store=self.fixture.f.store=self.fixture.f.f.store=self.fixture.f.f.fixture.store=self.fixture.f.f.fixture.scene.store=self.store
            if state=='unknown':
                with self.assertRaises(HCLFailure):RecoveryManager(self.store).resume_execution(request,expected_owner_id=owner_id)
                port=OfflineModelPort('MUST_NOT_SEND')
                result=HCL(self.store,principal=self.owner,gateway=ModelGateway(self.store,port)).run_sync(request)
                self.assertFalse(result.answer or result.claim_records);self.assertEqual(port.attempts,0)
            else:
                RecoveryManager(self.store).resume_execution(request,expected_owner_id=owner_id)
                result,_,port=self.run_candidates(self.candidates()[1:],request)
                self.assertEqual(port.attempts,2);self.assertEqual(result.usage['mock_calls'],3)

    def test_source_provenance_cannot_be_relabelled_with_rehashed_program(self):
        from hashlib import sha256
        _,proof,_=self.run_candidates()
        value=thaw(proof.values);program=value['inputs']['program']
        contribution=program['fragments'][2]['character_contributions'][0]
        contribution['additions']['observations'][0]['segment_ids']=program['fragments'][0]['character_models'][0]['segment_ids']
        program.pop('candidate_identity');program['candidate_identity']=sha256(codec.dumps(program)).hexdigest()
        with self.assertRaises(HCLFailure):AnswerAssembler()._claim(replace(proof,values=value))

    def test_packet_conditions_are_delivered_and_small_expression_budget_withholds_claim(self):
        candidates=self.candidates()
        for i,packet in enumerate(candidates):
            assumption='alignment-'+str(i)
            packet['assumptions']=packet['active_assumptions']=[assumption]
            packet['character_contributions'][0]['assumptions']=[assumption]
        result,proof,_=self.run_candidates(candidates)
        conditions=proof.values['character_arcs'][0]['binding_assumptions']
        self.assertEqual(len(conditions),3)
        self.assertTrue(set(conditions)<=set(proof.assumption_environments))
        for condition in conditions:self.assertIn(condition,result.answer)
        request=replace(self.request,request_id='small-expression',budget=replace(self.request.budget,max_visible_output_tokens=40))
        port=OfflineModelPort(responses=tuple(map(json.dumps,candidates)))
        limited=HCL(self.store,principal=self.owner,gateway=ModelGateway(self.store,port)).run_sync(request)
        self.assertNotEqual(limited.status,'COMPLETED');self.assertFalse(limited.claim_records)
        self.assertNotIn('Actual candidate trajectory',limited.answer)

    def test_foreign_source_present_in_same_snapshot_cannot_join(self):
        other=self.store.put_source('scene',self.owner,'other','Another work with the same display name '+ 'unrelated source ' * 210)
        snapshot=self.store.snapshot('scene',self.owner,self.request.source_handles+(other,))
        chunks=ContextCompiler().chunks(snapshot,self.request.question,'literature_compile',self.request.budget,OfflineModelPort().describe())
        self.assertEqual(len(chunks),4)
        self.assertEqual([s.source_id for s in chunks[-1].segments],['other'])
        candidates=self.candidates();foreign=deepcopy(candidates[-1]);refs=[s.segment_id for s in chunks[-1].segments]
        bind(foreign,refs)
        row=foreign['character_contributions'][0];row['source_id']='other';row['id']='foreign'
        for binding in row['bindings']:binding['event']['fragment']=3
        candidates.append(foreign)
        with self.assertRaises(HCLFailure):LiteratureCompiler().compose(snapshot,tuple(zip(chunks,map(json.dumps,candidates))),self.request.budget)

    def test_later_packet_cannot_override_initial_knowledge_or_mechanisms(self):
        for field in ('variables','active_assumptions'):
            candidates=self.candidates()
            candidates[1]['character_contributions'][0]['additions']['mental'][field]=[]
            with self.assertRaises(HCLFailure):self.compile(candidates)
        candidates=self.candidates();candidates[1]['character_contributions'][0]['additions']['mechanisms']=[]
        with self.assertRaises(HCLFailure):self.compile(candidates)

    def test_underlying_episode_alias_cannot_add_factor_but_independent_event_can(self):
        candidates=self.candidates();early=candidates[0]['character_contributions'][0];last=candidates[2]['character_contributions'][0]
        episode=deepcopy(early['additions']['affect']['episodes'][0]);episode['id']='alias-episode-1'
        bind(episode,last['segment_ids']);last['additions']['affect']['episodes'].append(episode)
        observation=deepcopy(early['additions']['observations'][0]);observation.update(id='alias-choice',context_id='retelling',episode_id=episode['id'])
        bind(observation,last['segment_ids']);last['additions']['observations'].append(observation)
        event=deepcopy(candidates[0]['events'][0]);event['id']='alias-story-event';bind(event,last['segment_ids']);candidates[2]['events'].append(event)
        last['bindings'].append(dict(episode_id=episode['id'],event=dict(fragment=2,id=event['id']),at=episode['at']))
        with self.assertRaises(HCLFailure) as alias:self.compile(candidates)
        self.assertEqual(alias.exception.diagnostic.field_path,'character_episode_identity_alias')
        conflicting=deepcopy(candidates)
        later=conflicting[2]['character_contributions'][0]
        later['additions']['affect']['episodes'][-1].update(at=5,plan_id='plan-5')
        later['bindings'][-1]['at']=5
        with self.assertRaises(HCLFailure) as clock:self.compile(conflicting)
        self.assertEqual(clock.exception.diagnostic.field_path,'character_episode_time_conflict')
        # A distinct explicitly declared underlying event at the same story time
        # remains independent. Equal action/actor/time do not imply identity.
        episode['episode_id']='genuinely-independent-event'
        _,proof,_=self.run_candidates(candidates)
        actual=proof.values['character_arcs'][0]['values']['models'][0]
        self.assertEqual(len(actual['longitudinal']['evidence_factor_ids']),5)

    def test_conflicting_reports_of_same_explicit_episode_fail_closed(self):
        candidates=self.candidates();first=candidates[0]['character_contributions'][0];last=candidates[2]['character_contributions'][0]
        report=deepcopy(first['additions']['observations'][0]);report.update(id='contradictory-report',action='cross')
        bind(report,last['segment_ids']);last['additions']['observations'].append(report)
        last['bindings'].append(deepcopy(first['bindings'][0]))
        with self.assertRaises(HCLFailure):self.compile(candidates)

    def test_semantic_identifier_named_segment_ids_is_not_treated_as_provenance(self):
        self.model['mental']['variables'][0]['id']='segment_ids'
        for event in self.model['mental']['events']:
            event['effects']['segment_ids']=event['effects'].pop('open')
        def rename_formula(value):
            if isinstance(value,dict):
                if value.get('op')=='atom' and value.get('name')=='open':value['name']='segment_ids'
                for item in value.values():rename_formula(item)
            elif isinstance(value,list):
                for item in value:rename_formula(item)
        rename_formula(self.model)
        candidates=self.candidates()
        program=self.compile(candidates)
        self.assertEqual(program['character_arcs'][0]['program']['models'][0]['mental']['variables'][0]['id'],'segment_ids')
        first=candidates[0]['character_contributions'][0]['additions']['mental']['events'][0]
        last=candidates[2]['character_contributions'][0]
        repeated=deepcopy(first);repeated['segment_ids']=last['segment_ids']
        last['additions']['mental']['events'].append(repeated)
        joined=self.compile(candidates)['character_arcs'][0]['program']['models'][0]
        self.assertEqual(len(joined['mental']['events']),4)
        self.assertIs(joined['mental']['events'][0]['effects']['segment_ids'],False)

    def test_v3_inherits_analogy_and_induction_alongside_real_joint_arc(self):
        from tests import test_unified_s4_concepts as concept
        from tests.test_unified_s4_concept_induction import term
        fixture=concept.ConceptExecutionTests();fixture.setUp()
        try:task=fixture.candidate()
        finally:fixture.tearDown()
        refs=[s.segment_id for s in self.chunks[0].segments]
        bind(task,refs)
        task['inductions']=[dict(id='diagonal',concept_key='same-pair',purpose='Finite declared comparison',
            assumptions=[],active_assumptions=[],positive=[dict(id=x,term=term('pair',term(x),term(x)),assumptions=[],segment_ids=refs) for x in ('a','b')],
            negative=[dict(id='mixed',term=term('pair',term('a'),term('b')),assumptions=[],segment_ids=refs)],unmodeled_segments=[])]
        for stream in (False,True):
            candidates=self.candidates();candidates[0]['analogies']=[dict(id='mapping-and-induction',task=task)]
            result,proof,_=self.run_candidates(candidates,replace(self.request,request_id='mixed-'+str(stream)),stream)
            self.assertEqual(len(proof.values['character_arcs']),1)
            self.assertEqual(len(proof.values['analogies']),1)
            self.assertTrue(proof.values['analogies'][0]['values']['inductions'])
            self.assertIn('TARGET_REFUTED',result.answer)
            self.assertIn('Explicit cross-packet character reading',result.answer)
            self.assertIn('Proposed concept',result.answer)

    def test_v3_with_analogy_only_preserves_existing_run_and_stream_path(self):
        from tests import test_unified_s4_narrative_analogies as analogies
        for stream in (False,True):
            case=analogies.NarrativeAnalogyTests()
            try:
                fixture,candidate=case.fixture()
                candidate.update(schema=SCHEMA,character_models=[],character_contributions=[])
                result,_=fixture.run_candidate(candidate,stream=stream)
                self.assertEqual(result.status,'PARTIAL',result.diagnostics)
                self.assertIn('TARGET_REFUTED',result.answer)
            finally:case.doCleanups()

    def test_rehashed_source_descriptor_integer_aliases_are_rejected(self):
        from hashlib import sha256
        _,proof,_=self.run_candidates()
        for field,value in (('byte_start',False),('byte_end',True),('version',True),('start',False)):
            changed=thaw(proof.values);program=changed['inputs']['program']
            program['fragments'][0]['source_segments'][0][field]=value
            program.pop('candidate_identity');program['candidate_identity']=sha256(codec.dumps(program)).hexdigest()
            with self.subTest(field=field),self.assertRaises(HCLFailure):AnswerAssembler()._claim(replace(proof,values=changed))


    def test_upper_layer_only_packet_keeps_real_evidence_without_fake_mental_events(self):
        for layer in ('observations', 'interaction', 'affect', 'identities'):
            candidates=self.candidates();first=candidates[0]['character_contributions'][0];last=candidates[2]['character_contributions'][0]
            refs=last['segment_ids']
            for path,_ in paths():collection(last['additions'],path).clear()
            candidates[2]['events']=[];last['bindings']=[]
            if layer=='observations':
                report=deepcopy(first['additions']['observations'][0]);report.update(id='late-repeated-report',context_id='late-repeated-context')
                bind(report,refs);last['additions']['observations']=[report]
                last['bindings']=[deepcopy(first['bindings'][0])]
            elif layer=='interaction':
                last['additions']['interaction']['utterances']=[dict(id='late-utterance',at=3,speaker='a',audience=['b'],version='v',literal={'open':False},
                    deliveries=[dict(event_id='change-3',readings=[dict(actor='b',contents=[{'open':False}],versions=['v'],segment_ids=refs)],segment_ids=refs)],segment_ids=refs)]
            elif layer=='affect':
                report=deepcopy(first['additions']['affect']['episodes'][0]);bind(report,refs)
                last['additions']['affect']['episodes']=[report];last['bindings']=[deepcopy(first['bindings'][0])]
            else:
                last['additions']['identities']=[dict(id='later-self-description',at=4,actor='b',speaker='b',kind='SELF_IDENTIFICATION',content='A declared later self-description.',segment_ids=refs)]
            with self.subTest(layer=layer):
                result,proof,_=self.run_candidates(candidates,replace(self.request,request_id='upper-only-'+layer),stream=True)
                arc=proof.values['character_arcs'][0];model=arc['values']['models'][0]
                self.assertEqual(len(model['inputs']['mental']['events']),3)
                self.assertEqual(model['inputs']['mental']['unmodeled_segments'],())
                self.assertFalse(set(refs)&set(arc['composition']['source_layers']['mental']))
                self.assertTrue(set(refs)<=set(arc['composition']['source_layers'][layer]))
                self.assertEqual(len(model['longitudinal']['evidence_factor_ids']),3)
                self.assertIn('Explicit cross-packet character reading',result.answer)
                damaged=thaw(proof.values);damaged['character_arcs'][0]['composition']['source_layers'][layer]=[]
                with self.assertRaises(HCLFailure):AnswerAssembler()._claim(replace(proof,values=damaged))
        # A header cannot claim unrelated text without a typed payload anchor.
        last['additions']['identities']=[]
        with self.assertRaises(HCLFailure) as error:self.compile(candidates)
        self.assertEqual(error.exception.diagnostic.field_path,'character_unaccounted_contribution_sources')

    def test_semantic_identifier_maps_and_reading_contents_preserve_namespace(self):
        from hcl.semantics.cross_packet_characters import IDENTIFIER_MAPS,grounded_refs,_merge_record
        compiler=LiteratureCompiler()
        for name in ('segment_ids','unmodeled_segments'):
            candidates=self.candidates();second=candidates[1]['character_contributions'][0];refs=second['segment_ids']
            second['additions']['interaction']['utterances']=[dict(id='message',at=3,speaker='a',audience=['b'],version='v',literal={name:False},
                deliveries=[dict(event_id='change-3',readings=[dict(actor='b',contents=[{name:False}],versions=['v'],segment_ids=refs)],segment_ids=refs)],segment_ids=refs)]
            candidates[0]['character_models'][0]['model']['mental']['variables'][0]['id']=name
            def rename(value):
                if isinstance(value,dict):
                    if value.get('op')=='atom' and value.get('name')=='open':value['name']=name
                    if isinstance(value.get('effects'),dict) and 'open' in value['effects']:value['effects'][name]=value['effects'].pop('open')
                    for item in value.values():rename(item)
                elif isinstance(value,list):
                    for item in value:rename(item)
            rename(candidates)
            duplicate=deepcopy(second['additions']['interaction']['utterances'][0])
            third=candidates[2]['character_contributions'][0]
            # Rebind only genuine record provenance, preserving literal dictionaries.
            duplicate['segment_ids']=third['segment_ids']
            duplicate['deliveries'][0]['segment_ids']=third['segment_ids']
            duplicate['deliveries'][0]['readings'][0]['segment_ids']=third['segment_ids']
            third['additions']['interaction']['utterances']=[duplicate]
            result,proof,_=self.run_candidates(candidates,replace(self.request,request_id='semantic-namespace-'+name))
            reading=proof.values['character_arcs'][0]['values']['models'][0]['inputs']['interaction']['utterances'][0]['deliveries'][0]['readings'][0]
            self.assertIs(reading['contents'][0][name],False)
            self.assertEqual(len(reading['segment_ids']),2)
            # Every declared semantic map/container shares this exact traversal rule.
            for field in IDENTIFIER_MAPS|{'contents'}:
                content=[{name:False}] if field=='contents' else {name:False}
                left={field:content,'segment_ids':['s1']};right={field:deepcopy(content),'segment_ids':['s2']}
                self.assertEqual(grounded_refs(compiler,left,{'s1':'source'},'source'),{'s1'})
                self.assertEqual(_merge_record(compiler,left,right)[field],content)
