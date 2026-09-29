"""Bounded source-reported object access from ordinary prose.

Only an explicit named observer is bound to a location report. Narrative order
is retained as source order; it is not silently promoted to event chronology,
private belief, or a prediction of where somebody will search.
"""
import re

_NAME = r'[A-Z][A-Za-z-]{0,39}'
_ITEM = r'[A-Za-z][A-Za-z -]{0,50}?'
_PLACE = r'[A-Za-z][A-Za-z -]{0,60}?'
_MOVE = re.compile(
    rf'(?P<mover>{_NAME}) (?P<verb>put|placed|place|moved|move) '
    rf'(?:the |a |an )?(?P<item>{_ITEM}) (?:in|on|at|to) '
    rf'(?:the |a |an )?(?P<place>{_PLACE})', re.I)
_SEEN_MOVE = re.compile(rf'(?P<viewer>{_NAME}) saw (?P<movement>.+)', re.I)
_SEEN_PLACE = re.compile(rf'(?P<viewer>{_NAME}) saw (?:the |a |an )?'
    rf'(?P<item>{_ITEM}) (?:in|on|at) (?:the |a |an )?(?P<place>{_PLACE})', re.I)
_QUERY = re.compile(rf'\b(?P<actor>{_NAME}) (?:would|might|will|does|did) '
    r'(?:look|search)\b.*?\b(?:find|for) (?:the |a |an )?'
    rf'(?P<item>{_ITEM})(?=\s+(?:given|according|based|in the story)\b|[?.!]|$)', re.I)
_INVERTED_QUERY = re.compile(rf'\bwhere (?:would|might|will|does|did) (?P<actor>{_NAME}) '
    r'(?:look|search)\b.*?\b(?:find|for) (?:the |a |an )?'
    rf'(?P<item>{_ITEM})(?=\s+(?:given|according|based|in the story)\b|[?.!]|$)', re.I)
_SENTENCE = re.compile(r'[^.!?。！？]+[.!?。！？]?')
_PRONOUNS = frozenset(('he', 'she', 'it', 'they', 'we', 'i', 'you', 'him', 'her', 'them'))


def information_query(query):
    """Select a general actor/object search question, independent of dataset."""
    match = _QUERY.search(query) or _INVERTED_QUERY.search(query)
    if match is None or match['actor'].casefold() in _PRONOUNS:
        return None
    return (match['actor'], match['item'].strip().casefold())


def _clean(value):
    return ' '.join(value.casefold().split())


def check_information_state(narrative, actor, item):
    """Return exact source spans and the actor's reported observations only.

    Missing access remains unknown. A later source-reported movement cannot be
    installed in a person's information state without a named observation.
    """
    if not isinstance(narrative, str) or not narrative or len(narrative) > 16000:
        raise ValueError('bounded narrative required')
    if (not isinstance(actor, str) or not actor or actor.casefold() in _PRONOUNS or
            not isinstance(item, str) or not item):
        raise ValueError('explicit actor and item required')
    sentences = [(m.group().strip(), m.start() + len(m.group()) - len(m.group().lstrip()))
                 for m in _SENTENCE.finditer(narrative) if m.group().strip()]
    if len(sentences) > 64:
        return dict(status='UNRESOLVED_SOURCE_BOUND', actor=actor, item=item,
                    checked_observation_count=0, observations=[], source_movements=[],
                    last_reported_observation=None, time_basis='NARRATIVE_ORDER_ONLY')
    observations, movements = [], []
    for index, (text, start) in enumerate(sentences, 1):
        body = text.rstrip('.!?。！？').strip()
        # Complete clauses only. Embedded or quoted speech, pronouns, negation,
        # and ambiguous multi-action sentences do not create an access edge.
        seen_move = _SEEN_MOVE.fullmatch(body)
        movement = _MOVE.fullmatch(seen_move['movement']) if seen_move else None
        seen_place = _SEEN_PLACE.fullmatch(body) if not movement else None
        bare_move = _MOVE.fullmatch(body) if not (movement or seen_place) else None
        matched = movement or seen_place or bare_move
        if not matched or _clean(matched['item']) != _clean(item):
            continue
        row = dict(source_quote=text, source_start=start,
                   source_end=start + len(text), narrative_position=index,
                   item=matched['item'], location=matched['place'],
                   time_basis='NARRATIVE_ORDER_ONLY',
                   assertion='SOURCE_REPORT_NOT_VERIFIED_WORLD_TRUTH')
        if movement or bare_move:
            movements.append(dict(row, mover=matched['mover'],
                                  observer=seen_move['viewer'] if movement else None))
        viewer = (seen_move['viewer'] if movement else
                  seen_place['viewer'] if seen_place else None)
        if viewer and viewer.casefold() == actor.casefold():
            observations.append(dict(row, access='EXPLICIT_NAMED_OBSERVATION',
                                     observer=viewer))
    latest = observations[-1] if observations else None
    return dict(status=('CHECKED_SOURCE_REPORTED_OBSERVATION' if latest else
                        'UNRESOLVED_NO_EXPLICIT_NAMED_OBSERVATION'),
        actor=actor, item=item, checked_observation_count=len(observations),
        observations=observations, source_movements=movements,
        last_reported_observation=latest,
        later_source_movement_without_observation_evidence=bool(latest and any(
            m['narrative_position'] > latest['narrative_position'] and
            (m['observer'] is None or m['observer'].casefold() != actor.casefold())
            for m in movements)),
        time_basis='NARRATIVE_ORDER_ONLY',
        inference_boundary=('Observation supports reported exposure only; it does not prove '
            'private belief, knowledge, current world location, or future search behavior. '
            'Unreported access is unknown, not absent.'))
