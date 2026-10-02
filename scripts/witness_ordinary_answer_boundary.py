"""New authored provider-free boundary witness; no model efficacy claim."""
import json
from hcl.cognition import CognitionWorkspace
from scripts.serious_eval_contract import runtime_digest


def witness():
    cases = [
        ('unsupported_trait', 'Mira closed the workshop door. Theo waited outside.',
         'Mira closed the door because she is inherently spiteful.', 'Mira closed the workshop door.'),
        ('reported_reason', 'Mira said, “I intend to close the workshop door.”',
         'The source reports Mira expressing an intention to close the door.',
         'Mira said, “I intend to close the workshop door.”'),
        ('reported_receipt', 'Mira said, “The workshop door is closed.” Theo heard Mira\'s last statement.',
         'The source reports Theo hearing Mira\'s statement; this does not establish acceptance.',
         'Theo heard Mira\'s last statement.'),
        ('availability_only', 'Mira said, “The workshop door is closed.” Mira\'s last statement was publicly available.',
         'Availability alone does not establish that Theo heard or accepted the statement.',
         'Mira\'s last statement was publicly available.'),
    ]
    results = []
    for case, source, answer, quote in cases:
        workspace = CognitionWorkspace(); workspace.put_source('authored-source', source)
        raw = json.dumps(dict(answer=answer, source_citations=[quote], uncertainty='', assumptions=''))
        result = workspace.answer_reader_entry('What can be concluded about Mira?', lambda messages: raw,
            source_ids=('authored-source',), allow_translation=False, max_chars=18000)
        results.append(dict(case=case, source=source, stub_answer=answer,
            checked_treatment_present=result['prepared'].receipt['checked_treatment_present'],
            quote_audit_status=result['source_citation_audit']['status'],
            semantic_certification=result['source_citation_audit']['semantic_certification'],
            raw_delivered_unchanged=result['answer']==raw, extraction_calls=result['preparation_provider_calls']))
    return dict(schema='hcl-ordinary-answer-boundary-witness-v1', runtime_sha256=runtime_digest(),
        provider_calls=0, synthetic_stub_answers=True, model_failure_observed=False,
        conclusion='EXACT_QUOTES_DO_NOT_CERTIFY_EXPLANATION; GENERAL_BOUNDARY_QUEUE_REMAINS_OPEN', cases=results)

if __name__ == '__main__': print(json.dumps(witness(), ensure_ascii=False, indent=2, sort_keys=True))
