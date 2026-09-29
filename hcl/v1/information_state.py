"""Bounded source-reported object access from ordinary prose.

An explicit named observer or a tightly bounded adjacent-sentence pronoun can
be bound to a location report. Narrative order is retained as source order;
it is not silently promoted to event chronology, private belief, or a
prediction of where somebody will search.
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
_SEEN_PLACE = re.compile(rf'(?P<viewer>{_NAME}) '
    r'(?:saw|sees|noticed|notices|glimpsed|glimpses|spotted|spots) '
    r'(?:a pair of |the |a |an )?'
    rf'(?P<item>{_ITEM}) (?:in|on|at) (?:the |a |an )?(?P<place>{_PLACE})', re.I)
_QUERY = re.compile(rf'\b(?P<actor>{_NAME}) (?:would|might|will|does|did) '
    r'(?:look|search)\b.*?\b(?:find|for) (?:the |a |an )?'
    rf'(?P<item>{_ITEM})(?=\s+(?:given|according|based|in the story)\b|[?.!]|$)', re.I)
_INVERTED_QUERY = re.compile(rf'\bwhere (?:would|might|will|does|did) (?P<actor>{_NAME}) '
    r'(?:look|search)\b.*?\b(?:find|for) (?:the |a |an )?'
    rf'(?P<item>{_ITEM})(?=\s+(?:given|according|based|in the story)\b|[?.!]|$)', re.I)
_SENTENCE = re.compile(r'[^.!?。！？]+[.!?。！？]?')
_PRONOUNS = frozenset(('he', 'she', 'it', 'they', 'we', 'i', 'you', 'him', 'her', 'them'))
_LOCAL_SUBJECT = re.compile(rf'(?:^|,\s*)(?P<actor>{_NAME}) '
    r'(?P<verb>[a-z]+(?:s|ed))\b')
_CAPITAL_NAME = re.compile(rf'\b(?P<name>{_NAME})(?!\x27s)\b')
_LOCAL_SIGHT = re.compile(rf'^(?:At|In|On) (?:the |a |an )?'
    r'(?P<place>[A-Za-z][A-Za-z \x27-]{0,60}?), '
    rf'(?P<viewer>he|she|{_NAME}) (?P<verb>saw|sees|noticed|notices|'
    r'glimpsed|glimpses|spotted|spots) (?:a pair of |the |a |an )?', re.I)
_UNSAFE_OBSERVATION_REMAINDER = re.compile(
    r'\b(?:not|never|no|might|may|could|if|imagined|imaginary|dream|dreams|'
    r'dreamed|pretended|pretends|claimed|reportedly|allegedly|hypothetically)\b', re.I)


def information_query(query):
    """Select a general actor/object search question, independent of dataset."""
    match = _QUERY.search(query) or _INVERTED_QUERY.search(query)
    if match is None or match['actor'].casefold() in _PRONOUNS:
        return None
    return (match['actor'], match['item'].strip().casefold())


def _clean(value):
    return ' '.join(value.casefold().split())


def _adjacent_subject(previous, actor):
    """Resolve only one source-local human subject, without name semantics."""
    if not previous:
        return False
    subjects = [m['actor'] for m in _LOCAL_SUBJECT.finditer(previous)]
    if len(subjects) != 1 or subjects[0].casefold() != actor.casefold():
        return False
    # A second non-possessive name can be another possible referent. Ignore
    # only the capitalized sentence opener, if it is not the matched subject.
    names = [m['name'] for m in _CAPITAL_NAME.finditer(previous)]
    if names and names[0].casefold() != actor.casefold():
        names = names[1:]
    return len(names) == 1 and names[0].casefold() == actor.casefold()


def _local_sight(body, previous, actor, item):
    prefix = _LOCAL_SIGHT.match(body)
    if prefix is None:
        return None
    pronoun = prefix['viewer'].casefold() in ('he', 'she')
    if (pronoun and not _adjacent_subject(previous, actor)) or (
            not pronoun and prefix['viewer'].casefold() != actor.casefold()):
        return None
    remainder = body[prefix.end():]
    item_match = re.match(re.escape(item) + r'\b', remainder, re.I)
    if item_match is None:
        return None
    tail = remainder[item_match.end():]
    if _UNSAFE_OBSERVATION_REMAINDER.search(tail) or '\x22' in tail or '\x27' in tail:
        return None
    return dict(item=remainder[:item_match.end()], place=prefix['place'],
        viewer=actor, pronoun=pronoun)


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
        previous = sentences[index - 2] if index > 1 else None
        adjacent = (previous is not None and '\n' not in narrative[
            previous[1] + len(previous[0]):start])
        local_sight = (_local_sight(body, previous[0] if adjacent else None, actor, item)
            if not (movement or seen_place or bare_move) else None)
        matched = movement or seen_place or bare_move or local_sight
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
                  seen_place['viewer'] if seen_place else
                  local_sight['viewer'] if local_sight else None)
        if viewer and viewer.casefold() == actor.casefold():
            observations.append(dict(row,
                access=('ADJACENT_UNIQUE_SUBJECT_PRONOUN_OBSERVATION' if local_sight and local_sight['pronoun']
                    else 'EXPLICIT_NAMED_OBSERVATION'), observer=viewer,
                actor_binding=('SOURCE_LOCAL_PRONOUN_INFERENCE_NOT_IDENTITY_FACT'
                    if local_sight and local_sight['pronoun'] else 'EXPLICIT_NAME')))
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
            'An adjacent pronoun binding is a local interpretation, not a verified '
            'identity fact. Unreported access is unknown, not absent.'))
