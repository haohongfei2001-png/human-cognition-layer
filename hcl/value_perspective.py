"""Evidence-bounded method over public character descriptions; no moral solver."""
import json
THIN_METHOD = (
    "Internally list the character's action-relevant value priorities with exact supporting phrases. "
    "Separate earlier from current priorities and retain priorities for which no ordering is stated. "
    "Distinguish acknowledgment or challenge from explicit revision. Compare acceptance and rejection "
    "against those public anchors, and do not turn equal regard into a universal rule for indecision. "
    "Return the source-supported reading and retain unresolved alternatives without inventing private facts."
)
def source_view(row, profile):
    fields = {"situation": row["situation"], "action": row["action"], "character_description": profile}
    if any(not isinstance(v, str) or not v.strip() or len(v)>20000 for v in fields.values()):
        raise ValueError("bounded exact public anchors required")
    return fields | {"scope": "PUBLIC_CONSTRUCTED_CHARACTER_READING_NOT_HIDDEN_MENTAL_TRUTH"}
def request_messages(view, task, common, thin=False):
    return [{"role":"system","content":common+(" "+THIN_METHOD if thin else "")},
            {"role":"user","content":json.dumps({"source":view,"task":task},sort_keys=True)}]
