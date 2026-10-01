"""Provider-free final budget gates; unchanged v24 source/checker/message bytes."""
import json
import sys
import types
import unittest
import zipfile

from hcl.cognition import CognitionWorkspace
from hcl.cognition import reader_entry as current
from scripts.development_drc008_replay import ARCHIVE, validate_archive
from tests.test_v1_conditional_reader_entry import Backend, SOURCE, proposals

QUERY = 'Explain what the source supports and which interpretations remain open.'
SIMPLE = 'Lena wrote "灯".\nThe crate stayed shut.'
CHECKED = ('Lena believes the corridor is clear. '
           'Lena said, "I do not believe the corridor is clear." '
           'Lena said, "I plan to carry the crate in order to clear the room if the corridor is clear."')


def workspace(source):
    w = CognitionWorkspace(); w.put_source('meeting', source); return w


def response(source):
    return json.dumps(dict(answer='A source report.',
        source_citations=[dict(source_id='meeting', quote=source)],
        uncertainty='No additional information.', assumptions='None.'))


class ReaderFinalBudgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        validate_archive()
        with zipfile.ZipFile(ARCHIVE) as z:
            text = z.read('hcl/cognition/reader_entry.py').decode()
        name = 'hcl.cognition._certified_v24_budget_test'
        cls.old = types.ModuleType(name)
        cls.old.__package__ = 'hcl.cognition'
        sys.modules[name] = cls.old
        exec(compile(text, str(ARCHIVE) + ':reader_entry.py', 'exec'), cls.old.__dict__)

    def test_current_amendment_and_wrong_digest(self):
        from scripts.development_embedded_scene_amendment import validate_current
        self.assertTrue(validate_current())
        with self.assertRaises(ValueError):
            validate_current(current_digest='0' * 64)

    def test_standalone_and_final_wire_equal_certified_v24_at_sufficient_budgets(self):
        for source in (SIMPLE, SOURCE, CHECKED):
            for translation in (False, True):
                for useful in (False, True):
                    with self.subTest(source=source, translation=translation, useful=useful):
                        oldw, neww = workspace(source), workspace(source)
                        oldb, newb = Backend(proposals() if useful and source == SOURCE else []), Backend(proposals() if useful and source == SOURCE else [])
                        kwargs = dict(source_ids=('meeting',), max_chars=64000, allow_translation=translation)
                        oldp = self.old.prepare_reader_entry(oldw, QUERY, backend=oldb, **kwargs)
                        newp = current.prepare_reader_entry(neww, QUERY, backend=newb, **kwargs)
                        self.assertEqual(oldp.messages, newp.messages)
                        self.assertEqual(oldp.receipt, newp.receipt)
                        self.assertEqual(oldb.calls, newb.calls)
                        olda = self.old.answer_reader_entry(workspace(source), QUERY, lambda _: response(source),
                            backend=Backend(proposals() if useful and source == SOURCE else []), **kwargs)
                        newa = current.answer_reader_entry(workspace(source), QUERY, lambda _: response(source),
                            backend=Backend(proposals() if useful and source == SOURCE else []), **kwargs)
                        self.assertEqual(olda['actual_final_messages'], newa['actual_final_messages'])
                        self.assertEqual(olda['prepared'].receipt, newa['prepared'].receipt)
                        self.assertEqual(olda['answer_raw'], newa['answer_raw'])
                        self.assertEqual(olda['source_citation_audit'], newa['source_citation_audit'])
                        self.assertNotIn('answer_inference_boundary', newp.receipt)

    def test_old_final_wire_overflows_prepared_only_budget_new_refuses_without_extraction(self):
        # Local preparation fits. The known final instruction does not fit.
        source = CHECKED
        p = self.old.prepare_reader_entry(workspace(source), QUERY, source_ids=('meeting',))
        budget = len(json.dumps(p.messages, ensure_ascii=False))
        old_calls = []
        old = self.old.answer_reader_entry(workspace(source), QUERY,
            lambda m: old_calls.append(m) or response(source), source_ids=('meeting',), max_chars=budget)
        self.assertGreater(len(json.dumps(old['actual_final_messages'], ensure_ascii=False)), budget)
        self.assertEqual(len(old_calls), 1)
        for opt_in in (False, True):
            calls, backend = [], Backend()
            with self.assertRaisesRegex(ValueError, 'final answer contract exceeds context budget'):
                current.answer_reader_entry(workspace(source), QUERY, lambda m: calls.append(m),
                    source_ids=('meeting',), backend=backend, allow_translation=opt_in, max_chars=budget)
            self.assertFalse(backend.calls)
            self.assertFalse(calls)

    def test_intermediate_ceiling_not_shrunk_for_minimized_wire_cold_and_warm(self):
        probe = current.prepare_reader_entry(workspace(SIMPLE), QUERY, source_ids=('meeting',))
        intermediate = json.loads(probe.prepared.preparation_json)['actual_final_messages']
        budget = len(json.dumps(intermediate, ensure_ascii=False))
        for warm in (False, True):
            w = workspace(SIMPLE)
            if warm:
                current.prepare_reader_entry(w, QUERY, source_ids=('meeting',), max_chars=budget)
            calls = []
            result = current.answer_reader_entry(w, QUERY, lambda m: calls.append(m) or response(SIMPLE),
                source_ids=('meeting',), max_chars=budget)
            self.assertLess(len(json.dumps(result['actual_final_messages'], ensure_ascii=False)), budget)
            self.assertEqual(result['answer_context_budget']['intermediate_preparation_limit_characters'], budget)
            self.assertEqual(len(calls), 1)

    def test_actual_final_exact_fit_and_one_short_checked_source(self):
        source = CHECKED
        large = current.answer_reader_entry(workspace(source), QUERY, lambda _: response(source), source_ids=('meeting',))
        exact = len(json.dumps(large['actual_final_messages'], ensure_ascii=False))
        calls = []
        result = current.answer_reader_entry(workspace(source), QUERY, lambda m: calls.append(m) or response(source),
            source_ids=('meeting',), max_chars=exact)
        self.assertEqual(result['actual_final_messages'], large['actual_final_messages'])
        self.assertEqual(result['answer_context_budget']['reserved_final_instruction_characters'], 237)
        with self.assertRaises(ValueError):
            current.answer_reader_entry(workspace(source), QUERY, lambda m: calls.append(m),
                source_ids=('meeting',), max_chars=exact-1)
        self.assertEqual(len(calls), 1)

    def test_unpredictable_translated_size_is_bounded_before_final_answer(self):
        p = self.old.prepare_reader_entry(workspace(SOURCE), QUERY, source_ids=('meeting',),
            backend=Backend(), allow_translation=True)
        self.assertEqual(p.receipt['selection'], 'CONDITIONAL_TRANSLATION')
        maximum = len(json.dumps(p.messages, ensure_ascii=False))
        calls, b = [], Backend()
        with self.assertRaisesRegex(ValueError, 'final answer contract exceeds context budget'):
            current.answer_reader_entry(workspace(SOURCE), QUERY, lambda m: calls.append(m),
                source_ids=('meeting',), backend=b, allow_translation=True, max_chars=maximum)
        # The response-dependent representation cannot be sized before extraction.
        # Its single explicitly opted-in extraction is retained, without a retry.
        self.assertEqual(len(b.calls), 1)
        self.assertFalse(calls)

    def test_invalid_budget_never_extracts_or_answers(self):
        for maximum in (True, 511, 64001, None, '64000'):
            b = Backend(); calls = []
            with self.assertRaises(ValueError):
                current.answer_reader_entry(workspace(SOURCE), QUERY, lambda m: calls.append(m),
                    source_ids=('meeting',), backend=b, allow_translation=True, max_chars=maximum)
            self.assertFalse(b.calls); self.assertFalse(calls)

    def test_revision_during_answer_still_fails_closed(self):
        for remove in (False, True):
            w = workspace(SIMPLE)
            def mutate(_):
                if remove: w.remove_source('meeting')
                else: w.put_source('meeting', 'Changed source.')
                return response(SIMPLE)
            result = current.answer_reader_entry(w, QUERY, mutate, source_ids=('meeting',))
            self.assertFalse(result['source_citation_audit']['deliverable'])
            self.assertEqual(result['answer_raw'], response(SIMPLE))


if __name__ == '__main__':
    unittest.main()
