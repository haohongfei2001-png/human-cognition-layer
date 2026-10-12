"""Bounded message games and social transitions under explicit local models.

No counts of epistemic worlds become probabilities. Receipt, interpretation,
acceptance, acknowledgment and verified model outcomes have separate inputs.
"""

from fractions import Fraction
from math import exp, isfinite

from hcl.operators.agency import rational
from hcl.operators.epistemic import EventModel

VERSION = "s3-finite-interaction-1"


def interpreted_event(event, readings, agents):
    """Private recipient-specific content updates the same M03 event product."""
    accepted = (
        set(event["trusted_by"])
        & set(event["understood_by"])
        & set(event["received_by"])
    )
    by_actor = {r["actor"]: r for r in readings}
    variants = {"actual": {"pre": True, "post": {}}, "skip": {"pre": True, "post": {}}}
    accepted_variants = {}
    for actor in sorted(accepted):
        row = by_actor.get(actor)
        accepted_variants[actor] = []
        # Preserve every declared reading as an alternative. Retaining the old
        # belief alone would silently discard conflicting new interpretations.
        for index, content in enumerate(row["contents"] if row is not None else ()):
            key = "accepted:" + actor + ":" + str(index)
            variants[key] = {"pre": True, "post": dict(content)}
            accepted_variants[actor].append(key)
    relations = {}
    for actor in agents:
        own = tuple(accepted_variants.get(actor, ()))
        relations[actor] = {
            key: own if own and key in ("actual", *own) else ("skip",)
            for key in variants
        }
    return EventModel(
        event["id"], variants, relations, ("actual",), tuple(event["assumptions"])
    )


def _softmax(values, beta):
    if not values:
        return {}
    logits = {key: beta * float(value) for key, value in values.items()}
    if not all(isfinite(value) for value in logits.values()):
        raise ValueError("finite model utilities required")
    offset = max(logits.values())
    weights = {key: exp(value - offset) for key, value in logits.items()}
    total = sum(weights.values())
    return {key: value / total for key, value in weights.items()}


def _condition(weights, support):
    selected = {
        key: value for key, value in weights.items() if key in support and value > 0
    }
    total = sum(selected.values())
    return {key: value / total for key, value in selected.items()} if total else {}


def message_game(
    states, messages, prior, *, beta, depth, max_work=100000, available_states=None
):
    """L0 literal conditioning -> bounded cooperative S/L recursion.

    The generative speaker in this *declared listener hypothesis* knows its
    state and maximizes identification probability minus cost. Actual speaker
    choices must separately use its computed perspective, including false
    beliefs. These are conditional model distributions, not human estimates.
    """
    if not states or len(states) > 32 or len(set(states)) != len(states):
        raise ValueError("finite unique states required")
    if not 1 <= len(messages) <= 16 or len({m["id"] for m in messages}) != len(
        messages
    ):
        raise ValueError("finite unique messages required")
    if (
        type(depth) is not int
        or not 0 <= depth <= 4
        or type(max_work) is not int
        or not 0 <= max_work <= 1000000
    ):
        raise ValueError("bounded recursive work required")
    b = float(rational(beta))
    if not 0 <= b <= 100:
        raise ValueError("bounded declared rationality required")
    for message in messages:
        if not set(message["meaning"]) <= set(states) or rational(message["cost"]) < 0:
            raise ValueError("declared literal extension and cost required")
    available = set(states) if available_states is None else set(available_states)
    if not available <= set(states):
        raise ValueError("undeclared conditioning states")
    if prior is None:
        return dict(
            status="PRIOR_UNSPECIFIED",
            literal_sets={
                m["id"]: tuple(sorted(available & set(m["meaning"]))) for m in messages
            },
            listener={},
            speaker={},
            levels=(),
            work=0,
            frontier=("NO_PROBABILITIES_FROM_WORLD_COUNTS",),
            calibration="DECLARED_MODEL_NOT_HUMAN_CALIBRATION",
        )
    if set(prior) != set(states):
        raise ValueError("prior over exact declared states required")
    weights = {key: rational(value) for key, value in prior.items()}
    if any(value < 0 for value in weights.values()) or sum(weights.values()) != 1:
        raise ValueError("normalized nonnegative declared prior required")
    weights = {key: float(value) for key, value in weights.items()}
    weights = _condition(weights, available)
    if not weights:
        return dict(
            status="INCONSISTENT_PRIOR_VIEW",
            listener={},
            speaker={},
            levels=(),
            work=0,
            frontier=(),
            calibration="DECLARED_MODEL_NOT_HUMAN_CALIBRATION",
        )
    work = 0

    def step(amount=1):
        nonlocal work
        if work + amount > max_work:
            raise OverflowError("MESSAGE_GAME_FRONTIER")
        work += amount

    levels, listener, speaker = [], {}, {}
    try:
        for message in messages:
            step(len(states))
            listener[message["id"]] = _condition(weights, set(message["meaning"]))
        levels.append(dict(depth=0, listener=listener, speaker={}))
        for level in range(1, depth + 1):
            speaker = {}
            for state in states:
                utilities = {}
                for message in messages:
                    step()
                    if state in message["meaning"] and listener[message["id"]]:
                        utilities[message["id"]] = listener[message["id"]].get(
                            state, 0
                        ) - float(rational(message["cost"]))
                speaker[state] = _softmax(utilities, b)
            updated = {}
            for message in messages:
                step(len(states))
                likelihood = {
                    state: weights.get(state, 0) * speaker[state].get(message["id"], 0)
                    for state in states
                }
                updated[message["id"]] = _condition(likelihood, set(states))
            listener = updated
            levels.append(dict(depth=level, listener=listener, speaker=speaker))
        status, frontier = "COMPUTED", ()
    except OverflowError:
        status, frontier = "FRONTIER_UNEXPLORED", ("MESSAGE_GAME_FRONTIER",)
        listener, speaker = {}, {}
    return dict(
        status=status,
        listener=listener,
        speaker=speaker,
        levels=tuple(levels),
        work=work,
        frontier=frontier,
        calibration="DECLARED_MODEL_NOT_HUMAN_CALIBRATION",
        generative_assumption="COOPERATIVE_FULL_STATE_INFORMATION_IDENTIFICATION",
    )


def listener_actions(posterior, state_q, beta):
    """Consume actual M05 one-step state Qs, never supplied action scores."""
    if not posterior:
        return dict(
            status="INCONSISTENT_OR_UNSPECIFIED_BELIEF",
            q={},
            policy={},
            best_actions=(),
        )
    if any(state not in state_q for state in posterior):
        raise ValueError("actual state computations missing")
    actions = set.intersection(*(set(state_q[state]) for state in posterior))
    if not actions:
        return dict(
            status="NO_COMMON_AVAILABLE_ACTION", q={}, policy={}, best_actions=()
        )
    q = {
        action: sum(
            weight * float(Fraction(state_q[state][action]))
            for state, weight in posterior.items()
        )
        for action in sorted(actions)
    }
    b = float(rational(beta))
    if not 0 <= b <= 100:
        raise ValueError("bounded declared listener rationality required")
    return dict(
        status="COMPUTED",
        q=q,
        policy=_softmax(q, b),
        best_actions=tuple(
            sorted(action for action, value in q.items() if value == max(q.values()))
        ),
        scope="ONE_STEP_M05_Q_UNDER_DECLARED_MESSAGE_POSTERIOR",
    )


def speaker_choices(
    speaker_states,
    state_weights,
    messages,
    predictions,
    *,
    goal,
    utilities,
    beta,
    sincere
):
    """Predict from the speaker's own view, never substitute actual world truth."""
    if not speaker_states:
        return dict(
            status="INCONSISTENT_SPEAKER_VIEW", utilities={}, policy={}, frontier=()
        )
    if state_weights is None:
        if len(speaker_states) != 1:
            return dict(
                status="SPEAKER_PRIOR_UNSPECIFIED",
                utilities={},
                policy={},
                frontier=("SPEAKER_PRIOR_UNSPECIFIED",),
            )
        weights = {speaker_states[0]: 1.0}
    else:
        parsed = {state: rational(value) for state, value in state_weights.items()}
        if any(v < 0 for v in parsed.values()) or sum(parsed.values()) != 1:
            raise ValueError("declared speaker prior required")
        weights = _condition(
            {key: float(value) for key, value in parsed.items()}, set(speaker_states)
        )
        if not weights:
            return dict(
                status="INCONSISTENT_SPEAKER_PRIOR",
                utilities={},
                policy={},
                frontier=(),
            )
    b = float(rational(beta))
    if (
        not 0 <= b <= 100
        or type(sincere) is not bool
        or goal not in ("IDENTIFY", "ACTION")
    ):
        raise ValueError("declared communication strategy required")
    scores = {}
    for message in messages:
        if sincere and not set(speaker_states) <= set(message["meaning"]):
            continue
        prediction = predictions.get(message["id"])
        if prediction is None or not prediction["posterior"]:
            continue
        if goal == "IDENTIFY":
            benefit = sum(
                weight * prediction["posterior"].get(state, 0)
                for state, weight in weights.items()
            )
        else:
            if not prediction["actions"]["policy"]:
                continue
            benefit = sum(
                weight * probability * float(rational(utilities[state][action]))
                for state, weight in weights.items()
                for action, probability in prediction["actions"]["policy"].items()
            )
        scores[message["id"]] = benefit - float(rational(message["cost"]))
    return dict(
        status="COMPUTED" if scores else "NO_EXECUTABLE_STRATEGY",
        utilities=scores,
        policy=_softmax(scores, b),
        best_messages=(
            tuple(
                sorted(
                    key
                    for key, value in scores.items()
                    if value == max(scores.values())
                )
            )
            if scores
            else ()
        ),
        speaker_states=tuple(sorted(speaker_states)),
        speaker_weights=weights,
        goal=goal,
        sincere=sincere,
        frontier=(),
        scope="CONDITIONAL_STRATEGY_NOT_ACTUAL_INTENT",
    )


def understands_version(interpretations, message, actor, version, at, content):
    """Use the latest available reading, without backfilling later evidence."""
    records = [
        i
        for i in interpretations
        if i["message_id"] == message and i["actor"] == actor and i["at"] <= at
    ]
    if not records:
        return False
    latest = max(i["at"] for i in records)
    return all(
        i["versions"] == [version] and i.get("contents") == [content]
        for i in records
        if i["at"] == latest
    )


def commitment_history(terms, facts, acts, deliveries, interpretations, *, through):
    """Deterministic conditional lifecycle; late facts never backfill receipt."""
    offer, speaker, recipient = terms["offer_id"], terms["speaker"], terms["recipient"]
    timeline = sorted(
        {
            terms["offered_at"],
            terms["deadline"],
            through,
            *(f["at"] for f in facts),
            *(a["at"] for a in acts),
            *(d["at"] for d in deliveries),
        }
    )
    if terms["acceptance"] not in ("QUALIFIED_ACT", "RECEIVED_BY_OFFEROR"):
        raise ValueError("declared acceptance-effect rule required")
    accepted = not terms["requires_acceptance"]
    processed = set()
    released, refused, activated, fulfilled, breached = (
        False,
        False,
        False,
        False,
        False,
    )
    history, invalid, frontier = [], [], []
    simultaneous = {}
    for act in acts:
        if (
            act["refers_to"] == offer
            and act["at"] <= through
            and act["kind"] in ("ACCEPT", "REFUSE", "WITHDRAW")
        ):
            simultaneous.setdefault((act["at"], act["actor"]), []).append(act)
    ambiguous = {
        act["id"]
        for group in simultaneous.values()
        if len({a["kind"] for a in group}) > 1
        for act in group
    }

    def received(message, actor, at):
        return any(
            d["message_id"] == message and d["actor"] == actor and d["at"] <= at
            for d in deliveries
        )

    for at in timeline:
        if at < terms["offered_at"] or at > through:
            continue
        for act in sorted(
            (a for a in acts if a["at"] <= at and a["id"] not in processed),
            key=lambda a: (a["at"], a["id"]),
        ):
            if act["refers_to"] != offer or act["kind"] not in (
                "ACCEPT",
                "REFUSE",
                "WITHDRAW",
                "REPORT_FULFILLED",
            ):
                continue
            kind = act["kind"]
            processed.add(act["id"])
            if act["id"] in ambiguous:
                invalid.append(
                    dict(
                        act_id=act["id"],
                        reason="SIMULTANEOUS_COMMITMENT_ACTS_UNORDERED",
                    )
                )
                frontier.append("SIMULTANEOUS_COMMITMENT_ACTS_UNORDERED")
                continue
            required = recipient if kind in ("ACCEPT", "REFUSE") else speaker
            if act["actor"] != required:
                invalid.append(dict(act_id=act["id"], reason="WRONG_PARTICIPANT"))
                continue
            if kind in ("ACCEPT", "REFUSE"):
                understood = understands_version(
                    interpretations,
                    offer,
                    recipient,
                    terms["version"],
                    act["at"],
                    terms["offer_literal"],
                )
                if (
                    not received(offer, recipient, act["at"])
                    or not understood
                    or act["version"] != terms["version"]
                ):
                    invalid.append(
                        dict(
                            act_id=act["id"],
                            reason="ORIGINAL_TERMS_NOT_RECEIVED_AND_INTERPRETED",
                        )
                    )
                    continue
                if kind == "ACCEPT":
                    if terms["acceptance"] == "RECEIVED_BY_OFFEROR" and not received(
                        act["id"], speaker, at
                    ):
                        processed.remove(act["id"])
                        continue
                    if at > terms["deadline"]:
                        # The bounded original terms do not specify a new or
                        # retroactive contract. Keep that effect unresolved.
                        invalid.append(
                            dict(
                                act_id=act["id"],
                                reason="LATE_ACCEPTANCE_EFFECT_UNMODELED",
                            )
                        )
                        frontier.append("LATE_ACCEPTANCE_EFFECT_UNMODELED")
                        continue
                    accepted = True
                else:
                    if accepted:
                        invalid.append(
                            dict(
                                act_id=act["id"],
                                reason="POST_ACCEPTANCE_REFUSAL_EFFECT_UNMODELED",
                            )
                        )
                        frontier.append("POST_ACCEPTANCE_REFUSAL_EFFECT_UNMODELED")
                        continue
                    refused = True
            elif kind == "WITHDRAW":
                if act["version"] != terms["version"]:
                    invalid.append(
                        dict(act_id=act["id"], reason="WITHDRAWAL_VERSION_MISMATCH")
                    )
                    continue
                if terms["withdrawal"] == "RECEIVED_RELEASE" and received(
                    act["id"], recipient, at
                ):
                    released = True
            else:
                invalid.append(
                    dict(act_id=act["id"], reason="REPORT_IS_NOT_VERIFIED_FULFILLMENT")
                )
        # Delayed withdrawal delivery takes effect only now, never at send time.
        if terms["withdrawal"] == "RECEIVED_RELEASE" and any(
            a["kind"] == "WITHDRAW"
            and a["actor"] == speaker
            and a["refers_to"] == offer
            and a["version"] == terms["version"]
            and a["id"] not in ambiguous
            and a["at"] <= at
            and received(a["id"], recipient, at)
            for a in acts
        ):
            released = True
        current = next((f for f in facts if f["at"] == at), None)
        condition = current["condition"] if current else (False, True)
        outcome = current["outcome"] if current else (False, True)
        eligible = accepted and not refused and not released
        if eligible and tuple(condition) == (True,):
            activated = True
        active = eligible and (
            activated
            if terms["activation"] == "LATCHED"
            else tuple(condition) == (True,)
        )
        if active and tuple(outcome) == (True,):
            fulfilled = True
        if (
            active
            and not fulfilled
            and at == terms["deadline"]
            and tuple(outcome) == (False,)
        ):
            breached = True
        status = (
            "BREACHED_THEN_FULFILLED"
            if breached and fulfilled
            else (
                "BREACHED"
                if breached
                else (
                    "FULFILLED"
                    if fulfilled
                    else (
                        "RELEASED"
                        if released
                        else (
                            "REFUSED"
                            if refused
                            else (
                                "ACTIVE"
                                if active
                                else (
                                    "AWAITING_ACCEPTANCE"
                                    if not accepted
                                    else (
                                        "CONDITION_FALSE"
                                        if tuple(condition) == (False,)
                                        else "CONDITION_UNRESOLVED"
                                    )
                                )
                            )
                        )
                    )
                )
            )
        )
        history.append(
            dict(
                at=at,
                status=status,
                accepted=accepted,
                activated=activated,
                released=released,
                condition=tuple(condition),
                outcome=tuple(outcome),
                assumption_environments=(
                    tuple(current.get("assumption_environments", ())) if current else ()
                ),
                fulfilled=fulfilled,
                breached=breached,
            )
        )
    return dict(
        status=history[-1]["status"] if history else "NOT_YET_OFFERED",
        history=tuple(history),
        invalid_acts=tuple(invalid),
        frontier=tuple(sorted(set(frontier))),
        original_version=terms["version"],
        scope="DECLARED_COMMITMENT_RULES_NOT_MORAL_VERDICT",
    )


def acknowledgment_chains(
    messages, acts, deliveries, interpretations, *, through, max_depth=4
):
    """Finite explicit receipt/interpretation/acknowledgment chains, not infinity."""
    if type(max_depth) is not int or not 1 <= max_depth <= 8:
        raise ValueError("bounded acknowledgment depth required")
    by_id = {m["id"]: m for m in messages}
    chains, diagnostics, prefixes = {}, [], {}

    def proof(message, actor, at):
        # Receipt and the latest interpretation remain separately inspectable.
        received = [
            d
            for d in deliveries
            if d["message_id"] == message and d["actor"] == actor and d["at"] <= at
        ]
        readings = [
            i
            for i in interpretations
            if i["message_id"] == message and i["actor"] == actor and i["at"] <= at
        ]
        evidence = []
        for kind, rows, select in (
            ("RECEIPT", received, min),
            ("INTERPRETATION", readings, max),
        ):
            if rows:
                point = select(row["at"] for row in rows)
                evidence.extend(
                    dict(kind=kind, **row) for row in rows if row["at"] == point
                )
        return evidence

    for act in sorted(acts, key=lambda a: (a["at"], a["id"])):
        if act["at"] > through or act["kind"] not in ("INTERPRET", "ACK"):
            continue
        own = by_id.get(act["id"])
        if own is None or (
            own["at"],
            own["speaker"],
            own["audience"],
            own["version"],
        ) != (act["at"], act["actor"], act["audience"], act["version"]):
            diagnostics.append(
                dict(act_id=act["id"], reason="UNBOUND_ACKNOWLEDGMENT_ACT")
            )
            continue
        parent = by_id.get(act["refers_to"])
        prior = chains.get(act["refers_to"])
        if (
            parent is None
            or parent["at"] >= act["at"]
            or act["actor"] not in parent["audience"]
            or parent["speaker"] not in act["audience"]
        ):
            diagnostics.append(
                dict(act_id=act["id"], reason="UNRESOLVED_ACKNOWLEDGMENT_REFERENCE")
            )
            continue
        received = any(
            d["message_id"] == parent["id"]
            and d["actor"] == act["actor"]
            and d["at"] <= act["at"]
            for d in deliveries
        )
        if not received:
            diagnostics.append(
                dict(act_id=act["id"], reason="PRIOR_MESSAGE_NOT_RECEIVED_AT_ACK")
            )
            continue
        if act["kind"] == "INTERPRET":
            valid = understands_version(
                interpretations,
                parent["id"],
                act["actor"],
                act["version"],
                act["at"],
                parent["literal"],
            )
            if not valid or act["version"] != parent["version"]:
                diagnostics.append(
                    dict(act_id=act["id"], reason="INTERPRETATION_MISMATCH")
                )
                continue
            chain, depth = (parent["id"], act["id"]), 1
            participants = tuple(sorted((parent["speaker"], act["actor"])))
            root = parent
            prefix = []
        elif prior is not None and act["version"] == prior["version"]:
            participants = prior["participants"]
            if (
                act["actor"] not in participants
                or parent["speaker"] not in participants
            ):
                diagnostics.append(
                    dict(act_id=act["id"], reason="ACKNOWLEDGMENT_PARTICIPANT_CHANGED")
                )
                continue
            root = by_id[prior["chain"][0]]
            prefix = prefixes[parent["id"]]
            if not understands_version(
                interpretations,
                parent["id"],
                act["actor"],
                act["version"],
                act["at"],
                parent["literal"],
            ):
                diagnostics.append(
                    dict(act_id=act["id"], reason="ACK_CONTENT_NOT_INTERPRETED")
                )
                continue
            chain, depth = (*prior["chain"], act["id"]), prior["depth"] + 1
        else:
            diagnostics.append(
                dict(act_id=act["id"], reason="NO_MATCHING_PRIOR_INTERPRETATION_CHAIN")
            )
            continue
        if own["literal"] != root["literal"] or own["version"] != root["version"]:
            diagnostics.append(
                dict(act_id=act["id"], reason="ACKNOWLEDGMENT_ROOT_CONTENT_MISMATCH")
            )
            continue
        if depth > max_depth:
            diagnostics.append(
                dict(act_id=act["id"], reason="ACKNOWLEDGMENT_DEPTH_FRONTIER")
            )
            continue
        delivered = tuple(
            sorted(
                a
                for a in act["audience"]
                if any(
                    d["message_id"] == act["id"]
                    and d["actor"] == a
                    and d["at"] <= through
                    for d in deliveries
                )
            )
        )
        prefix = [*prefix, *proof(parent["id"], act["actor"], act["at"])]
        prefixes[act["id"]] = prefix
        evidence = [
            *prefix,
            *(item for actor in delivered for item in proof(act["id"], actor, through)),
        ]
        chains[act["id"]] = dict(
            participants=participants,
            root_content=root["literal"],
            evidence=tuple(evidence),
            assumption_environments=tuple(
                sorted(
                    {
                        a
                        for item in evidence
                        for a in item.get("assumption_environments", ())
                    }
                )
            ),
            chain=chain,
            depth=depth,
            version=act["version"],
            delivered_to=delivered,
            complete=parent["speaker"] in delivered
            and understands_version(
                interpretations,
                act["id"],
                parent["speaker"],
                act["version"],
                through,
                by_id[act["id"]]["literal"],
            ),
            common_knowledge="NOT_ESTABLISHED",
        )
    return dict(
        chains=tuple(chains.values()),
        diagnostics=tuple(diagnostics),
        scope="FINITE_EXPLICIT_ACKNOWLEDGMENT_NOT_PRIVATE_UNDERSTANDING",
    )
