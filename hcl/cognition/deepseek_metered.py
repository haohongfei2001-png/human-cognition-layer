"""Metered port over a caller-owned existing DeepSeek client; no credential setup.

Constructing this adapter makes no request. The UniversalHCL allowance is the
admission/journal gate. Every SDK request has zero retries and fixed finite bounds.
"""
from decimal import Decimal
import hashlib
import json
import queue
import threading

MODEL='deepseek-v4-pro'
MAX_REQUEST_BYTES=36000
OUTPUT_TOKENS={'planning':4096,'answer':8192}
OUTPUT_MARGIN=32
INPUT_RATE=Decimal('1.32')
OUTPUT_RATE=Decimal('3.96')


class MeteredPortError(RuntimeError):
    """Static safe code only, never provider exception bodies."""


class DeepSeekMeteredPort:
    provider_free=False
    cost_basis='USAGE_RATED_PEAK_NOT_INVOICE'

    def __init__(self, client, *, maximum_wait_seconds=180):
        if type(maximum_wait_seconds)not in (int,float)or not 0<maximum_wait_seconds<=600:raise MeteredPortError('FINITE_WALL_WAIT_REQUIRED')
        self.client=client;self.maximum_wait_seconds=maximum_wait_seconds;self._quoted=set();self._closed=False;self._validate_client()

    def _validate_client(self):
        if self._closed:raise MeteredPortError('PORT_CLOSED_AFTER_UNKNOWN_DEADLINE')
        if type(getattr(self.client,'max_retries',None))is not int or self.client.max_retries!=0:
            raise MeteredPortError('ZERO_SDK_RETRIES_REQUIRED')
        if str(getattr(self.client,'base_url','')).rstrip('/') not in ('https://api.deepseek.com','https://api.deepseek.com/v1'):
            raise MeteredPortError('EXISTING_DEEPSEEK_DESTINATION_REQUIRED')
        timeout=getattr(self.client,'timeout',None)
        values=[timeout] if type(timeout)in (int,float) else [getattr(timeout,k,None)for k in ('connect','read','write','pool')]
        if any(type(v)not in (int,float)or not 0<v<=600 for v in values):
            raise MeteredPortError('FINITE_SDK_TIMEOUT_REQUIRED')

    def request(self, phase, messages):
        self._validate_client()
        if phase not in OUTPUT_TOKENS or not isinstance(messages,list)or not messages:
            raise MeteredPortError('BOUNDED_PHASE_MESSAGES_REQUIRED')
        if any(not isinstance(m,dict)or set(m)!={'role','content'}or m['role']not in ('system','user','assistant')or not isinstance(m['content'],str)for m in messages):
            raise MeteredPortError('PLAIN_MESSAGE_SCHEMA_REQUIRED')
        request=dict(model=MODEL,max_tokens=OUTPUT_TOKENS[phase],response_format={'type':'json_object'},
            reasoning_effort='high',thinking={'type':'enabled'},messages=[{'role':m['role'],'content':m['content']}for m in messages])
        encoded=json.dumps(request,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
        if len(encoded)>MAX_REQUEST_BYTES:raise MeteredPortError('REQUEST_BOUND_EXCEEDED_NO_TRUNCATION')
        return request,encoded

    def reservation_usd(self, phase, messages):
        _,encoded=self.request(phase,messages)
        self._quoted.add((phase,hashlib.sha256(encoded).hexdigest()))
        input_bound=2*len(encoded)+2048
        return str((input_bound*INPUT_RATE+(OUTPUT_TOKENS[phase]+OUTPUT_MARGIN)*OUTPUT_RATE)/1000000)

    def complete(self, phase, messages):
        request,encoded=self.request(phase,messages)
        identity=(phase,hashlib.sha256(encoded).hexdigest())
        if identity not in self._quoted:raise MeteredPortError('EXACT_REQUEST_MUST_BE_RESERVED_FIRST')
        self._quoted.remove(identity)
        # No request/response bodies or exception text enter an error receipt.
        try:
            channel=queue.Queue(maxsize=1)
            def invoke():
                try:
                    result=self.client.chat.completions.create(**{k:v for k,v in request.items()if k!='thinking'},
                        extra_body={'thinking':request['thinking']})
                    channel.put((True,result))
                except BaseException:
                    channel.put((False,None))  # Never carry a provider exception body.
            threading.Thread(target=invoke,daemon=True).start()
            try: returned,result=channel.get(timeout=self.maximum_wait_seconds)
            except queue.Empty:
                self._closed=True
                raise MeteredPortError('DEADLINE_SEND_UNKNOWN_NO_RETRY') from None
            if not returned:raise MeteredPortError('PROVIDER_TRANSPORT_FAILURE_NO_RETRY')

            raw=result.model_dump(mode='json') if hasattr(result,'model_dump')else result
            if not isinstance(raw,dict)or raw.get('model')!=MODEL:raise MeteredPortError('MODEL_ID_OUTSIDE_FREEZE')
            usage=raw.get('usage')
            if not isinstance(usage,dict):raise MeteredPortError('NUMERIC_USAGE_REQUIRED')
            counts={key:usage.get(key)for key in ('prompt_tokens','completion_tokens')}
            if any(type(v)is not int or v<=0 for v in counts.values()):raise MeteredPortError('NUMERIC_USAGE_REQUIRED')
            if 'total_tokens'in usage and (type(usage['total_tokens'])is not int or usage['total_tokens']!=sum(counts.values())):
                raise MeteredPortError('INCONSISTENT_USAGE_UNKNOWN_COST')
            if counts['prompt_tokens']>2*len(encoded)+2048 or counts['completion_tokens']>OUTPUT_TOKENS[phase]+OUTPUT_MARGIN:
                raise MeteredPortError('USAGE_OUTSIDE_FROZEN_BOUND')
            choices=raw.get('choices')
            if not isinstance(choices,list)or len(choices)!=1 or choices[0].get('finish_reason')!='stop':raise MeteredPortError('INCOMPLETE_ANSWER_NO_RETRY')
            message=choices[0].get('message',{});text=message.get('content')
            if not isinstance(text,str)or len(text)>(32000 if phase=='planning'else 64000):raise MeteredPortError('CONTENT_BOUND_EXCEEDED')
            # reasoning_content, provider debugging and arbitrary metadata are
            # never returned. Cost is a conservative usage-rated peak estimate.
            rated=(counts['prompt_tokens']*INPUT_RATE+counts['completion_tokens']*OUTPUT_RATE)/1000000
            return dict(text=text,actual_usd=str(rated),usage=counts)
        except MeteredPortError:raise
        except Exception:raise MeteredPortError('PROVIDER_TRANSPORT_OR_SHAPE_FAILURE_NO_RETRY') from None
