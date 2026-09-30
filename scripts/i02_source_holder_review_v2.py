"""Explicit ordinary-question auditor interface; consumed v1 remains untouched."""
import json
from scripts.i02_source_holder_review import INSTRUCTION, validate_review

def messages(question, source_id, source):
    if any(not isinstance(x,str) or not x.strip() for x in (question,source_id,source)):
        raise ValueError('ordinary question, source identity and complete source required')
    return [dict(role='system',content=INSTRUCTION),dict(role='user',content=json.dumps(
        dict(question=question,sources=[dict(source_id=source_id,text=source)]),ensure_ascii=False))]
