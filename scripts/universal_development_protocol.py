"""Six fixed authored human-domain tasks; no module preselection or provider execution."""
from decimal import Decimal
import hashlib,json
from pathlib import Path
from hcl.cognition.deepseek_metered import MAX_REQUEST_BYTES,OUTPUT_TOKENS,OUTPUT_MARGIN,INPUT_RATE,OUTPUT_RATE,MODEL
from hcl.cognition.universal_entry import PLANNER_POLICY
from scripts.serious_eval_contract import runtime_digest

CASES=[
 dict(case_id='society_without_source',question='分析人类社会：从个体动机、人与人互动、制度三个层次说明它们如何相互影响。指出概括的局限，不要把所有社会或个人说成一样。',sources={},expected_label=None,scoring='SOURCE_FIRST_OPEN_ENDED_REVIEW_NOT_NUMERIC_ACCURACY',review_criteria=['addresses all three requested levels','does not invent supplied evidence or citations','states material limits without refusing ordinary analysis']),
 dict(case_id='reported_belief_change',question='What does the source establish? Answer A, B, or C: A) Iris made different public belief reports; B) Iris\'s true private belief certainly changed; C) the bridge is objectively unsafe.',sources={'bridge':'Iris said, "I believe the bridge is safe." Iris said, "I do not believe the bridge is safe."'},expected_label='A',scoring='EXACT_OPTION_AND_SEPARATE_SOURCE_FIRST_EXPLANATION'),
 dict(case_id='receipt_not_availability',question='Whose hearing is explicitly reported? Answer A, B, or C: A) everyone; B) Mara; C) nobody. Keep reported hearing distinct from agreement or knowledge.',sources={'notice':'Iris said, "The hall is closed." Iris\'s last statement was publicly available. Leon did not hear Iris\'s last statement. Mara heard Iris\'s last statement.'},expected_label='B',scoring='EXACT_OPTION_AND_SEPARATE_SOURCE_FIRST_EXPLANATION'),
 dict(case_id='competing_action_reasons',question='Why did Nia skip the meeting, and is a single actual motive established? Answer A, B, or C: A) definitely only to avoid noise; B) two reported goals can support conditional explanations, without proving a unique actual motive; C) definitely because she dislikes coworkers.',sources={'meeting':'\n'.join(['Nia said, "I want to avoid the noise."','Nia said, "I plan to skip the meeting in order to avoid the noise."','Nia said, "I want to finish the report."','Nia said, "I plan to skip the meeting in order to finish the report."','Nia said, "At the time, I knew about the meeting."','Nia said, "At the time, I could skip the meeting."','Nia said, "I skipped the meeting."'])},expected_label='B',scoring='EXACT_OPTION_AND_SEPARATE_SOURCE_FIRST_EXPLANATION'),
 dict(case_id='conditional_responsibility',question='For this analysis, responsibility requires causal contribution and control. Is Ari responsible on this rule and the supplied reports? Answer A, B, or C: A) yes, all required factors are reported; B) definitely morally blameworthy; C) unresolved because control is not established.',sources={'gate':'Ari: I opened the gate.\nNarrator: The animals escaped.\nNarrator: Ari opening the gate caused the animals to escape.'},expected_label='C',scoring='EXACT_OPTION_AND_SEPARATE_SOURCE_FIRST_EXPLANATION'),
 dict(case_id='contextual_values_two_sources',question='Compare Lena\'s reported priorities. Answer A, B, or C: A) a single global ranking is established for every situation; B) one statement proves the other false; C) reported priorities differ by context and do not establish a unique context-free ranking.',sources={'routine':'Lena said, "During routine maintenance I prefer a slower inspection to reduce the chance of overlooking damage."','emergency':'Lena said, "During an urgent evacuation I prefer leaving promptly rather than finishing a routine inspection."'},expected_label='C',scoring='EXACT_OPTION_AND_SEPARATE_SOURCE_FIRST_EXPLANATION'),
]

for _case in CASES:
    if _case['expected_label'] is not None:
        _case['question'] += ' Put only the chosen letter in the JSON answer field; use assumptions and uncertainty for explanatory limits.'

def ordinary(case):return {key:case[key]for key in ('question','sources')}
def digest(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def protocol():
    input_cost=(2*MAX_REQUEST_BYTES+2048)*INPUT_RATE/1000000
    maxima={phase:input_cost+(tokens+OUTPUT_MARGIN)*OUTPUT_RATE/1000000 for phase,tokens in OUTPUT_TOKENS.items()}
    ceiling=6*maxima['planning']+12*maxima['answer']
    return dict(schema='hcl-universal-authored-development-protocol-v1',
        purpose='CONSTRUCTED_FUNCTIONAL_DEVELOPMENT_COMPARISON_NOT_INDEPENDENT_GENERALIZATION',
        selection='SIX_FIXED_HUMAN_DOMAIN_TASKS_BEFORE_OUTPUTS_NO_CAPABILITY_TRIGGER_FILTER',
        cases=[dict(case_id=c['case_id'],ordinary_input_sha256=digest(ordinary(c)),scoring=c['scoring'],
                    arm_order=['Base','HCL']if i%2==0 else ['HCL','Base'])for i,c in enumerate(CASES)],
        source_package_sha256=digest(CASES),runtime_sha256=runtime_digest(),
        planner_policy_sha256=hashlib.sha256(PLANNER_POLICY.encode()).hexdigest(),
        model=MODEL,model_snapshot='RETURNED_ALIAS_NOT_PHYSICAL_SNAPSHOT_CERTIFICATION',
        base_calls=6,hcl_planning_calls=6,hcl_answer_calls=6,maximum_calls=18,
        extraction_calls=0,grader_calls=0,retries=0,phase_output_tokens=OUTPUT_TOKENS,
        maximum_request_bytes=MAX_REQUEST_BYTES,input_bound='2_UTF8_SERIALIZED_REQUEST_BYTES_PLUS_2048',
        output_margin=OUTPUT_MARGIN,rates_usd_per_million={'input':str(INPUT_RATE),'output':str(OUTPUT_RATE)},
        phase_maximum_reservation_usd={k:str(v)for k,v in maxima.items()},
        all_call_maximum_reservation_usd=str(ceiling),proposed_cap_usd='2.50',
        authorized_calls=0,authorized_spend_usd=0,live_execution_enabled=False,
        historical_budget_transfer=False,labels_and_rubrics_never_sent_to_provider=True,
        internal_planner_selects_capabilities=True,missing_treatment_is_observed_outcome=True,
        no_source_answer_is_unsourced_model_knowledge=True,
        final_confirmation_qualified=False,longmemeval='SEALED_NOT_ACCESSED')

if __name__=='__main__':
    print(json.dumps(protocol(),ensure_ascii=False,sort_keys=True,indent=2))
