"""Source-declared story, recall, disclosure and record time stay distinct."""
from dataclasses import asdict, dataclass
from datetime import date
import json
import re

from .core import identity
from .episodic import EpisodicIndex
from .revision_time import _stamp
from .workspace import CognitionWorkspace

_NAME=r'(?:[A-Z][\w-]*|she|he|they|someone)'
_DAY=r'\d{4}-\d{2}-\d{2}'
_DIRECT=re.compile(rf'Narrator: On (?P<disclosure>{_DAY}), (?P<actor>{_NAME}) said, "(?P<body>[^"\n]+)"\.?')
_RECALL=re.compile(rf'Narrator: On (?P<disclosure>{_DAY}), (?P<reporter>{_NAME}) disclosed a recollection from (?P<recall>{_DAY}) of (?P<actor>{_NAME}) saying on (?P<story>{_DAY}), "(?P<body>[^"\n]+)"\.?')
_CHALLENGE=re.compile(rf"Narrator: On (?P<disclosure>{_DAY}), (?P<challenger>{_NAME}) challenged (?P<reporter>{_NAME})'s recollection from (?P<recall>{_DAY}) of (?P<actor>{_NAME})'s statement on (?P<story>{_DAY})\.")
_RECEIPT=re.compile(rf"Narrator: On (?P<disclosure>{_DAY}), (?P<viewer>{_NAME}) heard (?P<reporter>{_NAME})'s disclosure from (?P<reported>{_DAY})\.")
_AMBIGUOUS={'she','he','they','someone'}
_POLICY=('Each date is a source declaration. Story time, recall time, disclosure time, '
    'source narrative order and system record time are separate. An attributed '
    'recollection is not an independently verified past utterance or a new utterance '
    'at disclosure. A challenge marks a report contested, not false. A source available '
    'to an analyst does not prove a character received, believed or understood it. '
    'Earlier views cannot acquire later disclosures or receipts. Unknown reference '
    'and inconsistent dates remain unresolved; narrator accuracy is not assumed.')


def _day(value):
    if value is None:return None
    return date.fromisoformat(value).isoformat()


@dataclass(frozen=True)
class NarrativeEpisode:
    episode_id:str
    source_id:str
    source_version:int
    start:int
    end:int
    quote:str
    narrative_order:int
    story_time:str|None
    recall_time:str|None
    disclosure_time:str|None
    system_record_time:str
    actor_surface:str
    reporter_surface:str|None
    reported_content:str
    authority:str
    reference_status:str
    temporal_status:str='DECLARED_DATES_ONLY'
    target_episode_id:str|None=None


def parse_narrative_episodes(source_id,text,*,version=1,recorded_at):
    """Extract source dates without assigning private state or chronology by order.

    Explicit unsupported lines remain diagnostics. A recall has both an original
    attributed story time and a distinct recall/disclosure time. Its quoted actor
    is never silently promoted to a currently speaking or independently verified
    direct source. Missing dates do not fall back to source order.
    """
    if not isinstance(source_id,str) or not source_id or not isinstance(text,str) or len(text)>64000 or type(version)is not int or version<1:
        raise ValueError('bounded versioned narrative source required')
    stamp=_stamp(recorded_at)
    episodes=[];diagnostics=[];offset=0
    for order,line in enumerate(text.splitlines(keepends=True),1):
        quote=line.rstrip('\r\n');m=_RECALL.fullmatch(quote);kind='RECOLLECTION' if m else None
        if not m:
            m=_CHALLENGE.fullmatch(quote)
            kind='CHALLENGE' if m else None
        if not m:
            m=_RECEIPT.fullmatch(quote)
            kind='RECEIPT' if m else None
        if not m:
            m=_DIRECT.fullmatch(quote)
            kind='DIRECT' if m else None
        if not m:
            if quote.strip():diagnostics.append(dict(narrative_order=order,start=offset,status='UNRESOLVED_TEMPORAL_FORM',quote=quote))
            offset+=len(line);continue
        row=m.groupdict();disclosure=_day(row['disclosure']);recall=_day(row.get('recall'))
        story=_day(row.get('story') or row['disclosure'])
        # Contradictory dates are preserved as an unresolved source claim, not
        # repaired or sorted into a fabricated event sequence.
        chronology='CONFLICTING_DECLARED_TIMES' if kind in ('RECOLLECTION','CHALLENGE') and not story<=recall<=disclosure else 'DECLARED_DATES_ONLY'
        if chronology=='CONFLICTING_DECLARED_TIMES':diagnostics.append(dict(narrative_order=order,status=chronology,quote=quote))
        reporter=row.get('reporter')
        actor=row.get('actor') or row.get('viewer') or row.get('challenger')
        ambiguous=actor in _AMBIGUOUS or reporter in _AMBIGUOUS
        authority={'RECOLLECTION':'ATTRIBUTED_RECOLLECTION_NOT_DIRECT_SELF_REPORT',
            'CHALLENGE':'SOURCE_REPORTED_CHALLENGE_NOT_FALSITY',
            'RECEIPT':'SOURCE_REPORTED_RECEIPT_NOT_BELIEF',
            'DIRECT':'NARRATED_SPEECH_NOT_VERIFIED_WORLD_FACT'}[kind]
        episodes.append(NarrativeEpisode(identity('narrative-episode',source_id,version,offset,quote),source_id,version,offset,offset+len(quote),quote,order,story,recall,disclosure,stamp,actor,reporter,row.get('body') or '',authority,
            'UNRESOLVED_REFERENCE' if ambiguous else 'SOURCE_LOCAL_NAMES',chronology))
        offset+=len(line)
    if len(episodes)>128:raise ValueError('narrative episode bound exceeded')
    return tuple(episodes),tuple(diagnostics)


@dataclass(frozen=True)
class NarrativeSnapshot:
    known_at:str
    source_versions:tuple
    observer:str|None
    payload_json:str

    @property
    def payload(self):return json.loads(self.payload_json)

    def messages(self,timeline,query,*,max_chars=96000):
        if not isinstance(query,str) or not query.strip() or len(query)>8000 or type(max_chars)is not int or not 1000<=max_chars<=128000:
            raise ValueError('bounded narrative query and context required')
        if self.source_versions!=timeline._selected_versions(self.known_at,self.observer):
            raise ValueError('historical source selection or access changed; resnapshot')
        messages=[dict(role='system',content=_POLICY),dict(role='user',content=json.dumps(dict(query=query,cognition=self.payload),ensure_ascii=False,sort_keys=True))]
        if len(json.dumps(messages,ensure_ascii=False))>max_chars:
            raise ValueError('narrative context budget exceeded')
        return messages


class NarrativeTimeline:
    """Versioned chapters; one projection keeps five separate temporal axes."""
    def __init__(self,*,max_chapters=16,max_episodes=256):
        if type(max_chapters)is not int or not 1<=max_chapters<=32 or type(max_episodes)is not int or not 1<=max_episodes<=512:
            raise ValueError('bounded narrative capacity required')
        self.max_chapters,self.max_episodes=max_chapters,max_episodes
        self._chapters={}

    def put_chapter(self,source_id,text,*,recorded_at,permitted_observers=()):
        if not isinstance(source_id,str) or not source_id or not isinstance(permitted_observers,tuple) or len(set(permitted_observers))!=len(permitted_observers) or any(not isinstance(a,str) or not a for a in permitted_observers):
            raise ValueError('source identity and explicit access required')
        if source_id not in self._chapters and len(self._chapters)>=self.max_chapters:
            raise ValueError('chapter capacity exceeded')
        stamp=_stamp(recorded_at)
        prior=self._chapters.get(source_id,())
        if prior and stamp<=prior[-1]['recorded_at']:
            raise ValueError('source correction requires later system record time')
        version=len(prior)+1
        episodes,diagnostics=parse_narrative_episodes(source_id,text,version=version,recorded_at=stamp)
        if sum(len(v[-1]['episodes']) for key,v in self._chapters.items() if key!=source_id)+len(episodes)>self.max_episodes:
            raise ValueError('narrative event capacity exceeded')
        record=dict(source_id=source_id,version=version,text=text,recorded_at=stamp,permitted_observers=permitted_observers,episodes=episodes,diagnostics=diagnostics)
        self._chapters[source_id]=(*prior,record)
        return version

    def _select(self,known_at,observer):
        stamp=_stamp(known_at)
        selected=[]
        for source_id,versions in sorted(self._chapters.items()):
            available=[r for r in versions if r['recorded_at']<=stamp]
            if not available:continue
            record=available[-1]
            # Current access revocation applies even when examining old records.
            if observer is not None and (observer not in versions[-1]['permitted_observers'] or observer not in record['permitted_observers']):continue
            selected.append(record)
        return tuple(selected)

    def _selected_versions(self,known_at,observer):
        return tuple((r['source_id'],r['version']) for r in self._select(known_at,observer))

    def snapshot(self,*,story_through,disclosed_through,known_at,observer=None,character=None,max_events=64):
        story_day,disclosure_day=_day(story_through),_day(disclosed_through)
        if type(max_events)is not int or not 1<=max_events<=128 or (character is not None and (not isinstance(character,str) or not character)):
            raise ValueError('bounded temporal projection required')
        selected=self._select(known_at,observer)
        workspace=CognitionWorkspace()
        for record in selected:
            workspace._versions[record['source_id']]=record['version']-1
            workspace.put_source(record['source_id'],record['text'],permitted_observers=record['permitted_observers'])
        episodic=EpisodicIndex(workspace,max_events=self.max_episodes)
        episodic.refresh(observer=observer)
        visible=[]
        for record in selected:
            for episode in record['episodes']:
                if episode.disclosure_time<=disclosure_day and (episode.story_time<=story_day or episode.authority=='SOURCE_REPORTED_RECEIPT_NOT_BELIEF'):
                    visible.append(episode)
        if len(visible)>max_events:raise ValueError('temporal view event budget exceeded; narrow dates or chapters')
        recalled=[e for e in visible if e.authority=='ATTRIBUTED_RECOLLECTION_NOT_DIRECT_SELF_REPORT']
        resolutions={}
        for episode in visible:
            if episode.authority=='SOURCE_REPORTED_CHALLENGE_NOT_FALSITY':
                anchors=[r for r in recalled if r.source_id==episode.source_id and
                    r.reference_status=='SOURCE_LOCAL_NAMES' and episode.reference_status=='SOURCE_LOCAL_NAMES' and
                    r.temporal_status=='DECLARED_DATES_ONLY' and episode.temporal_status=='DECLARED_DATES_ONLY' and
                    (r.reporter_surface,r.actor_surface,r.story_time,r.recall_time)==
                    (episode.reporter_surface,episode.actor_surface,episode.story_time,episode.recall_time) and r.disclosure_time<=episode.disclosure_time]
            elif episode.authority=='SOURCE_REPORTED_RECEIPT_NOT_BELIEF':
                # A receipt points to one reporter/day. Multiple possible records
                # are unresolved; do not choose a private communication path.
                reported=re.search(r'from (\d{4}-\d{2}-\d{2})\.$',episode.quote)
                anchors=[r for r in recalled if r.source_id==episode.source_id and
                    r.reference_status=='SOURCE_LOCAL_NAMES' and episode.reference_status=='SOURCE_LOCAL_NAMES' and
                    r.reporter_surface==episode.reporter_surface and reported and r.disclosure_time==reported[1]
                    and r.disclosure_time<=episode.disclosure_time]
            else:continue
            resolutions[episode.episode_id]=anchors[0].episode_id if len(anchors)==1 else None
        challenged={target for e in visible if e.authority=='SOURCE_REPORTED_CHALLENGE_NOT_FALSITY'
            for target in (resolutions.get(e.episode_id),) if target}
        receipt_links={target:e for e in visible if e.authority=='SOURCE_REPORTED_RECEIPT_NOT_BELIEF' and e.actor_surface==character
            for target in (resolutions.get(e.episode_id),) if target}
        rows=[]
        for episode in visible:
            if character is not None and episode.episode_id not in receipt_links:
                continue
            row=asdict(episode)
            row['episodic_event_ref']=identity('episode',episode.source_id,episode.source_version,episode.start,episode.end)
            # The F01 event is local and must match exact source bytes and
            # the historical version chosen by the known-at snapshot.
            indexed=episodic.fetch(row['episodic_event_ref'],observer=observer)
            if indexed['excerpt']!=episode.quote:
                raise ValueError('narrative and episodic source anchors differ')
            row['source_span_id']=indexed['source_span_id']
            row['challenge_status']='CONTESTED_SOURCE_RECOLLECTION_NOT_FALSIFIED' if episode.episode_id in challenged else 'NO_EXPLICIT_CHALLENGE_IN_VIEW'
            row['linked_episode_id']=resolutions.get(episode.episode_id)
            receipt=receipt_links.get(episode.episode_id)
            row['character_receipt']='EXPLICIT_REPORTED_RECEIPT_NOT_BELIEF' if receipt else 'NOT_ESTABLISHED'
            row['receipt_source']=dict(source_id=receipt.source_id,source_version=receipt.source_version,
                quote=receipt.quote,episode_id=receipt.episode_id) if receipt else None
            row['character_knowledge']='NOT_INFERRED'
            rows.append(row)
        rows.sort(key=lambda r:(r['source_id'],r['narrative_order']))
        relevant_sources={r['source_id'] for r in rows}|{r['receipt_source']['source_id'] for r in rows if r['receipt_source']}
        payload=dict(story_through=story_day,disclosed_through=disclosure_day,known_at=_stamp(known_at),
            observer=observer,character=character,source_versions=[v for v in self._selected_versions(known_at,observer) if character is None or v[0] in relevant_sources],
            narrative_order_scope='SOURCE_LOCAL_LINE_ORDER_NOT_CROSS_SOURCE_CHRONOLOGY',
            narrative_order_events=rows,story_order_event_ids=[r['episode_id'] for r in sorted(rows,key=lambda r:(r['story_time'],r['source_id'],r['narrative_order'])) if r['temporal_status']=='DECLARED_DATES_ONLY' and r['story_time']<=story_day],
            unresolved_temporal_event_ids=[r['episode_id'] for r in rows if r['temporal_status']!='DECLARED_DATES_ONLY'],
            character_access='SOURCE_REPORTED_RECEIPT_ONLY' if character else 'NOT_ASSESSED',
            source_completeness='BOUNDED_EXPLICIT_TEMPORAL_FORMS_ONLY',world_truth='NOT_ESTABLISHED',policy=_POLICY)
        return NarrativeSnapshot(_stamp(known_at),self._selected_versions(known_at,observer),observer,
            json.dumps(payload,ensure_ascii=False,sort_keys=True))
