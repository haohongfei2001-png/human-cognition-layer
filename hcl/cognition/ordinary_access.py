"""Ordinary explicit communication reports -> existing bounded B02 access checks.

No co-presence/watching/availability-to-comprehension inference. The normalization
is a syntactic representation, never a new original quotation or access certificate.
"""
import re
from .communication import CommunicationScene
from .semantic import _PRONOUNS

_NAME=r'[A-Z][\w-]{0,39}(?: [A-Z][\w-]{0,39})?'
_SPEECH=re.compile(rf'(?P<speaker>{_NAME}) (?:said|says|stated|replied|wrote|added|explained),? ["“](?P<body>[^"“”\r\n]+)["”]\.?')
_RECEIPT=re.compile(rf'(?P<actor>{_NAME}) (?P<verb>later heard|later read|heard|read|did not hear|did not read) (?P<speaker>{_NAME})\x27s last statement\.')
_AVAILABLE=re.compile(rf'(?P<speaker>{_NAME})\x27s last statement was publicly available\.')
_ADDRESSED=re.compile(rf'(?P<speaker>{_NAME}) sent their last statement privately to (?P<actor>{_NAME})\.')


def prepare_ordinary_access(text, *, source_id, version):
    """Complete bounded explicit grammar only; unsupported input stays unresolved.

    Roles and last-statement references are validated by the unchanged B02 scene.
    Aliases are reversible source-local names, not cross-document identity joins.
    Source-order later receipt preserves earlier reported non-receipt, never calendar
    access/comprehension or a private-state change.
    """
    if (not isinstance(text,str) or not text.strip() or len(text)>64000
            or not isinstance(source_id,str) or not source_id or type(version)is not int or version<1):
        raise ValueError('bounded authorized original source/revision required')
    lines=text.splitlines()
    if not 1<=len(lines)<=80:
        return dict(state=None,reason='COMMUNICATION_LINE_BUDGET',checked_operations=0)
    aliases={};bindings=[];normalized=[];access_count=0;offset=0
    def alias(name):
        if name.casefold() in _PRONOUNS:raise ValueError('ambiguous actor/reference remains unresolved')
        if name not in aliases:
            if len(aliases)==8:raise ValueError('communication actor budget exceeded')
            aliases[name]='Person'+str(len(aliases)+1)
        return aliases[name]
    try:
        for line_number,raw in enumerate(text.splitlines(keepends=True),1):
            line=raw.rstrip('\r\n');fragment=line.strip();start=offset+len(line)-len(line.lstrip());offset+=len(raw)
            if not fragment:continue
            speech=_SPEECH.fullmatch(fragment)
            receipt=_RECEIPT.fullmatch(fragment)
            available=_AVAILABLE.fullmatch(fragment)
            addressed=_ADDRESSED.fullmatch(fragment)
            if speech:
                # Do not normalize mixed opening/closing quotation conventions.
                quoted=fragment[fragment.find('"'):] if '"' in fragment else fragment[fragment.find('“'):]
                if not (quoted.rstrip('.').startswith('"') and quoted.rstrip('.').endswith('"') or quoted.rstrip('.').startswith('“') and quoted.rstrip('.').endswith('”')):
                    raise ValueError('ambiguous speech quotation')
                canonical=alias(speech['speaker'])+': '+speech['body']
            elif receipt:
                verb=receipt['verb'];later='later ' if verb.startswith('later ') else ''
                if later:verb=verb[len(later):]
                canonical='Narrator: '+alias(receipt['actor'])+' '+later+verb+' '+alias(receipt['speaker'])+"'s last statement."
                access_count+=1
            elif available:
                canonical='Narrator: '+alias(available['speaker'])+"'s last statement was publicly available."
                access_count+=1
            elif addressed:
                canonical='Narrator: '+alias(addressed['speaker'])+' sent their last statement privately to '+alias(addressed['actor'])+'.'
                access_count+=1
            else:
                raise ValueError('unsupported source may qualify communication reports; no partial access parse')
            normalized.append(canonical)
            bindings.append(dict(source_id=source_id,version=version,start=start,quote=fragment,
                original_source_line=line_number,derived_statement_line=len(normalized),
                derived_line=canonical,authority='LOCAL_SYNTAX_REPRESENTATION_NOT_ORIGINAL_QUOTATION'))
        if not access_count:return dict(state=None,reason='NO_EXPLICIT_RECEIPT_AVAILABILITY_OR_ADDRESS_REPORT',checked_operations=0)
        scene=CommunicationScene('\n'.join(normalized),source_id='derived-access-representation')
        views=[]
        for name,actor in aliases.items():
            view=scene.view(actor)
            views.append(dict(source_named_actor=name,representation_actor=actor,
                access_audit=list(view.access_audit),
                visible_derived_statements=[e.raw_text for e in view.events],
                view_authority='REPORTED_SOURCE_INFORMATION_ROUTE_NOT_PRIVATE_BELIEF',
                comprehension='NOT_ESTABLISHED',acceptance='NOT_ESTABLISHED',
                knowledge='NOT_ESTABLISHED',ignorance_from_missing_route='NOT_INFERRED'))
    except ValueError as exc:
        return dict(state=None,reason=str(exc),checked_operations=0)
    state=dict(schema='hcl-ordinary-reported-communication-v1',mechanism='EXISTING_B02_COMMUNICATION_SCENE',
        authority='SOURCE_REPORTED_ACCESS_UNDER_LITERAL_REPORT_FORM',
        source_id=source_id,source_version=version,source_local_actor_aliases=aliases,
        original_quote_bindings=bindings,views=views,
        temporal_semantics='SOURCE_ORDER_ONLY_NOT_CALENDAR_OR_RETROACTIVE_ACCESS',
        representation_quotable=False,private_state_established=False,world_receipt_verified=False,
        semantic_certification=False,shared_exposure_establishes_shared_belief=False)
    return dict(state=state,reason=None,checked_operations=len(views))
