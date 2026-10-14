"""Independent finite directional classification oracle and typed LGG queries."""
from copy import deepcopy
from itertools import product
import unittest

from hcl.operators.concept_induction import generalize_examples, match_independent_case
from hcl.operators.concept_versions import classify_case
from hcl.operators.judgment import JudgmentWork
from scripts.witness_unified_concept_judgment import term


class ClassificationMathTests(unittest.TestCase):
    def definition(self, pairs, direction="BICONDITIONAL"):
        positives=[dict(id=str(i),term=term("pair",term(a),term(b))) for i,(a,b) in enumerate(pairs)]
        return dict(id="c",direction=direction,actual=generalize_examples(positives,[]),counterexamples=[],boundary=[],withdrawn=False)

    def test_exhaustive_independent_membership_oracle(self):
        patterns=[self.definition([("a","a"),("b","b")]),
                  self.definition([("a","b"),("c","d")]),
                  self.definition([("a","a")])]
        directions=("NECESSARY","SUFFICIENT","BICONDITIONAL","TYPICAL")
        for kinds in product(directions,repeat=3):
            for a,b in (("a","a"),("c","c"),("c","d")):
                rows=[dict(p,direction=d) for p,d in zip(patterns,kinds)]
                matched=(a==b,True,a==b=="a")
                positive=any(m and d in ("SUFFICIENT","BICONDITIONAL") for m,d in zip(matched,kinds))
                negative=any(not m and d in ("NECESSARY","BICONDITIONAL") for m,d in zip(matched,kinds))
                expected=[True] if positive and not negative else [False] if negative and not positive else [False,True]
                case=dict(term=term("pair",term(a),term(b)),assumptions=[],active_assumptions=[])
                actual=classify_case(dict(criteria=rows,withdrawn=[]),case,JudgmentWork(1000))
                self.assertEqual(actual["possible_values"],expected,(kinds,a,b,actual))
                if positive and negative:self.assertEqual(actual["status"],"CONFLICTING")

    def test_necessary_sufficient_and_typical_directions(self):
        pattern=self.definition([("a","a"),("b","b")])
        for direction,yes,no in [("NECESSARY",[False,True],[False]),("SUFFICIENT",[True],[False,True]),
                                  ("BICONDITIONAL",[True],[False]),("TYPICAL",[False,True],[False,True])]:
            for pair,wanted in [(("c","c"),yes),(("c","d"),no)]:
                actual=classify_case(dict(criteria=[dict(pattern,direction=direction)],withdrawn=[]),
                    dict(term=term("pair",*(term(x) for x in pair)),assumptions=[],active_assumptions=[]),JudgmentWork(100))
                self.assertEqual(actual["possible_values"],wanted)

    def test_missing_withdrawn_challenged_and_boundary_are_not_false(self):
        row=self.definition([("a","a"),("b","b")])
        case=dict(term=term("pair",term("c"),term("c")),assumptions=[],active_assumptions=[])
        for changed,c in [(dict(row,withdrawn=True),case),(dict(row,counterexamples=["bad"]),case),
                          (dict(row,boundary=[dict(term=case["term"])]),case),(row,dict(case,term=None)),
                          (row,dict(case,assumptions=["missing"]))]:
            self.assertEqual(classify_case(dict(criteria=[changed],withdrawn=[]),c,JudgmentWork(100))["possible_values"],[False,True])

    def test_query_is_not_training_and_repeated_variables_hold(self):
        definition=self.definition([("a","a"),("b","b")])
        before=deepcopy(definition)
        check=match_independent_case(definition["actual"]["pattern"],term("pair",term("c"),term("d")),JudgmentWork(100).spend)
        self.assertEqual(check["status"],"NO_MATCH")
        self.assertEqual(definition,before)
        with self.assertRaises(OverflowError):
            match_independent_case(definition["actual"]["pattern"],term("pair",term("c"),term("c")),JudgmentWork(1).spend)
