"""Preparation is useful without granting a run or rewriting native labels."""
import json
from pathlib import Path
import unittest
from scripts.development_mindgames_source import select_rows, prepare_source
from scripts.development_confirmation_firewall import require_final_development_disjoint


class SourcePreparationTests(unittest.TestCase):
    def test_selection_uses_only_stable_native_index_not_labels_or_difficulty(self):
        rows=[dict(index=i,premise='SYNTHETIC public source',hypothesis='SYNTHETIC question',label='entailment',difficulty=i) for i in range(20)]
        original=[r['index'] for r in select_rows(rows)]
        changed=[dict(r,label='not_entailment',difficulty=-r['difficulty']) for r in reversed(rows)]
        self.assertEqual(original,[r['index'] for r in select_rows(changed)])
        for bad in [rows+[rows[0]], [dict(rows[0],index=True)], []]:
            with self.assertRaises(ValueError):select_rows(bad)

    def test_native_input_is_exact_and_excludes_oracle_and_model_fields(self):
        row=dict(index=1,premise='  SYNTHETIC 原文\nnot changed. ',hypothesis='SYNTHETIC query?',label='entailment',smcdel_problem='FORMAL_ORACLE',pbcheck='ANSWER_TRACE',deberta_pred=1,difficulty=0.99,setup='hidden_config')
        prepared=prepare_source(row)
        self.assertEqual(prepared['ordinary_input'],dict(premise=row['premise'],hypothesis=row['hypothesis']))
        self.assertEqual(set(prepared['ordinary_input']),{'premise','hypothesis'})
        changed=prepare_source(dict(row,label='not_entailment',smcdel_problem='OTHER'))
        self.assertEqual(prepared['ordinary_input_sha256'],changed['ordinary_input_sha256'])
        self.assertNotEqual(prepared['native_row_sha256'],changed['native_row_sha256'])
        self.assertEqual(prepared['authorized_calls'],0)
        self.assertFalse(prepared['live_execution_enabled'])
        for changes in [dict(premise=''),dict(hypothesis=None),dict(label='maybe'),dict(index=True)]:
            with self.assertRaises(ValueError):prepare_source(dict(row,**changes))

    def test_receipt_retains_all_fixed_rows_and_no_execution_or_efficacy_claim(self):
        value=json.loads(Path('reports/HCL_DEVELOPMENT_SOURCE_PREPARATION.json').read_text())
        self.assertEqual(value['provider_calls'],0);self.assertEqual(value['authorized_calls'],0)
        self.assertEqual(value['authorized_spend_usd'],0);self.assertEqual(value['model_answers'],[])
        self.assertFalse(value['admitted_for_paid_execution']);self.assertFalse(value['final_confirmation_qualified'])
        self.assertFalse(value['operational_model_scorer_freeze'])
        self.assertEqual([c['native_index'] for c in value['mindgames']['cases']],[3274,41454,41671,54915,65380,1556])
        self.assertEqual(len(value['tombench']['cases']),6)
        for group in ['mindgames','tombench']:
            self.assertEqual(value[group]['history']['history']['checkout_head'],value['base_main'])
            self.assertTrue(value[group]['history']['history_clear'])
            for case in value[group]['cases']:
                self.assertFalse(case['grade_rewritten']);self.assertFalse(case['model_output_seen'])
        self.assertEqual(value['tombench']['cases'][1]['native_label'],'B')
        self.assertEqual(value['tombench']['cases'][1]['source_first_review'],'REJECT_SOURCE_QUESTION_OPTION_MISMATCH')
        self.assertEqual(value['tombench']['cases'][-1]['native_label'],'B')
        self.assertEqual(value['tombench']['cases'][-1]['source_first_review'],'UNSUPPORTED_NATIVE_PREDICTION')

    def test_opened_publisher_aliases_native_rows_and_sources_are_final_consumed(self):
        value=json.loads(Path('reports/HCL_DEVELOPMENT_SOURCE_PREPARATION.json').read_text())
        candidates=[dict(source_url=u) for u in ['https://huggingface.co/datasets/sileod/mindgames/resolve/future/file','https://github.com/sileod/llm-theory-of-mind/blob/future/file']]
        for group in ['mindgames','tombench']:
            for case in value[group]['cases']:
                candidates += [dict(source_sha256=case[k],dataset_id='renamed') for k in ['native_row_sha256','source_sha256']]
        candidates.append(dict(source_sha256=value['mindgames']['distribution_sha256']))
        for candidate in candidates:
            with self.subTest(candidate=candidate),self.assertRaises(ValueError):require_final_development_disjoint(candidate)


if __name__=='__main__':unittest.main()
