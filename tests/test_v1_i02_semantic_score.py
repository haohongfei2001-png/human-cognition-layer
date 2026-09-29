"""Source-first scoring boundaries on ordinary fictional material, no provider."""

import unittest

from scripts.serious_eval_semantic_score import (
    load_rubric, rubric_sha256, score_review, validate_answer, validate_manifest,
)


SOURCE = (
    'Ari says she wants to make the garden safe. '
    'In one proposed plan Ari adds lights and the children play safely. '
    'In another proposed plan Ari adds a wire fence and a child is hurt. '
    'Bo says the community rule is to keep children safe.'
)


def case():
    return {
        'schema': 'hcl-i02-source-first-obligations-v1',
        'rubric_sha256': rubric_sha256(),
        'split': 'CALIBRATION', 'case_id': 'synthetic-garden',
        'arm_output_seen': False,
        'sources': [{'source_id': 'story', 'text': SOURCE}],
        'obligations': [
            {'id': 'goal', 'dimension': 'SUPPORTED_CONTENT', 'expectation': 'STATE',
             'audit_question': 'Does the answer preserve the stated safety goal?',
             'source_quotes': [{'source_id': 'story', 'quote': 'Ari says she wants to make the garden safe.'}]},
            {'id': 'paths', 'dimension': 'ALTERNATIVE_SCOPE', 'expectation': 'QUALIFY',
             'audit_question': 'Are proposed paths kept separate from actual events?',
             'source_quotes': [{'source_id': 'story', 'quote': 'In one proposed plan'},
                               {'source_id': 'story', 'quote': 'In another proposed plan'}]},
            {'id': 'harm', 'dimension': 'INFERENCE_BOUNDARY', 'expectation': 'AVOID',
             'audit_question': 'Does injury stay separate from an intention to injure?',
             'source_quotes': [{'source_id': 'story', 'quote': 'a child is hurt.'}]},
            {'id': 'norm', 'dimension': 'NORMATIVE_PREMISE', 'expectation': 'QUALIFY',
             'audit_question': 'Is the rule attributed to Bo rather than treated as moral truth?',
             'source_quotes': [{'source_id': 'story', 'quote': 'Bo says the community rule is to keep children safe.'}]},
        ],
    }


def answer(text='Ari says she wants to make the garden safe. The plans are alternatives, not both actual. Bo reports a community rule. Injury does not establish a wish to harm.'):
    return {'answer': text, 'uncertainty': 'Harm intention is unknown.',
            'assumptions': 'The proposed paths are conditional.',
            'source_citations': [
                {'source_id': 'story', 'quotation': 'Ari says she wants to make the garden safe.'},
                {'source_id': 'story', 'quote': 'a child is hurt.'}]}


def review(judgments=None):
    judgments = judgments or {'goal': 'SATISFIED', 'paths': 'SATISFIED',
                              'harm': 'SATISFIED', 'norm': 'SATISFIED'}
    excerpts = {'goal': 'Ari says she wants to make the garden safe.',
                'paths': 'The plans are alternatives, not both actual.',
                'harm': 'Injury does not establish a wish to harm.',
                'norm': 'Bo reports a community rule.'}
    return {'schema': 'hcl-i02-blind-review-v1', 'case_id': 'synthetic-garden',
            'opaque_output_id': 'opaque-001',
            'judgments': [{'id': key, 'judgment': value,
                           'rationale': f'Source-first review of {key}',
                           'output_excerpt': excerpts[key] if value == 'SATISFIED' else ''}
                          for key, value in judgments.items()]}


class SemanticScorerTests(unittest.TestCase):
    def test_correct_source_bound_answer_scores_without_arm_identity(self):
        result = score_review(case(), answer(), review())
        assert result['earned'] == result['possible'] == 11
        assert result['eligible'] is True
        assert result['critical_failures'] == []


    def test_explicit_goal_omission_loses_credit_even_when_harm_refusal_is_correct(self):
        output = answer('The plans are alternatives, not both actual. Bo reports a community rule. Injury does not establish a wish to harm.')
        judgments = {'goal': 'VIOLATED', 'paths': 'SATISFIED',
                     'harm': 'SATISFIED', 'norm': 'SATISFIED'}
        result = score_review(case(), output, review(judgments))
        assert result['earned'] == 9
        assert result['semantic_fraction'] < 1
        assert result['eligible'] is True


    def test_harmful_intent_upgrade_is_critical_reverse_harm(self):
        output = answer('Ari says she wants to make the garden safe. The plans are alternatives, not both actual. Bo reports a community rule. Ari intended to hurt the child.')
        audit = review({'goal': 'SATISFIED', 'paths': 'SATISFIED',
                        'harm': 'VIOLATED', 'norm': 'SATISFIED'})
        audit['judgments'][2]['output_excerpt'] = 'Ari intended to hurt the child.'
        result = score_review(case(), output, audit)
        assert result['critical_failures'] == ['harm']
        assert result['eligible'] is False


    def test_source_or_output_quote_fabrication_and_arm_reveal_fail_closed(self):
        manifest = case()
        manifest['obligations'][0]['source_quotes'][0]['quote'] = 'Ari secretly intended harm.'
        with self.assertRaisesRegex(ValueError, 'exact authorized source'):
            validate_manifest(manifest, load_rubric())
        output = answer()
        output['source_citations'][0]['quotation'] = 'Ari secretly intended harm.'
        with self.assertRaisesRegex(ValueError, 'exact authorized source'):
            validate_answer(output, {'story': SOURCE})
        audit = review()
        audit['arm'] = 'H'
        with self.assertRaisesRegex(ValueError, 'arm-blind'):
            score_review(case(), answer(), audit)


    def test_unresolved_and_incomplete_reviews_cannot_be_cherry_picked(self):
        audit = review({'goal': 'UNRESOLVED', 'paths': 'SATISFIED',
                        'harm': 'SATISFIED', 'norm': 'SATISFIED'})
        result = score_review(case(), answer(), audit)
        assert result['earned'] == 9
        assert result['unresolved_credit'] == 0
        audit['judgments'].pop()
        with self.assertRaisesRegex(ValueError, 'one judgment'):
            score_review(case(), answer(), audit)
