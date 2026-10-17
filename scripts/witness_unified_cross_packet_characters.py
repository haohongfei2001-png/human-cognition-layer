"""Independent provider-free v3 packet port and actual run/stream witness.

No tests or expected M09 trajectories are imported. All fit, turn and future
results come from the real shared operators and verified ordinary delivery.
"""
import argparse
import asyncio
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile

from hcl import HCL, ExecutionBudget, ExecutionIssue
from hcl.kernel.types import Principal, TaskRequest, Issue, thaw
from hcl.memory import codec
from hcl.memory.store import StateStore
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.runtime.context import ContextCompiler
from scripts.witness_unified_relationship import propose as relationship_propose

QUESTION = "Compare the conditional character arc."
PARAGRAPHS = [
    "EARLY: B waits at closure time 1 and crosses at opening time 2; shared source-local actors and safety/duty/coping mechanisms are declared conditional interpretations ",
    "REVEAL: a closure report reaches B at story time 3; the reader learns this after the early behaviour; this supplies no earlier receipt ",
    "COUNTER: at story time 4 B observes opening but a reported choice can oppose the early pattern; time 5 is a hypothetical forecast ",
    "UNRELATED: a landscape description makes no declaration about this character ",
]
SOURCE = "\n".join(p + "original context " * 200 for p in PARAGRAPHS)


def proposals(snapshot, chunks, mode):
    raw = relationship_propose(snapshot, QUESTION, "counterevidence" if mode == "late" else "stable")["models"][0]
    raw['mental']['events'][2].update(kind='message',seen_by=[],received_by=['b'],understood_by=['b'],trusted_by=['b'])
    dynamic = [('mental','events'),('mental','queries'),('mental','plans'),
        ('interaction','utterances'),('interaction','acts'),('interaction','commitments'),('interaction','games'),
        ('affect','episodes'),('affect','channels'),('relationships',),('roles',),('identities',),('observations',),('forecasts',)]
    def get(value, path):return value[path[0]] if len(path)==1 else value[path[0]][path[1]]
    def put(value,path,rows):
        if len(path)==1:value[path[0]]=rows
        else:value.setdefault(path[0],{})[path[1]]=rows
    def anchor(value,refs):
        if isinstance(value,dict):
            for k,v in value.items():
                if k=='segment_ids' and isinstance(v,list):value[k]=list(refs)
                else:anchor(v,refs)
        elif isinstance(value,list):
            for v in value:anchor(v,refs)
    all_segments=[s for c in chunks for s in c.segments]
    assert len(all_segments)==4
    owners={s.segment_id:c.ordinal for c in chunks for s in c.segments}
    frame=dict(fragment=owners[all_segments[0].segment_id],id='declared-work-frame')
    static=deepcopy(raw)
    for path in dynamic:put(static,path,[])
    rows=[]
    for chunk in chunks:
        packet=dict(schema='hcl-literature-fragment-3',assumptions=[],active_assumptions=[],frames=[],events=[],mentions=[],orders=[],queries=[],motifs=[],variants=[],comparisons=[],analogies=[],unmodeled_segments=[],character_models=[],character_contributions=[])
        for segment in chunk.segments:
            chapter=all_segments.index(segment);refs=[segment.segment_id]
            if chapter==3:
                packet['unmodeled_segments'].extend(refs)
                if mode=='unrelated':packet['motifs'].append(dict(id='landscape',literal='landscape',segment_ids=refs))
                continue
            if chapter==0:
                anchor(static,refs)
                packet['frames'].append(dict(id=frame['id'],parent=None,kind='INTERPRETATION',narrator='analyst',focalizer='b',segment_ids=refs))
                packet['character_models'].append(dict(id='source-b',source_id='records',actor='b',frame=frame,assumptions=[],segment_ids=refs,model=static))
            if chapter==2 and mode=='disconnected':
                packet['unmodeled_segments'].extend(refs);continue
            times=((0,1,2),(3,),(4,5))[chapter]
            additions={}
            for path in dynamic:
                def at(r):
                    if path[0] in ('observations','forecasts'):
                        return next(e['at'] for e in raw['affect']['episodes'] if e['id']==r['episode_id'])
                    return r.get('at',1)
                put(additions,path,[deepcopy(r) for r in get(raw,path) if at(r) in times])
            anchor(additions,refs)
            bindings=[]
            for episode in additions['affect']['episodes']:
                packet['events'].append(dict(id=episode['id'],frame=frame,description='Explicit original event',assumptions=[],segment_ids=refs))
                bindings.append(dict(episode_id=episode['id'],event=dict(fragment=chunk.ordinal,id=episode['id']),at=episode['at']))
            if chapter==2 and mode=='evidence_only':
                for path in dynamic:put(additions,path,[])
                packet['events']=[];bindings=[]
            if chapter==2 and mode in ('alias','independent'):
                episode=deepcopy(raw['affect']['episodes'][0]);episode['id']='alias-display'
                if mode=='independent':episode['episode_id']='independent-event'
                anchor(episode,refs);additions['affect']['episodes'].append(episode)
                report=deepcopy(raw['observations'][0]);report.update(id='alias-choice',context_id='new-report',episode_id=episode['id'])
                anchor(report,refs);additions['observations'].append(report)
                packet['events'].append(dict(id='alias-story-event',frame=frame,description='Explicit event reference',assumptions=[],segment_ids=refs))
                bindings.append(dict(episode_id=episode['id'],event=dict(fragment=chunk.ordinal,id='alias-story-event'),at=episode['at']))
            if chapter==2 and mode in ('duplicate','evidence_only'):
                report=deepcopy(raw['observations'][0]);report.update(id='retelling',context_id='later-report',segment_ids=refs)
                additions['observations'].append(report)
                bindings.append(dict(episode_id='episode-1',event=dict(fragment=frame['fragment'],id='episode-1'),at=1))
            packet['character_contributions'].append(dict(id='chapter-'+str(chapter),declaration=dict(fragment=frame['fragment'],id='source-b'),
                source_id='records',actor='b',frame=frame,assumptions=[],segment_ids=refs,bindings=bindings,additions=additions))
        rows.append(packet)
    return rows


def witness():
    owner=Principal('synthetic-v3-witness','reader');rows=[];rejections=[]
    budget=ExecutionBudget(max_mock_calls=4,max_feedback=0,max_output_bytes=1048576,max_total_output_bytes=16777216,
        max_visible_output_tokens=1048576,max_request_bytes=10000,max_context_tokens=10000,max_steps=64,max_local_evaluations=100000)
    with tempfile.TemporaryDirectory() as root:
        store=StateStore.sqlite(Path(root)/'state.sqlite',revision=True);store.create_session('s',owner)
        handle=store.put_source('s',owner,'records',SOURCE);snapshot=store.snapshot('s',owner,(handle,))
        try:
            for mode in ('stable','late','unrelated','duplicate','disconnected','frontier','regrouped','independent','evidence_only','alias'):
                allowance=replace(budget,max_local_evaluations=8) if mode=='frontier' else replace(budget,max_request_bytes=20000,max_context_tokens=20000) if mode=='regrouped' else budget
                chunks=ContextCompiler().chunks(snapshot,QUESTION,'literature_compile',allowance,OfflineModelPort().describe())
                assert len(chunks)==(1 if mode=='regrouped' else 4)
                candidates=proposals(snapshot,chunks,mode)
                port=OfflineModelPort(responses=tuple(json.dumps(c) for c in candidates))
                request=TaskRequest(mode,QUESTION,(handle,),'s',owner,budget=allowance,issue=ExecutionIssue('root',goals=(Issue(mode,'literature.analyze'),)))
                client=HCL(store,principal=owner,gateway=ModelGateway(store,port))
                async def collect():return [e async for e in client.stream(request)]
                result=asyncio.run(collect())[-1].result
                if mode=='alias':
                    assert not result.claim_records and not result.answer
                    assert result.status!='COMPLETED' and port.attempts==len(chunks)
                    rejections.append(dict(case=mode,status=result.status,diagnostics=[dict(stage=d.stage,code=d.code,field_path=d.field_path) for d in result.diagnostics],packets_read=port.attempts))
                    continue
                assert result.status=='PARTIAL',result.diagnostics
                assert port.attempts==len(chunks)
                actual_read=''.join(s['text'] for wire in port.contexts for s in json.loads(wire)['segments'] if s['kind']=='SOURCE')
                assert actual_read==SOURCE
                assert all(json.loads(wire)['candidate_schema']=='hcl-literature-fragment-1' for wire in port.contexts)
                proof=next(r for r in store.inferences('s',owner) if r.result_id in result.execution_receipt['result_ids'])
                assert len(proof.values['character_arcs'])==1
                arc=thaw(proof.values['character_arcs'][0]);model=arc['values']['models'][0]
                assert 'Explicit cross-packet character reading' in result.answer
                assert any(f.field=='character_arcs' for c in result.claim_records for f in c.used_result_fields)
                assert result.usage['local_evaluations']<=allowance.max_local_evaluations
                attempts=port.attempts;replay=client.run_sync(request)
                assert replay.answer==result.answer and port.attempts==attempts
                rows.append(dict(case=mode,actual=arc,answer=result.answer,usage=dict(result.usage),
                    packets_read=len(port.contexts),source_read_sha256=sha256(actual_read.encode()).hexdigest(),
                    candidate_sha256=[sha256(json.dumps(c,sort_keys=True).encode()).hexdigest() for c in candidates],replay_new_attempts=port.attempts-attempts))
            stable,late,unrelated,duplicate,disconnected,frontier,regrouped,independent,evidence_only=[r['actual']['values']['models'][0] for r in rows]
            assert stable['prediction_matrix']==late['prediction_matrix']
            assert stable['longitudinal']['pareto_explored']!=late['longitudinal']['pareto_explored']
            assert any(t['change_points'] for t in late['preferred_forecasts'])
            assert rows[0]['answer']!=rows[1]['answer']
            assert stable==unrelated
            assert stable['longitudinal']['evidence_factor_ids']==duplicate['longitudinal']['evidence_factor_ids']
            assert {codec.canonical(t['profile']) for t in stable['longitudinal']['trajectories']}=={codec.canonical(t['profile']) for t in duplicate['longitudinal']['trajectories']}
            assert len(disconnected['observations'])==3
            assert frontier['longitudinal']['global_comparison']=='NOT_ESTABLISHED'
            assert stable==regrouped
            assert len(independent['longitudinal']['evidence_factor_ids'])==5
            assert evidence_only['inputs']['mental']==disconnected['inputs']['mental']
            assert evidence_only['longitudinal']['evidence_factor_ids']==disconnected['longitudinal']['evidence_factor_ids']
            layers=rows[-1]['actual']['composition']['source_layers']
            assert set(layers['observations'])-set(layers['mental'])
            assert not evidence_only['inputs']['mental']['unmodeled_segments']
        finally:store.close()
    root=Path(__file__).resolve().parents[1]
    return dict(schema='hcl-cross-packet-character-witness-1',checked_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
        runtime_hashes={str(p.relative_to(root)):sha256(p.read_bytes()).hexdigest() for p in sorted((root/'hcl').rglob('*.py'))},
        rows=rows,rejections=rejections,provider_calls=0,provider_spend_usd=0,sealed_content_reads=0,
        evidence_scope='EXPLICIT_SOURCE_LOCAL_V3_JOINS_ACTUAL_PACKET_READING_M09_M11_INTEGRATED_OFFLINE',
        not_established=['AUTOMATIC_V3_EXTRACTION','CROSS_SOURCE_OR_SESSION_IDENTITY','UNBOUNDED_NOVEL_UNDERSTANDING','FULL_M09','FULL_M11','FULL_S3','FULL_S4','LIVE_EFFECT'])


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path);args=parser.parse_args()
    args.output.write_text(json.dumps(witness(),ensure_ascii=False,sort_keys=True,indent=2)+'\n')
