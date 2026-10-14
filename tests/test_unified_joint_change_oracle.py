"""Independent exhaustive oracles for the small finite joint-edit language.

The reference search enumerates complete assignments, not paths through legal
single-edit intermediates. Its M13 oracle builds proof trees and enumerates all
complete three-valued labellings; its M14 oracle uses exact Fraction arithmetic.
Neither oracle calls production argument, classification or decision solvers.
All fixtures are synthetic and provider-free.
"""

from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
from itertools import product
import json
import unittest

from hcl.kernel.types import HCLFailure, Issue, thaw
from hcl.memory import codec
from hcl.semantics.joint_change_compiler import JointChangeCompiler
from hcl.semantics.segments import segment_snapshot
from scripts.witness_unified_concept_judgment import propose, term, SCENE, PRINCIPLES
from tests import test_unified_s4_judgment as fixture


def edit_identity(edit):
    if edit["kind"] == "CHOICE_REPLACE":
        return (edit["kind"], edit["choice_id"], edit["version_id"])
    return tuple(edit[key] for key in
                 ("kind", "source_id", "model_id", "argument_id", "item_id"))


def canonical_edits(candidate):
    baseline = candidate["joint_changes"]["baseline"]
    return {edit_identity(row): row for row in candidate["joint_changes"]["edits"]
            if row["kind"] != "CHOICE_REPLACE"
            or row["version_id"] != baseline[row["choice_id"]]}


def full_assignments(candidate):
    """Independent exhaustive terminal-state enumeration with unit edit costs."""
    request = candidate["joint_changes"]
    atoms = canonical_edits(candidate)
    choices = sorted(request["baseline"])
    options = {choice: {request["baseline"][choice]} for choice in choices}
    withdrawals = []
    for identity, edit in atoms.items():
        if edit["kind"] == "CHOICE_REPLACE":
            options[edit["choice_id"]].add(edit["version_id"])
        else:
            withdrawals.append(identity)
    for values in product(*(sorted(options[key]) for key in choices)):
        selected = dict(zip(choices, values))
        if any([selected[row["left"]], selected[row["right"]]] not in row["allowed_pairs"]
               for row in candidate["concepts"]["constraints"]):
            continue
        replacements = {("CHOICE_REPLACE", key, value) for key, value in selected.items()
                        if value != request["baseline"][key]}
        for flags in product((False, True), repeat=len(withdrawals)):
            retracted = {key for key, active in zip(withdrawals, flags) if active}
            yield frozenset(replacements | retracted), selected, retracted


def ground_tree(value):
    return (value["sort"], value["symbol"],
            tuple(ground_tree(child) for child in value["arguments"]))


def reference_pattern(examples):
    """An independent small first-order generalizer with correlated variables."""
    variables = {}

    def descend(column):
        if len(set(column)) == 1:
            return ("node", column[0][0], column[0][1],
                    tuple(descend(tuple(child for _ in column)) for child in column[0][2]))
        if len({(row[0], row[1], len(row[2])) for row in column}) == 1:
            return ("node", column[0][0], column[0][1],
                    tuple(descend(tuple(row[2][i] for row in column))
                          for i in range(len(column[0][2]))))
        assert len({row[0] for row in column}) == 1
        return ("variable", column[0][0], variables.setdefault(column, len(variables)))

    return descend(tuple(ground_tree(row["term"]) for row in examples))


def reference_match(pattern, value):
    substitutions = {}

    def visit(expected, actual):
        if expected[1] != actual[0]:
            return False
        if expected[0] == "variable":
            key = expected[2]
            return substitutions.setdefault(key, actual) == actual
        return (expected[2] == actual[1] and len(expected[3]) == len(actual[2])
                and all(visit(a, b) for a, b in zip(expected[3], actual[2])))

    return visit(pattern, ground_tree(value))


def reference_classifications(candidate, selected):
    """Truth, falsity or unknown; never read a production classification result."""
    concepts = candidate["concepts"]
    versions = {row["id"]: row for row in concepts["versions"]}
    cases = {row["id"]: row for row in concepts["cases"]}
    results = {}
    for use in concepts["uses"]:
        selector = use["selector"]
        version = versions[selector["id"] if selector["kind"] == "PINNED"
                           else selected[selector["id"]]]
        case = cases[use["case_id"]]
        positive = negative = False
        uncertain = (case["term"] is None
                     or bool(set(case["assumptions"]) - set(case["active_assumptions"])))
        active = set(version["active_assumptions"])
        uncertain |= bool(set(version["assumptions"]) - active)
        for criterion in version["criteria"]:
            examples = [row for row in criterion["positive"] if set(row["assumptions"]) <= active]
            if (not examples or not set(criterion["assumptions"]) <= active
                    or any(not set(row["assumptions"]) <= active
                           for key in ("positive", "negative", "boundary") for row in criterion[key])):
                uncertain = True
                continue
            pattern = reference_pattern(examples)
            direction = criterion["direction"]
            if direction in ("SUFFICIENT", "BICONDITIONAL"):
                uncertain |= any(reference_match(pattern, row["term"]) for row in criterion["negative"])
            if case["term"] is None:
                continue
            matched = reference_match(pattern, case["term"])
            positive |= matched and direction in ("SUFFICIENT", "BICONDITIONAL")
            negative |= not matched and direction in ("NECESSARY", "BICONDITIONAL")
            uncertain |= any(row["term"] == case["term"] for row in criterion["boundary"])
        results[use["id"]] = (None if uncertain or positive == negative else positive)
    return results


def complete_labellings(nodes, edges):
    """Brute force Caminada labellings, independent of grounded iteration."""
    nodes = tuple(nodes)
    incoming = {node: {left for left, right in edges if right == node} for node in nodes}
    forced = {node: "IN" for node in nodes if not incoming[node]}
    remaining = [node for node in nodes if node not in forced]
    assert len(remaining) <= 12, "keep the independent exhaustive oracle genuinely small"
    labellings = []
    for values in product(("IN", "OUT", "UNDEC"), repeat=len(remaining)):
        labelling = dict(forced)
        labelling.update(zip(remaining, values))
        if all(labelling[node] == (
            "OUT" if any(labelling[other] == "IN" for other in incoming[node]) else
            "IN" if all(labelling[other] == "OUT" for other in incoming[node]) else "UNDEC")
               for node in nodes):
            labellings.append(labelling)
    assert labellings
    extensions = {frozenset(node for node, label in row.items() if label == "IN")
                  for row in labellings}
    grounded = set.intersection(*(set(row) for row in extensions))
    preferred = {row for row in extensions if not any(row < other for other in extensions)}
    return grounded, preferred


def reference_arguments(model, classifications, retractions):
    """Construct tiny source proof trees, then solve their defeat graph by labels."""
    source = model["argument"]
    scope = (model["mental"]["source_id"], model["mental"]["id"], source["id"])
    disabled = {(row[0], row[-1]) for row in retractions if row[1:4] == scope}
    literals = {row["id"]: (row["kind"], row["atom"], row["negative"])
                for row in source["literals"]}
    bound = {row["premise_id"]: (classifications[row["use_id"]], row["expected"])
             for row in model["concept_bindings"]}
    # The synthetic fixture explicitly establishes knowledge, opportunity and
    # breached commitment; their actual M03/M05/M07 results are checked below.
    bound.update({row["premise_id"]: (True, row["expected"]) for row in model["fact_bindings"]})
    premises = [row for row in source["premises"]
                if ("PREMISE_RETRACT", row["id"]) not in disabled
                and set(row["assumptions"]) <= set(source["active_assumptions"])
                and (row["id"] not in bound or bound[row["id"]][0] is bound[row["id"]][1])]
    rules = [row for row in source["rules"] if ("RULE_RETRACT", row["id"]) not in disabled
             and set(row["assumptions"]) <= set(source["active_assumptions"])]
    proofs = {}

    def derive(literal, ancestry=()):
        if literal in ancestry:
            return []
        found = []
        for premise in premises:
            if literals[premise["literal"]] == literal:
                key = (premise["id"], ())
                proofs[key] = dict(conclusion=literal, top=premise["id"],
                    vulnerable=premise["ordinary"], subs={key},
                    bases={premise["id"]} if premise["ordinary"] else set())
                found.append(key)
        for rule in rules:
            if literals[rule["conclusion"]] != literal:
                continue
            children = [derive(literals[key], ancestry + (literal,)) for key in rule["premises"]]
            for support in product(*children):
                key = (rule["id"], support)
                proofs[key] = dict(conclusion=literal, top=rule["id"],
                    vulnerable=not rule["strict"],
                    subs={key}.union(*(proofs[child]["subs"] for child in support)),
                    bases=({rule["id"]} if not rule["strict"] else
                           set().union(*(proofs[child]["bases"] for child in support))))
                found.append(key)
        return found

    for literal in literals.values():
        derive(literal)
    priorities = {(row["better"], row["worse"]) for row in source["priorities"]}
    while True:
        closure = priorities | {(a, d) for a, b in priorities for c, d in priorities if b == c}
        if closure == priorities:
            break
        priorities = closure
    edges = set()
    for left, attacker in proofs.items():
        for right, target in proofs.items():
            for subkey in target["subs"]:
                sub = proofs[subkey]
                a, b = attacker["conclusion"], sub["conclusion"]
                contrary = a[:2] == b[:2] and a[2] != b[2]
                blocked = (bool(sub["bases"] and attacker["bases"])
                           and all((better, worse) in priorities
                                   for better in sub["bases"] for worse in attacker["bases"]))
                if contrary and sub["vulnerable"] and not blocked:
                    edges.add((left, right))
    grounded, preferred = complete_labellings(proofs, edges)
    unknown = {literals[row["literal"]][:2] for row in source["premises"]
               if row["id"] in bound and bound[row["id"]][0] is None
               and ("PREMISE_RETRACT", row["id"]) not in disabled}
    while True:
        closure = unknown | {literals[row["conclusion"]][:2] for row in rules
                             if any(literals[key][:2] in unknown for key in row["premises"])}
        if closure == unknown:
            break
        unknown = closure

    def pair(literal, extension):
        accepted = {proofs[key]["conclusion"] for key in extension}
        opposite = literal[:2] + (not literal[2],)
        return (literal in accepted, opposite in accepted)

    queries = {}
    for row in source["queries"]:
        literal = literals[row["literal"]]
        supported = pair(literal, proofs)
        accepted = pair(literal, grounded)
        queries[row["id"]] = dict(
            positive_supported=supported[0], opposed_supported=supported[1],
            positive_accepted=accepted[0], opposed_accepted=accepted[1],
            preferred_acceptance=sorted({pair(literal, extension) for extension in preferred}),
            resolved=literal[:2] not in unknown,
            joint_pairs={extension: pair(literal, extension) for extension in preferred})
    return queries


def reference_decision(model, queries):
    """Independent exact single-state, weighted decision oracle for these fixtures."""
    decision = model["decisions"][0]
    plan = next(row for row in model["mental"]["plans"] if row["id"] == decision["plan_id"])
    states, recommendations = [], []
    resolved = True
    for framework in decision["frameworks"]:
        def norm_state(norm, extension=None):
            query = queries[norm["argument_query_id"]] if norm["argument_query_id"] else None
            if query is None:
                return "ACTIVE"
            if not query["resolved"]:
                return "UNRESOLVED"
            positive, opposed = ((query["positive_accepted"], query["opposed_accepted"])
                                 if extension is None else query["joint_pairs"][extension])
            return "ACTIVE" if positive and not opposed else "REJECTED" if opposed and not positive else "UNRESOLVED"

        initial = {norm["id"]: norm_state(norm) for norm in framework["norms"]}
        resolved &= all(queries[norm["argument_query_id"]]["resolved"]
                        for norm in framework["norms"] if norm["argument_query_id"])
        extensions = [None]
        if "UNRESOLVED" in initial.values():
            extensions = list(next(iter(queries.values()))["joint_pairs"])
        branches, winners = set(), []
        for extension in extensions:
            norm_states = {norm["id"]: norm_state(norm, extension) for norm in framework["norms"]}
            permissions, scores = [], {}
            for action in plan["graph"]["actions"]:
                forbidden = sorted(norm["id"] for norm in framework["norms"]
                    if norm_states[norm["id"]] == "ACTIVE" and action["id"] not in norm["permitted_actions"])
                unresolved = sorted(norm["id"] for norm in framework["norms"]
                    if norm_states[norm["id"]] == "UNRESOLVED" and action["id"] not in norm["permitted_actions"])
                feasible = "risk" in action["enabled"] and "risk" in action["feasible"]
                status = ("INFEASIBLE" if not feasible else "PROHIBITED" if forbidden else
                          "PERMISSION_UNRESOLVED" if unresolved else "PERMITTED_IN_DECLARED_FRAMEWORK")
                permissions.append((action["id"], status, tuple(forbidden), tuple(unresolved)))
                if status == "PERMITTED_IN_DECLARED_FRAMEWORK":
                    end = action["transitions"]["risk"]
                    scores[action["id"]] = sum(
                        Fraction(framework["weights"][dimension["id"]]) *
                        (Fraction(dimension["state_values"][end]) -
                         Fraction(dimension["action_costs"][action["id"]]))
                        for dimension in decision["dimensions"])
            best = max(scores.values(), default=None)
            recommended = frozenset(action for action, score in scores.items() if score == best)
            winners.append(set(recommended))
            branches.add((tuple(sorted(norm_states.items())), tuple(sorted(permissions))))
        states.append(frozenset(branches))
        recommendations.append(set.intersection(*winners))
    return dict(recommended=tuple(sorted(set.intersection(*recommendations))),
                joint_branches=tuple(states), resolved=resolved)


def reference_target(candidate, selected, retractions):
    target = candidate["joint_changes"]["target"]
    model = next(row for row in candidate["models"]
                 if (row["mental"]["source_id"], row["mental"]["id"]) ==
                 (target["source_id"], target["model_id"]))
    classifications = reference_classifications(candidate, selected)
    queries = reference_arguments(model, classifications, retractions)
    if target["kind"] == "M13_ACCEPTANCE":
        result = dict(queries[target["query_id"]])
        result.pop("joint_pairs")
        return result
    return reference_decision(model, queries)


def reference_search(candidate):
    baseline = reference_target(candidate, candidate["joint_changes"]["baseline"], set())
    rows = {edits: reference_target(candidate, selected, retractions)
            for edits, selected, retractions in full_assignments(candidate)}
    wins = {edits for edits, value in rows.items()
            if edits and baseline["resolved"] and value["resolved"] and value != baseline}
    minimum = min(map(len, wins), default=None)
    unknown = any(not value["resolved"] and (minimum is None or len(edits) <= minimum)
                  for edits, value in rows.items())
    return dict(baseline=baseline, rows=rows, complete=not unknown,
                minimum=None if unknown else minimum,
                witnesses=set() if unknown else {edits for edits in wins if len(edits) == minimum},
                candidates=wins)


class IndependentJointOracleUnitTests(unittest.TestCase):
    def test_complete_labellings_distinguish_grounded_and_joint_preferred(self):
        grounded, preferred = complete_labellings(("a", "b", "c"), {("a", "b"), ("b", "a")})
        self.assertEqual(grounded, {"c"})
        self.assertEqual(preferred, {frozenset(("a", "c")), frozenset(("b", "c"))})
        self.assertEqual(complete_labellings(("a",), {("a", "a")}), (set(), {frozenset()}))

    def test_reference_pattern_keeps_repeated_variable_constraint(self):
        examples = [{"term": term("pair", term(x), term(x))} for x in ("a", "b")]
        pattern = reference_pattern(examples)
        self.assertTrue(reference_match(pattern, term("pair", term("fresh"), term("fresh"))))
        self.assertFalse(reference_match(pattern, term("pair", term("fresh"), term("other"))))


class JointChangeOracleContracts(unittest.TestCase):
    def setUp(self):
        self.f = fixture.JudgmentExecutionTests()
        self.f.setUp()
        self.addCleanup(self.f.tearDown)
        handles = (self.f.store.put_source("s", self.f.owner, "scene", SCENE),
                   self.f.store.put_source("s", self.f.owner, "principles", PRINCIPLES))
        self.snapshot = self.f.store.snapshot("s", self.f.owner, handles)
        self.allowance = replace(self.f.request.budget, max_local_evaluations=1000000)

    def candidate(self, kind="M13_ACCEPTANCE"):
        candidate = propose(self.snapshot, self.f.request.question)
        candidate["schema"] = "hcl-judgment-candidates-4"
        target = dict(kind=kind, source_id="scene", model_id="notice")
        target.update(dict(argument_id="norms", query_id="duty") if kind == "M13_ACCEPTANCE"
                      else dict(decision_id="notification"))
        candidate["joint_changes"] = dict(baseline=dict(meaning="revised"), target=target, edits=[])
        candidate["models"][0]["decisions"][0]["responsibility_queries"] = []
        argument = candidate["models"][0]["argument"]
        # Keep exhaustive labelling and production preferred-set searches tiny;
        # responsibility is not the target of this finite oracle contract.
        argument["rules"] = [row for row in argument["rules"] if row["id"] != "responsibility"]
        argument["queries"] = [row for row in argument["queries"] if row["id"] != "responsibility"]
        for query in argument["queries"]:
            query["preferred"] = True
        return candidate

    def choice(self, candidate, version="original", choice="meaning"):
        row = next(row for row in candidate["concepts"]["choices"] if row["id"] == choice)
        return dict(kind="CHOICE_REPLACE", choice_id=choice, version_id=version,
                    segment_ids=list(row["segment_ids"]))

    def retract(self, candidate, item="backup", kind="RULE_RETRACT", model_index=0):
        model = candidate["models"][model_index]
        row = next(row for row in model["argument"]["rules" if kind == "RULE_RETRACT" else "premises"]
                   if row["id"] == item)
        return dict(kind=kind, source_id=model["mental"]["source_id"], model_id=model["mental"]["id"],
                    argument_id=model["argument"]["id"], item_id=item, segment_ids=list(row["segment_ids"]))

    def backup(self, candidate, name="backup"):
        argument = candidate["models"][0]["argument"]
        row = deepcopy(argument["rules"][0])
        row.update(id=name, premises=["known"])
        argument["rules"].append(row)
        argument["priorities"].append(dict(better=name, worse="liberty", segment_ids=row["segment_ids"]))

    def second_family(self, candidate):
        concepts = candidate["concepts"]
        for old in list(concepts["versions"]):
            row = deepcopy(old)
            row.update(id="credential-" + old["id"], concept_key="verified-credential",
                       scope="credential-evidence", purpose="Classify the independent credential relation.")
            for criterion in row["criteria"]:
                for example in criterion["positive"]:
                    example["term"]["symbol"] = "credential"
            concepts["versions"].append(row)
        case = deepcopy(concepts["cases"][0])
        case["id"] = "new-credential"
        case["term"]["symbol"] = "credential"
        concepts["cases"].append(case)
        use = deepcopy(concepts["uses"][0])
        use.update(id="credential-use", concept_key="verified-credential", scope="credential-evidence",
                   case_id=case["id"], selector=dict(kind="CHOICE", id="credential"))
        concepts["uses"].append(use)
        concepts["choices"].append(dict(id="credential", versions=["credential-original", "credential-revised"],
                                         segment_ids=list(concepts["choices"][0]["segment_ids"])))
        model = candidate["models"][0]
        argument = model["argument"]
        refs = list(concepts["choices"][0]["segment_ids"])
        argument["literals"].append(dict(id="credential-category", atom="credential-category", negative=False,
                                           kind="CLAIM", segment_ids=refs))
        argument["premises"].append(dict(id="fact-credential", literal="credential-category", ordinary=False,
                                           assumptions=[], segment_ids=refs))
        argument["rules"].append(dict(id="credential-duty", premises=["known", "credential-category"],
                                       conclusion="duty", strict=False, assumptions=[], segment_ids=refs))
        argument["priorities"].append(dict(better="credential-duty", worse="liberty", segment_ids=refs))
        model["concept_bindings"].append(dict(premise_id="fact-credential", use_id="credential-use",
                                                expected=True, segment_ids=refs))
        candidate["joint_changes"]["baseline"]["credential"] = "credential-revised"

    def compile(self, candidate):
        return JointChangeCompiler().compile(self.snapshot, segment_snapshot(self.snapshot, self.f.request.question),
                                              json.dumps(candidate, ensure_ascii=False), self.allowance)

    def execute(self, candidate, allowance=None):
        from hcl.operators.joint_changes import JointChangeOperator
        operation = JointChangeOperator().run(self.snapshot, Issue("oracle", "judgment.evaluate"),
                                               allowance or self.allowance, self.compile(candidate))
        inference = operation.candidate_delta.new_inferences[0]
        self.assertEqual(inference.kind, "CONDITIONAL_JOINT_CHANGE_JUDGMENT")
        return thaw(inference.values)

    def actual_edits(self, values, row):
        atoms = {atom["atom_id"]: edit_identity(atom["edit"])
                 for atom in values["program"]["joint_changes"]["atoms"]}
        return frozenset(atoms[key] for key in row["atom_ids"])

    def assert_evaluation(self, candidate, row, expected):
        target = row["target"]
        self.assertEqual(target["resolved"], expected["resolved"])
        selected = candidate["joint_changes"]["target"]
        if selected["kind"] == "M13_ACCEPTANCE":
            for key in ("positive_supported", "opposed_supported", "positive_accepted", "opposed_accepted"):
                self.assertEqual(target["semantics"][key], expected[key], (key, row["atom_ids"]))
            self.assertEqual([tuple(pair) for pair in target["semantics"]["preferred_acceptance"]],
                             expected["preferred_acceptance"])
            return
        model = next(model for model in row["actual_judgment"]["models"]
                     if (model["source_id"], model["model_id"]) == (selected["source_id"], selected["model_id"]))
        decision = next(row for row in model["decisions"] if row["decision_id"] == selected["decision_id"])
        self.assertEqual(tuple(decision["robust_across_frameworks"]), expected["recommended"])
        self.assertEqual(tuple(target["semantics"]["recommended"]), expected["recommended"])
        branches = []
        for framework in decision["frameworks"]:
            branches.append(frozenset((tuple(sorted(branch["states"].items())), tuple(sorted(
                (item["action_id"], item["status"], tuple(sorted(item["prohibiting_norms"])),
                 tuple(sorted(item["unresolved_norms"]))) for item in branch["result"]["eligibility"])))
                for branch in framework["branches"]))
        self.assertEqual(tuple(branches), expected["joint_branches"])

    def assert_oracle(self, candidate):
        original = deepcopy(candidate)
        expected = reference_search(candidate)
        values = self.execute(candidate)
        self.assertEqual(candidate, original)
        search = values["joint_search"]
        self.assertEqual(search["complete"], expected["complete"])
        self.assertEqual(search["minimum_cardinality"], expected["minimum"])
        self.assertEqual({self.actual_edits(values, row) for row in search["minimum_witnesses"]},
                         expected["witnesses"])
        checked = {self.actual_edits(values, row): row for row in values["evaluations"]}
        self.assertIn(frozenset(), checked)
        self.assertEqual(search["baseline"], checked[frozenset()]["target"])
        for edits, row in checked.items():
            self.assertIn(edits, expected["rows"])
            self.assert_evaluation(candidate, row, expected["rows"][edits])
            self.assertEqual(len(edits), len(row["atom_ids"]))
        if expected["complete"]:
            required = {edits for edits in expected["rows"]
                        if expected["minimum"] is None or len(edits) <= expected["minimum"]}
            self.assertTrue(required <= set(checked), "minimum must cover every smaller layer and every tie")
        for row in search["minimum_witnesses"] + search["candidate_witnesses"]:
            edits = self.actual_edits(values, row)
            self.assertIn(edits, expected["candidates"])
            self.assertEqual(row["cardinality"], len(edits))
            self.assertEqual(row["evaluation_id"], checked[edits]["evaluation_id"])
        return values, expected

    def test_concept_and_independent_support_withdrawal_are_jointly_necessary(self):
        for kind in ("M13_ACCEPTANCE", "M14_DECISION"):
            with self.subTest(kind=kind):
                candidate = self.candidate(kind)
                self.backup(candidate)
                candidate["joint_changes"]["edits"] = [self.choice(candidate), self.retract(candidate)]
                values, oracle = self.assert_oracle(candidate)
                self.assertEqual(oracle["minimum"], 2)
                baseline = oracle["baseline"]
                self.assertTrue(all(value == baseline for edits, value in oracle["rows"].items() if len(edits) == 1))
                self.assertEqual(len(values["joint_search"]["minimum_witnesses"]), 1)

    def test_two_genuinely_different_concept_families_are_jointly_necessary(self):
        for kind in ("M13_ACCEPTANCE", "M14_DECISION"):
            with self.subTest(kind=kind):
                candidate = self.candidate(kind)
                self.second_family(candidate)
                candidate["joint_changes"]["edits"] = [self.choice(candidate),
                    self.choice(candidate, "credential-original", "credential")]
                _, oracle = self.assert_oracle(candidate)
                self.assertEqual(oracle["minimum"], 2)
                self.assertEqual(len({row["concept_key"] for row in candidate["concepts"]["versions"]}), 2)

    def test_interlocked_choices_are_evaluated_at_legal_terminals(self):
        candidate = self.candidate("M14_DECISION")
        self.second_family(candidate)
        candidate["concepts"]["constraints"] = [dict(left="meaning", right="credential", allowed_pairs=[
            ["revised", "credential-revised"], ["original", "credential-original"]],
            segment_ids=candidate["concepts"]["choices"][0]["segment_ids"])]
        candidate["joint_changes"]["edits"] = [self.choice(candidate),
            self.choice(candidate, "credential-original", "credential")]
        values, oracle = self.assert_oracle(candidate)
        self.assertEqual(oracle["minimum"], 2)
        self.assertEqual(sorted(map(len, oracle["rows"])), [0, 2])
        self.assertEqual(sorted(len(row["atom_ids"]) for row in values["evaluations"]), [0, 2])

    def test_all_minimum_ties_include_rule_premise_and_selector_changes(self):
        for kind in ("M13_ACCEPTANCE", "M14_DECISION"):
            with self.subTest(kind=kind):
                candidate = self.candidate(kind)
                candidate["joint_changes"]["edits"] = [self.choice(candidate),
                    self.retract(candidate, "care-duty"), self.retract(candidate, "fact-current-category", "PREMISE_RETRACT")]
                _, oracle = self.assert_oracle(candidate)
                self.assertEqual(oracle["minimum"], 1)
                self.assertEqual(len(oracle["witnesses"]), 3)

    def test_duplicate_support_requires_each_independent_activation_withdrawal(self):
        candidate = self.candidate()
        self.backup(candidate)
        self.backup(candidate, "another-backup")
        candidate["joint_changes"]["edits"] = [self.choice(candidate), self.retract(candidate),
            self.retract(candidate, "another-backup")]
        _, oracle = self.assert_oracle(candidate)
        self.assertEqual(oracle["minimum"], 3)

    def test_edit_and_source_row_permutations_and_duplicate_atoms_preserve_all_ties(self):
        candidate = self.candidate()
        candidate["joint_changes"]["edits"] = [self.choice(candidate), self.retract(candidate, "care-duty"),
            self.retract(candidate, "fact-current-category", "PREMISE_RETRACT")]
        first, oracle = self.assert_oracle(candidate)
        alternate = deepcopy(candidate)
        alternate["joint_changes"]["edits"] = list(reversed(candidate["joint_changes"]["edits"])) * 2
        alternate["joint_changes"]["edits"].append(self.choice(candidate, "revised"))
        for key in ("literals", "premises", "rules", "priorities", "queries"):
            alternate["models"][0]["argument"][key].reverse()
        for version in alternate["concepts"]["versions"]:
            for criterion in version["criteria"]:
                criterion["positive"].reverse()
        second, other = self.assert_oracle(alternate)
        self.assertEqual(other["witnesses"], oracle["witnesses"])
        self.assertEqual(len(second["program"]["joint_changes"]["atoms"]), 3)
        self.assertEqual(len(second["program"]["joint_changes"]["ignored_edits"]), 1)
        self.assertEqual({row["atom_id"] for row in first["program"]["joint_changes"]["atoms"]},
                         {row["atom_id"] for row in second["program"]["joint_changes"]["atoms"]})

    def test_no_solution_exhausts_every_legal_assignment_and_scoped_retraction(self):
        candidate = self.candidate()
        candidate["joint_changes"]["target"]["query_id"] = "meeting"
        candidate["joint_changes"]["baseline"]["meaning"] = "original"
        candidate["joint_changes"]["edits"] = [self.choice(candidate, "revised"),
            self.retract(candidate, "fact-current-category", "PREMISE_RETRACT")]
        values, oracle = self.assert_oracle(candidate)
        self.assertIsNone(oracle["minimum"])
        self.assertEqual(len(values["evaluations"]), 4)
        # The joint activation retraction cancels the concept's newly available
        # proof. It must not be dropped merely because it is a baseline no-op.
        rows = {self.actual_edits(values, row): row for row in values["evaluations"]}
        both = next(row for edits, row in rows.items() if len(edits) == 2)
        argument = both["actual_judgment"]["models"][0]["actual_argument"]["values"]["models"][0]
        duty = next(row for row in argument["queries"] if row["query_id"] == "duty")
        self.assertFalse(duty["positive_accepted"])
        self.assertTrue(duty["opposed_accepted"])

    def test_semantically_redundant_version_is_not_a_target_change(self):
        candidate = self.candidate()
        duplicate = deepcopy(candidate["concepts"]["versions"][1])
        duplicate["id"] = "revised-alias"
        duplicate["purpose"] = "A separately declared purpose retaining this case's exact classification."
        candidate["concepts"]["versions"].append(duplicate)
        candidate["concepts"]["choices"][0]["versions"].append(duplicate["id"])
        candidate["joint_changes"]["edits"] = [self.choice(candidate, duplicate["id"])]
        values, oracle = self.assert_oracle(candidate)
        self.assertIsNone(oracle["minimum"])
        self.assertEqual(len(values["evaluations"]), 2)
        before, after = sorted(values["evaluations"], key=lambda row: len(row["atom_ids"]))
        self.assertNotEqual(before["classifications"]["current"]["definition_version"],
                            after["classifications"]["current"]["definition_version"])
        self.assertNotEqual(before["actual_judgment"]["models"][0]["actual_argument"]["result_id"],
                            after["actual_judgment"]["models"][0]["actual_argument"]["result_id"])

    def test_m13_support_change_counts_even_when_acceptance_and_recommendation_do_not(self):
        candidate = self.candidate()
        candidate["models"][0]["argument"]["priorities"][0].update(better="liberty", worse="care-duty")
        candidate["joint_changes"]["edits"] = [self.retract(candidate, "care-duty")]
        _, oracle = self.assert_oracle(candidate)
        self.assertEqual(oracle["minimum"], 1)
        after = next(row for edits, row in oracle["rows"].items() if edits)
        self.assertTrue(oracle["baseline"]["positive_supported"])
        self.assertFalse(after["positive_supported"])
        for key in ("positive_accepted", "opposed_accepted", "preferred_acceptance"):
            self.assertEqual(oracle["baseline"][key], after[key])

    def test_m14_joint_permissions_count_even_when_recommendation_is_identical(self):
        candidate = self.candidate("M14_DECISION")
        candidate["models"][0]["decisions"][0]["frameworks"][0]["weights"] = dict(care="3/4", convenience="1/4")
        candidate["joint_changes"]["edits"] = [self.choice(candidate)]
        _, oracle = self.assert_oracle(candidate)
        self.assertEqual(oracle["minimum"], 1)
        after = next(row for edits, row in oracle["rows"].items() if edits)
        self.assertEqual(oracle["baseline"]["recommended"], ("protect",))
        self.assertEqual(after["recommended"], ("protect",))
        self.assertNotEqual(oracle["baseline"]["joint_branches"], after["joint_branches"])

    def test_two_opposed_norms_use_joint_preferred_extensions_not_marginal_products(self):
        candidate = self.candidate("M14_DECISION")
        argument = candidate["models"][0]["argument"]
        argument["priorities"] = []
        query = deepcopy(argument["queries"][0])
        query.update(id="no-duty", literal="not-duty")
        argument["queries"].append(query)
        frame = candidate["models"][0]["decisions"][0]["frameworks"][0]
        opposing = deepcopy(frame["norms"][0])
        opposing.update(id="ignore-without-duty", label="opposed conditional permission", permitted_actions=["ignore"],
                        argument_query_id="no-duty")
        frame["norms"].append(opposing)
        candidate["joint_changes"]["edits"] = [self.choice(candidate)]
        values, oracle = self.assert_oracle(candidate)
        self.assertEqual(oracle["baseline"]["recommended"], ())
        self.assertEqual(len(oracle["baseline"]["joint_branches"][0]), 2)
        baseline = next(row for row in values["evaluations"] if not row["atom_ids"])
        branches = baseline["actual_judgment"]["models"][0]["decisions"][0]["frameworks"][0]["branches"]
        self.assertEqual({(row["states"]["protect-known-risk"], row["states"]["ignore-without-duty"])
                          for row in branches}, {("ACTIVE", "REJECTED"), ("REJECTED", "ACTIVE")})

    def test_preferred_dispute_retains_correlated_pairs_and_exact_rational_ties(self):
        candidate = self.candidate("M14_DECISION")
        candidate["models"][0]["argument"]["priorities"] = []
        frame = candidate["models"][0]["decisions"][0]["frameworks"][0]
        frame["weights"] = dict(care="4/9", convenience="5/9")
        candidate["joint_changes"]["edits"] = [self.choice(candidate)]
        values, oracle = self.assert_oracle(candidate)
        self.assertEqual(oracle["minimum"], 1)
        self.assertEqual(oracle["baseline"]["recommended"], ("protect",))
        alternative = next(value for edits, value in oracle["rows"].items() if edits)
        self.assertEqual(alternative["recommended"], ("ignore", "protect"))
        baseline = next(row for row in values["evaluations"] if not row["atom_ids"])
        self.assertEqual(len(baseline["actual_judgment"]["models"][0]["decisions"][0]["frameworks"][0]["branches"]), 2)

    def test_unknown_alternative_cannot_prove_minimum_or_erase_resolved_candidates(self):
        candidate = self.candidate()
        unknown = deepcopy(candidate["concepts"]["versions"][1])
        unknown["id"] = "unknown"
        unknown["criteria"][0]["direction"] = "TYPICAL"
        candidate["concepts"]["versions"].append(unknown)
        candidate["concepts"]["choices"][0]["versions"].append("unknown")
        candidate["joint_changes"]["edits"] = [self.choice(candidate), self.choice(candidate, "unknown")]
        values, oracle = self.assert_oracle(candidate)
        self.assertFalse(oracle["complete"])
        self.assertIsNone(values["joint_search"]["minimum_cardinality"])
        self.assertFalse(values["joint_search"]["minimum_witnesses"])
        self.assertEqual({self.actual_edits(values, row) for row in values["joint_search"]["candidate_witnesses"]},
                         oracle["candidates"])
        self.assertTrue(values["joint_search"]["frontier"])

    def test_original_negative_examples_and_pinned_commitment_remain_unchanged(self):
        candidate = self.candidate("M14_DECISION")
        original = candidate["concepts"]["versions"][0]
        negative = deepcopy(original["criteria"][0]["positive"][0])
        negative.update(id="original-negative", term=term("pair", term("negative-a"), term("negative-b")))
        original["criteria"][0]["negative"] = [negative]
        self.backup(candidate)
        candidate["joint_changes"]["edits"] = [self.choice(candidate), self.retract(candidate)]
        values, _ = self.assert_oracle(candidate)
        baseline = next(row for row in values["evaluations"] if not row["atom_ids"])
        fixed = baseline["actual_judgment"]["models"][0]
        for row in values["evaluations"]:
            actual = row["actual_judgment"]["models"][0]
            self.assertEqual(row["classifications"]["promise-scope"], baseline["classifications"]["promise-scope"])
            for field in ("cognition", "actual_interaction", "opportunities"):
                self.assertEqual(codec.dumps(actual[field]), codec.dumps(fixed[field]))
            for key in ("knowledge", "control", "promise", "concept:promise-scope"):
                self.assertEqual(codec.dumps(actual["facts"][key]), codec.dumps(fixed["facts"][key]))
            self.assertEqual(actual["facts"]["knowledge"]["possible_values"], [True])
            self.assertEqual(actual["facts"]["promise"]["possible_values"], [True])
        preserved = values["program"]["concepts"]["versions"][0]["criteria"][0]["negative"]
        self.assertEqual(preserved, [negative])

    def test_challenged_negative_example_cannot_be_repaired_by_withdrawing_argument_support(self):
        candidate = self.candidate()
        candidate["joint_changes"]["baseline"]["meaning"] = "original"
        revised = candidate["concepts"]["versions"][1]
        negative = deepcopy(revised["criteria"][0]["positive"][0])
        negative.update(id="challenge", term=deepcopy(candidate["concepts"]["cases"][0]["term"]))
        revised["criteria"][0]["negative"] = [negative]
        candidate["joint_changes"]["edits"] = [self.choice(candidate, "revised"), self.retract(candidate, "care-duty")]
        values, oracle = self.assert_oracle(candidate)
        self.assertFalse(oracle["complete"])
        self.assertEqual(values["program"]["concepts"]["versions"][1]["criteria"][0]["negative"], [negative])

    def test_retractions_do_not_leak_across_equal_argument_ids_in_distinct_models(self):
        candidate = self.candidate()
        other = deepcopy(candidate["models"][0])
        other["mental"]["id"] = "other-notice"
        candidate["models"].append(other)
        candidate["joint_changes"]["edits"] = [self.retract(candidate, "care-duty", model_index=1)]
        values, oracle = self.assert_oracle(candidate)
        self.assertIsNone(oracle["minimum"])
        self.assertEqual(len(values["evaluations"]), 2)
        before, after = sorted(values["evaluations"], key=lambda row: len(row["atom_ids"]))
        for row in (before, after):
            first = row["actual_judgment"]["models"][0]
            target = next(query for query in first["actual_argument"]["values"]["models"][0]["queries"]
                          if query["query_id"] == "duty")
            self.assertTrue(target["positive_accepted"])
        second = after["actual_judgment"]["models"][1]
        query = next(query for query in second["actual_argument"]["values"]["models"][0]["queries"]
                     if query["query_id"] == "duty")
        self.assertFalse(query["positive_accepted"])
        self.assertTrue(query["opposed_accepted"])

    def test_conflicting_replacements_never_form_a_two_edit_assignment(self):
        candidate = self.candidate()
        candidate["joint_changes"]["target"]["query_id"] = "meeting"
        alias = deepcopy(candidate["concepts"]["versions"][0])
        alias["id"] = "original-alias"
        candidate["concepts"]["versions"].append(alias)
        candidate["concepts"]["choices"][0]["versions"].append(alias["id"])
        candidate["joint_changes"]["edits"] = [self.choice(candidate), self.choice(candidate, alias["id"])]
        values, _ = self.assert_oracle(candidate)
        self.assertEqual(sorted(len(row["atom_ids"]) for row in values["evaluations"]), [0, 1, 1])

    def test_budget_frontier_never_certifies_a_minimum_or_invents_negative_search(self):
        candidate = self.candidate()
        candidate["joint_changes"]["edits"] = [self.choice(candidate), self.retract(candidate, "care-duty"),
            self.retract(candidate, "fact-current-category", "PREMISE_RETRACT")]
        full, oracle = self.assert_oracle(candidate)
        for bound in (0, 1, 100, full["local_evaluations"] - 1):
            with self.subTest(bound=bound):
                values = self.execute(candidate, replace(self.allowance, max_local_evaluations=bound))
                self.assertLessEqual(values["local_evaluations"], bound)
                self.assertFalse(values["joint_search"]["complete"])
                self.assertIsNone(values["joint_search"]["minimum_cardinality"])
                self.assertFalse(values["joint_search"]["minimum_witnesses"])
                self.assertTrue(values["joint_search"]["frontier"])
                self.assertTrue({self.actual_edits(values, row) for row in values["joint_search"]["candidate_witnesses"]}
                                <= oracle["candidates"])
                if bound == full["local_evaluations"] - 1:
                    self.assertTrue(values["joint_search"]["candidate_witnesses"])
                    self.assertFalse(values["joint_search"]["layers"][-1]["complete"])

    def test_compiler_rejects_cross_scope_and_mutable_pin_aliases(self):
        for mutation in ("scope", "argument", "pin"):
            with self.subTest(mutation=mutation):
                candidate = self.candidate()
                edit = self.retract(candidate, "care-duty")
                candidate["joint_changes"]["edits"] = [edit]
                if mutation == "scope":
                    edit["model_id"] = "absent-model"
                elif mutation == "argument":
                    edit["argument_id"] = "absent-argument"
                else:
                    candidate["concepts"]["uses"][1]["selector"] = dict(kind="CHOICE", id="meaning")
                with self.assertRaises(HCLFailure):
                    self.compile(candidate)


if __name__ == "__main__":
    unittest.main()
