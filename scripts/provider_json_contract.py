"""Pure pre-transport JSON mode guard/error receipt for future provider drivers.

Frozen historical drivers stay unchanged. No transport, retry or credentials here.
"""
import re

def validate_json_mode_request(request):
    mode=request.get('response_format',{})
    if not isinstance(mode,dict):raise ValueError('invalid response format')
    if mode.get('type')!='json_object':return True
    messages=request.get('messages')
    if (not isinstance(messages,list) or not messages or
            not any(isinstance(m,dict) and isinstance(m.get('content'),str)
                    and m.get('role') in ('system','developer') and re.search(r'\bjson\b',m['content'],re.I) for m in messages)):
        raise ValueError('JSON response mode requires an explicit JSON instruction before transport')
    return True


def provider_error_receipt(exc, *, redactions=()):
    """Keep available HTTP error fields; absent status/body/headers stay unknown."""
    response=getattr(exc,'response',None);body=getattr(exc,'body',None)
    if body is None and response is not None:
        try:body=response.json()
        except (ValueError,AttributeError):body=getattr(response,'text',None)
    headers=getattr(response,'headers',{}) or {}
    # Never publish transport authorization/cookies. Raw provider error body is
    # separate from successful model output; failed usage/cost cannot be invented.
    def redact(value):
        if isinstance(value,str):
            for secret in redactions:
                if isinstance(secret,str) and secret:value=value.replace(secret,'<REDACTED_EXISTING_CREDENTIAL>')
            return value
        if isinstance(value,list):return [redact(x) for x in value]
        if isinstance(value,dict):return {k:redact(v) for k,v in value.items()}
        return value
    allowed={'request-id','x-request-id','date','content-type'}
    return dict(failure_type=type(exc).__name__,http_status=getattr(exc,'status_code',None),
        error_body=redact(body),credential_redaction_requested=bool(redactions),response_headers={k:redact(v) for k,v in headers.items() if k.lower() in allowed},
        request_id=getattr(exc,'request_id',None),usage=None,actual_cost_usd=None,
        retry_performed=False,successful_model_response=False)
