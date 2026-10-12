"""Exact hypothetical source-piece permutations and declared occurrence contrasts.

Generated order is never original evidence, a story chronology edge, or an
estimate of reader emotion. Source text and semantic labels remain unchanged.
"""

from hashlib import sha256

MAX_REORDER_PARTS = 16
MAX_REORDER_MENTIONS = 128
MAX_REORDER_WORK = 16384


def reorder_text(text, parts, order):
    """Return a bounded permutation and its exact, piecewise source offset map."""
    if (
        type(text) is not str
        or len(text) > 4 * 1024 * 1024
        or type(parts) not in (tuple, list)
        or not 2 <= len(parts) <= MAX_REORDER_PARTS
        or type(order) not in (tuple, list)
        or len(order) != len(parts)
        or any(type(i) is not int for i in order)
        or sorted(order) != list(range(len(parts)))
    ):
        raise ValueError("bounded original-piece permutation required")
    text.encode()
    previous = None
    for part in parts:
        start, end = part["start"], part["end"]
        if (
            type(start) is not int
            or type(end) is not int
            or not 0 <= start < end <= len(text)
            or previous is not None
            and start != previous
            or text[start:end] != part["quote"]
        ):
            raise ValueError("contiguous exact original pieces required")
        previous = end
    start, end = parts[0]["start"], parts[-1]["end"]
    position, pieces, replacements = start, [], []
    for index in order:
        part = parts[index]
        fragment = text[part["start"] : part["end"]]
        pieces.append(
            dict(
                part_index=index,
                original_range=(part["start"], part["end"]),
                generated_range=(position, position + len(fragment)),
                original_quote_sha256=sha256(fragment.encode()).hexdigest(),
            )
        )
        replacements.append(fragment)
        position += len(fragment)
    changed = text[:start] + "".join(replacements) + text[end:]
    assert len(changed) == len(text)
    return changed, dict(
        original_range=(start, end),
        generated_range=(start, end),
        pieces=pieces,
        order=tuple(order),
        basis="EXACT_HYPOTHETICAL_PIECE_PERMUTATION",
    )


def reorder_discourse(mentions, source_id, offset_map, max_work):
    """Compare actually mapped original occurrences with an explicit frontier.

    Mentions crossing a cut are unresolved, never re-identified by name/string
    matching. Equal positions remain overlap, not an invented strict order.
    """
    if type(max_work) is not int or not 0 <= max_work <= MAX_REORDER_WORK:
        raise ValueError("bounded discourse comparison work required")
    selected = [m for m in mentions if m["source_id"] == source_id]
    if len(selected) > MAX_REORDER_MENTIONS:
        raise ValueError("bounded declared occurrence set required")
    work, projected, unresolved, changed, frontier = 0, [], [], [], []
    region_start, region_end = offset_map["original_range"]

    class Exhausted(Exception):
        pass

    def charge():
        nonlocal work
        if work >= max_work:
            raise Exhausted()
        work += 1

    def relation(left, right):
        if left[1] <= right[0]:
            return "BEFORE"
        if right[1] <= left[0]:
            return "AFTER"
        return "OVERLAPPING_MENTIONS"

    pending = []
    try:
        for index, mention in enumerate(selected):
            pending = [[m["fragment"], m["mention_id"]] for m in selected[index:]]
            charge()
            anchor = mention["anchor"]
            start, end = anchor["start"], anchor["end"]
            generated = None
            if end <= region_start or start >= region_end:
                generated = (start, end)
            else:
                for piece in offset_map["pieces"]:
                    left, right = piece["original_range"]
                    if left <= start < end <= right:
                        shift = piece["generated_range"][0] - left
                        generated = (start + shift, end + shift)
                        break
            if generated is None:
                unresolved.append(
                    dict(
                        mention=[mention["fragment"], mention["mention_id"]],
                        original_anchor=anchor,
                        reason="MENTION_CROSSES_REORDER_CUT",
                    )
                )
                continue
            projected.append(
                dict(
                    mention=[mention["fragment"], mention["mention_id"]],
                    declared_event=mention["event"],
                    declared_frame=mention["frame"],
                    original_anchor=anchor,
                    generated_range=generated,
                    reference_attribution_resolved=mention["attribution_resolved"],
                    qualification="HYPOTHETICAL_POSITION_NOT_ORIGINAL_EVIDENCE",
                )
            )
        pending = []
        for i, left in enumerate(projected):
            for right in projected[i + 1 :]:
                charge()
                old = relation(
                    (left["original_anchor"]["start"], left["original_anchor"]["end"]),
                    (
                        right["original_anchor"]["start"],
                        right["original_anchor"]["end"],
                    ),
                )
                new = relation(left["generated_range"], right["generated_range"])
                if old != new:
                    changed.append(
                        dict(
                            left=left["mention"],
                            right=right["mention"],
                            original_relation=old,
                            hypothetical_relation=new,
                            axis="DISCOURSE_ORDER_ONLY",
                        )
                    )
    except Exhausted:
        frontier.append("REORDER_DISCOURSE_WORK_FRONTIER")
    return dict(
        schema="hcl-reorder-discourse-1",
        source_id=source_id,
        projected_mentions=projected,
        unresolved_mentions=unresolved,
        uncomputed_mentions=pending,
        changed_pairs=changed,
        work=work,
        frontier=tuple(frontier),
        status=(
            "PARTIAL"
            if frontier or unresolved
            else "COMPLETE_DECLARED_OCCURRENCE_COMPARISON"
        ),
        coverage="DECLARED_SOURCE_MENTIONS_ONLY",
        story_time_effect="UNCHANGED_ORIGINAL_MODEL",
        semantic_or_emotional_effect="NOT_ESTABLISHED",
    )
