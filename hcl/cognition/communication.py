"""Source-reported delivery/access paths select evidence before semantic work.

Availability and addressing are not receipt. Receipt is not comprehension or
acceptance. Contradictory access reports stay unresolved; explicit later receipt
can add access without rewriting an earlier snapshot.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import re

from hcl.v04.model import EventRecord
from hcl.v06.perspective import event_accessible_to
from .core import identity
from .semantic import AuthorizedText, _local_candidates, _PRONOUNS
from .workspace import CognitionWorkspace
from .epistemic import prepare_epistemic

_NAME = r'[A-Z][A-Za-z0-9_-]{0,31}'
_ACTORS = rf'{_NAME}(?: and {_NAME}){{0,7}}'
_RECEIPT = re.compile(rf"Narrator: (?P<actors>{_ACTORS}) (?P<later>later )?"
    rf"(?P<verb>heard|read|missed|did not hear|did not read) "
    rf"(?:(?P<speaker>{_NAME})'s last statement|the previous statement)\.")
_AVAILABLE = re.compile(rf"Narrator: (?P<speaker>{_NAME})'s last statement was publicly available\.")
_STATEMENT_REPORT = re.compile(rf"Narrator: {_NAME}'s statement (?:that .+ (?:is (?:true|false)|omitted that .+)|omitted that .+)\.")
_SENT = re.compile(rf"Narrator: (?P<speaker>{_NAME}) sent (?:their|the) last statement privately to (?P<actors>{_ACTORS})\.")


@dataclass(frozen=True)
class CommunicationView:
    actor: str
    source_id: str
    events: tuple[EventRecord, ...]
    access_audit: tuple[dict, ...]
    through_line: int

    @property
    def visible_text(self):
        return '\n'.join(e.raw_text for e in self.events)

    def workspace(self):
        workspace = CognitionWorkspace()
        if self.events:
            workspace.put_source(self.source_id, self.visible_text, permitted_observers=(self.actor,))
        return workspace

    def semantic(self, query, *, backend=None):
        workspace = self.workspace()
        result = workspace.prepare_semantic(query, source_ids=(self.source_id,) if self.events else (),
            observer=self.actor, backend=backend)
        return workspace, result

    def epistemic(self, query, *, max_depth=3):
        workspace = self.workspace()
        result = prepare_epistemic(workspace, query, source_ids=(self.source_id,) if self.events else (),
            observer=self.actor, max_depth=max_depth)
        return workspace, result


class CommunicationScene:
    def __init__(self, narrative, *, source_id='communication-scene'):
        if (not isinstance(narrative, str) or not narrative.strip() or len(narrative) > 64000
                or not isinstance(source_id, str) or not source_id):
            raise ValueError('bounded authorized narrative required')
        self.source_id = source_id
        self._original = narrative
        self.lines = tuple(narrative.splitlines())
        if len(self.lines) > 80 or any(not s.strip() or len(s) > 4000 for s in self.lines):
            raise ValueError('one unambiguous statement/access cue per bounded source line')

    def _prefix_events(self, cutoff):
        # Preserve B02's existing per-line strip representation, but resolve A02
        # scope once on the selected prefix. Map each whole line back to its
        # original occurrence; neither duplicate text nor future lines can lend
        # another occurrence authority.
        texts, spans, offsets = [], [], []
        original_start = canonical_start = 0
        for original, raw in zip(self.lines[:cutoff], self._original.splitlines(keepends=True)):
            text = original.strip()
            start = original_start + len(original) - len(original.lstrip())
            end = start + len(text)
            if self._original[start:end] != text:
                raise ValueError('communication source occurrence mismatch')
            texts.append(text)
            spans.append((start, end))
            offsets.append(canonical_start)
            original_start += len(raw)
            canonical_start += len(text) + 1
        source = AuthorizedText(self.source_id, '\n'.join(texts))
        candidates = _local_candidates(source) if texts else ()
        result = []
        for text, offset, span in zip(texts, offsets, spans):
            events = [p for p in candidates if p['kind'] == 'event'
                and p['source_id'] == self.source_id and p['start'] == offset and p['quote'] == text]
            if len(events) != 1 or self._original[span[0]:span[1]] != events[0]['quote']:
                raise ValueError('unsupported or ambiguous communication source; no inferred audience')
            result.append((events[0]['content'], span))
        return result

    def view(self, actor, *, through_line=None):
        if not isinstance(actor, str) or not re.fullmatch(_NAME, actor) or actor.lower() in _PRONOUNS:
            raise ValueError('explicit source-named actor required')
        cutoff = len(self.lines) if through_line is None else through_line
        if type(cutoff) is not int or not 0 <= cutoff <= len(self.lines):
            raise ValueError('valid source-line snapshot required')
        prefix_events = self._prefix_events(cutoff)
        statements, last, all_actors = [], {}, {actor}
        for number, original in enumerate(self.lines[:cutoff], 1):
            text = original.strip()
            event, source_span = prefix_events[number - 1]
            source_report = event['assertion_scope'] == 'SOURCE_REPORT'
            cue = _RECEIPT.fullmatch(text) or _AVAILABLE.fullmatch(text) or _SENT.fullmatch(text)
            if cue:
                if not source_report or event['speaker_surface'] != 'Narrator':
                    raise ValueError('access cue requires an actual narrator source occurrence')
                row = cue.groupdict()
                speaker = row.get('speaker')
                statement = last.get(speaker) if speaker else (statements[-1] if statements else None)
                if statement is None or (speaker is None and statement['line'] != number - 1):
                    raise ValueError('access cue lacks an unambiguous preceding statement')
                if not statement['source_report']:
                    raise ValueError('access target requires an actual source occurrence')
                actors = tuple(row.get('actors', '').split(' and ')) if row.get('actors') else ()
                if len(set(actors)) != len(actors) or any(a.lower() in _PRONOUNS for a in actors):
                    raise ValueError('explicit distinct access recipients required')
                all_actors.update(actors)
                if 'verb' in row:
                    positive = row['verb'] in ('heard', 'read')
                    if row.get('later') and not positive:
                        raise ValueError('later non-receipt cannot erase an earlier received statement')
                    kind = ('LATER_RECEIPT' if row.get('later') else 'RECEIPT') if positive else 'NON_RECEIPT'
                else:
                    kind = 'ADDRESSED' if actors else 'PUBLICLY_AVAILABLE'
                statement['proofs'].append(dict(source_line=number, quote=original,
                    actors=actors, kind=kind, source_kind='EXPLICIT_NARRATOR_REPORT'))
                continue
            speaker = event['speaker_surface']
            narrator_record = speaker == 'Narrator' and text.startswith('Narrator:')
            # Reader narration remains unavailable unless a separate explicit
            # receipt names the actor. Ambiguous access cues must not fall back
            # to generic narrator records and thereby evade access validation.
            if narrator_record and not _STATEMENT_REPORT.fullmatch(text) and re.search(r'\b(heard|hear|read|missed|sent|statement|available)\b', text, re.I):
                raise ValueError('unsupported or ambiguous narrator access cue')
            if ((not narrator_record and event['speaker_candidates'] != [speaker])
                    or not re.fullmatch(_NAME, speaker)):
                raise ValueError('explicit actual speaker required')
            if not narrator_record:
                all_actors.add(speaker)
            # Ineligible statements remain ordered, untransmitted sentinels.
            # Removing one would incorrectly resolve "last" to older speech.
            statement = dict(line=number, text=text, speaker=speaker, proofs=[],
                source_report=source_report, source_span=source_span)
            statements.append(statement)
            last[speaker] = statement
        if len(all_actors) > 8:
            raise ValueError('communication actor budget exceeded')
        visible, audit = [], []
        for statement in statements:
            proofs = [p for p in statement['proofs'] if actor in p['actors']]
            positive = [p for p in proofs if p['kind'] in ('RECEIPT', 'LATER_RECEIPT')]
            negative = [p for p in proofs if p['kind'] == 'NON_RECEIPT']
            later = [p for p in positive if p['kind'] == 'LATER_RECEIPT']
            if statement['speaker'] == actor:
                status = 'OWN_EXPRESSION'
            elif later and all(p['source_line'] < later[-1]['source_line'] for p in negative):
                status = 'REPORTED_LATER_EXPOSURE'
            elif positive and negative:
                status = 'CONFLICTING_EXPOSURE_REPORTS'
            elif positive:
                status = 'REPORTED_EXPOSURE'
            elif negative:
                status = 'REPORTED_NON_EXPOSURE'
            elif any(p['kind'] == 'ADDRESSED' for p in proofs):
                status = 'ADDRESSED_RECEIPT_UNKNOWN'
            elif any(p['kind'] == 'PUBLICLY_AVAILABLE' for p in statement['proofs']):
                status = 'PUBLIC_AVAILABILITY_EXPOSURE_UNKNOWN'
            else:
                status = 'EXPOSURE_UNKNOWN'
            allowed = status in ('OWN_EXPRESSION', 'REPORTED_EXPOSURE', 'REPORTED_LATER_EXPOSURE')
            if allowed and not statement['source_report']:
                raise ValueError('visible expression requires an actual source occurrence')
            # Authorizer audit is separate from model inputs. No hidden body is
            # returned even here; a missing route is not a private belief state.
            audit.append(dict(statement_line=statement['line'], status=status,
                relevant_access_proofs=proofs, content_transmitted=allowed,
                comprehension='NOT_ESTABLISHED', acceptance='NOT_ESTABLISHED',
                calendar_time='NOT_ESTABLISHED'))
            if allowed:
                index = len(visible) + 1
                stamp = (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=index)).isoformat()
                event = EventRecord(identity('visible-message', actor, index, statement['text']),
                    stamp, statement['text'], identity('view-source', self.source_id, actor), stamp,
                    actor_id=None if statement['speaker'] == 'Narrator' else statement['speaker'], recipient_ids=(actor,),
                    metadata={'reader_only': False, 'public': False, 'narrator': statement['speaker'] == 'Narrator',
                              'time_semantics': 'VISIBLE_SOURCE_ORDER_ONLY', 'access_state': status})
                if not event_accessible_to(event, actor):
                    raise ValueError('retained perspective policy rejected projected event')
                visible.append(event)
        return CommunicationView(actor, identity('view-source', self.source_id, actor),
            tuple(visible), tuple(audit), cutoff)
