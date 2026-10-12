"""Finite belief-state dynamic programming and declared mixed action policies.

Rewards, costs, transitions, observation channels and mixture parameters are
conditional model inputs. The solver computes Q; it never accepts action scores.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
import math

from hcl.kernel.types import freeze


def rational(value):
    if type(value) not in (int, str):
        raise ValueError("exact finite rational required")
    number = Fraction(value)
    if abs(number) > 1000000 or number.denominator > 1000000:
        raise ValueError("numeric model bound")
    return number


def encoded(value):
    return str(value.numerator) if value.denominator == 1 else str(value)


@dataclass(frozen=True)
class Action:
    action_id: str
    cost: str
    enabled: tuple[str, ...]
    feasible: tuple[str, ...]
    transitions: object
    observations: object

    def __post_init__(self):
        if type(self.action_id) is not str or not self.action_id or len(self.action_id) > 160:
            raise ValueError("action identity required")
        if rational(self.cost) < 0:
            raise ValueError("nonnegative action cost required")
        object.__setattr__(self, "enabled", tuple(self.enabled))
        object.__setattr__(self, "feasible", tuple(self.feasible))
        object.__setattr__(self, "transitions", freeze(self.transitions))
        object.__setattr__(self, "observations", freeze(self.observations))


@dataclass(frozen=True)
class PlanModel:
    states: tuple[str, ...]
    terminal: tuple[str, ...]
    utilities: object
    actions: tuple[Action, ...]

    def __post_init__(self):
        if (
            not 1 <= len(self.states) <= 128
            or len(set(self.states)) != len(self.states)
            or any(type(x) is not str or not x or len(x) > 160 for x in self.states)
        ):
            raise ValueError("finite planning states required")
        if not set(self.terminal) <= set(self.states) or set(self.utilities) != set(self.states):
            raise ValueError("terminal states and every state's terminal utility required")
        for value in self.utilities.values():
            rational(value)
        if not 1 <= len(self.actions) <= 32 or len({a.action_id for a in self.actions}) != len(
            self.actions
        ):
            raise ValueError("finite unique typed actions required")
        states = set(self.states)
        for action in self.actions:
            if (
                type(action) is not Action
                or not set(action.enabled) <= states
                or not set(action.feasible) <= set(action.enabled)
            ):
                raise ValueError("action opportunities/preconditions must be declared")
            if (
                set(action.transitions) != states
                or not set(action.transitions.values()) <= states
                or set(action.observations) != states
            ):
                raise ValueError("total finite transition and observation functions required")
            if any(type(value) is not str or len(value) > 160 for value in action.observations.values()):
                raise ValueError("bounded observation symbols required")
            if any(action.transitions[state] != state for state in self.terminal):
                raise ValueError("terminal planning states must be absorbing")
        object.__setattr__(self, "states", tuple(self.states))
        object.__setattr__(self, "terminal", tuple(self.terminal))
        object.__setattr__(self, "utilities", freeze(self.utilities))
        object.__setattr__(self, "actions", tuple(self.actions))


def _belief(model, weights):
    if not isinstance(weights, Mapping) or not weights or not set(weights) <= set(model.states):
        raise ValueError("declared belief distribution required")
    parsed = {state: rational(value) for state, value in weights.items()}
    if any(value < 0 for value in parsed.values()) or sum(parsed.values()) != 1:
        raise ValueError("belief weights must be nonnegative and sum to one")
    return tuple(sorted((state, value) for state, value in parsed.items() if value))


def solve_action_values(model, weights, horizon, *, max_expansions=100000, actual_state=None):
    """Exact finite-horizon planning over observation-conditioned belief states."""
    if (
        type(horizon) is not int
        or not 1 <= horizon <= 32
        or type(max_expansions) is not int
        or not 1 <= max_expansions <= 10000000
    ):
        raise ValueError("bounded planning allowance required")
    if actual_state is not None and actual_state not in model.states:
        raise ValueError("declared actual state required")
    belief = _belief(model, weights)
    terminal = set(model.terminal)
    used = 0

    def spend():
        nonlocal used
        if used >= max_expansions:
            raise OverflowError("PLANNING_FRONTIER")
        used += 1

    def available(distribution):
        active = {state for state, weight in distribution if state not in terminal}
        return tuple(a for a in model.actions if active and active <= set(a.enabled))

    def stop(distribution):
        return sum(weight * rational(model.utilities[state]) for state, weight in distribution)

    @lru_cache(None)
    def value(distribution, left):
        spend()
        actions = available(distribution)
        if left == 0 or not actions:
            return stop(distribution)
        return max(q(distribution, action, left) for action in actions)

    def q(distribution, action, left):
        spend()
        cost = rational(action.cost) * sum(
            weight for state, weight in distribution if state not in terminal
        )
        groups = {}
        for state, weight in distribution:
            target = action.transitions[state]
            symbol = action.observations[target]
            group = groups.setdefault(symbol, {})
            group[target] = group.get(target, Fraction(0)) + weight
        expected = -cost
        for group in groups.values():
            mass = sum(group.values())
            successor = tuple(sorted((state, weight / mass) for state, weight in group.items()))
            expected += mass * value(successor, left - 1)
        return expected

    try:
        actions = available(belief)
        results = {a.action_id: q(belief, a, horizon) for a in actions}
        best = max(results.values()) if results else None
        return dict(
            status=(
                "SOLVED"
                if actions
                else (
                    "TERMINAL" if all(state in terminal for state, _ in belief) else "NO_AVAILABLE_ACTIONS"
                )
            ),
            q={key: encoded(v) for key, v in results.items()},
            best_actions=sorted(key for key, v in results.items() if v == best),
            subjective_feasibility={
                a.action_id: all(state in a.feasible for state, weight in belief if state not in terminal)
                for a in actions
            },
            world_feasibility=(
                {}
                if actual_state is None
                else {a.action_id: actual_state in a.feasible for a in model.actions}
            ),
            belief={state: encoded(weight) for state, weight in belief},
            horizon=horizon,
            expansions=used,
            frontier=[],
            scope="DECLARED_BELIEF_GOAL_TRANSITION_MODEL_ONLY",
        )
    except OverflowError:
        return dict(
            status="FRONTIER_UNEXPLORED",
            q={},
            best_actions=[],
            expansions=used,
            frontier=["PLANNING_FRONTIER"],
            scope="DECLARED_BELIEF_GOAL_TRANSITION_MODEL_ONLY",
        )


def mixed_policy(q_values, *, beta, rational_weight, habit_weight, error_weight, habit):
    """All mixture parameters are declared hypotheses, not human constants."""
    if not isinstance(q_values, Mapping) or not q_values:
        raise ValueError("computed nonempty action values required")
    values = {key: rational(value) for key, value in q_values.items()}
    weights = tuple(rational(v) for v in (rational_weight, habit_weight, error_weight))
    b = rational(beta)
    if b < 0 or b > 100 or any(w < 0 for w in weights) or sum(weights) != 1:
        raise ValueError("bounded beta and normalized nonnegative mixture required")
    if set(habit) != set(values):
        raise ValueError("habit policy over the same feasible action set required")
    habits = {key: rational(v) for key, v in habit.items()}
    if any(v < 0 for v in habits.values()) or sum(habits.values()) != 1:
        raise ValueError("normalized declared habit required")
    logits = {key: float(b * value) for key, value in values.items()}
    offset = max(logits.values())
    exps = {key: math.exp(value - offset) for key, value in logits.items()}
    normalizer = sum(exps.values())
    soft = {key: value / normalizer for key, value in exps.items()}
    distribution = {
        key: float(weights[0]) * soft[key]
        + float(weights[1] * habits[key])
        + float(weights[2]) / len(values)
        for key in values
    }
    return dict(
        probabilities=distribution,
        rational_component=soft,
        mixture={
            "rational": encoded(weights[0]),
            "habit": encoded(weights[1]),
            "error": encoded(weights[2]),
        },
        calibration="DECLARED_MODEL_PARAMETERS_NOT_CALIBRATED_HUMAN_PROBABILITIES",
    )
