"""Frozen diagnostic transport configuration; production HCL runtime stays unchanged."""
from decimal import Decimal
import hashlib
import json
import queue
import threading

from hcl.cognition.deepseek_metered import DeepSeekMeteredPort, MeteredPortError, MODEL, INPUT_RATE, OUTPUT_RATE, OUTPUT_MARGIN
from scripts.bounded_diagnostic_protocol import MAX_REQUEST_BYTES, MAX_WAIT_SECONDS


class DiagnosticPort(DeepSeekMeteredPort):
    def __init__(self,client,*,planning_tokens):
        if type(planning_tokens)is not int or planning_tokens not in (4096,8192):
            raise ValueError('FROZEN_DIAGNOSTIC_CONFIGURATION_REQUIRED')
        self.planning_tokens=planning_tokens;self.diagnostics={}
        super().__init__(client,maximum_wait_seconds=MAX_WAIT_SECONDS)

    def _validate_client(self):
        super()._validate_client()
        timeout=self.client.timeout
        values=[timeout]if type(timeout)in (int,float)else [getattr(timeout,k,None)for k in ('connect','read','write','pool')]
        if any(v>MAX_WAIT_SECONDS for v in values):raise MeteredPortError('FINITE_SDK_TIMEOUT_REQUIRED')

    def request(self,phase,messages):
        request,_=super().request(phase,messages)
        request['max_tokens']=self.planning_tokens if phase=='planning' else 8192
        encoded=json.dumps(request,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
        if len(encoded)>MAX_REQUEST_BYTES:raise MeteredPortError('REQUEST_BOUND_EXCEEDED_NO_TRUNCATION')
        return request,encoded

    def reservation_usd(self,phase,messages):
        request,encoded=self.request(phase,messages)
        self._quoted.add((phase,hashlib.sha256(encoded).hexdigest()))
        return str(((2*len(encoded)+2048)*INPUT_RATE+(request['max_tokens']+OUTPUT_MARGIN)*OUTPUT_RATE)/1000000)

    def complete(self,phase,messages):
        request,encoded=self.request(phase,messages)
        identity=(phase,hashlib.sha256(encoded).hexdigest())
        if identity not in self._quoted:raise MeteredPortError('EXACT_REQUEST_MUST_BE_RESERVED_FIRST')
        self._quoted.remove(identity);self.diagnostics={}
        try:
            channel=queue.Queue(maxsize=1)
            def invoke():
                try:
                    result=self.client.chat.completions.create(**{k:v for k,v in request.items()if k!='thinking'},
                        extra_body={'thinking':request['thinking']})
                    channel.put((True,result))
                except BaseException:channel.put((False,None))
            threading.Thread(target=invoke,daemon=True).start()
            try:returned,result=channel.get(timeout=self.maximum_wait_seconds)
            except queue.Empty:
                self._closed=True
                raise MeteredPortError('DEADLINE_SEND_UNKNOWN_NO_RETRY') from None
            if not returned:raise MeteredPortError('PROVIDER_TRANSPORT_FAILURE_NO_RETRY')
            self.diagnostics.update(response_returned=True,usage_valid=False)
            raw=result.model_dump(mode='json')if hasattr(result,'model_dump')else result
            if not isinstance(raw,dict)or raw.get('model')!=MODEL:raise MeteredPortError('MODEL_ID_OUTSIDE_FREEZE')
            usage=raw.get('usage')
            if not isinstance(usage,dict):raise MeteredPortError('NUMERIC_USAGE_REQUIRED')
            counts={key:usage.get(key)for key in ('prompt_tokens','completion_tokens')}
            if any(type(v)is not int or v<=0 for v in counts.values()):raise MeteredPortError('NUMERIC_USAGE_REQUIRED')
            if 'total_tokens'in usage and (type(usage['total_tokens'])is not int or usage['total_tokens']!=sum(counts.values())):
                raise MeteredPortError('INCONSISTENT_USAGE_UNKNOWN_COST')
            if counts['prompt_tokens']>2*len(encoded)+2048 or counts['completion_tokens']>request['max_tokens']+OUTPUT_MARGIN:
                raise MeteredPortError('USAGE_OUTSIDE_FROZEN_BOUND')
            self.diagnostics.update(usage=counts,usage_valid=True)
            details=usage.get('completion_tokens_details')
            reasoning=details.get('reasoning_tokens')if isinstance(details,dict)else None
            if type(reasoning)is int and 0<=reasoning<=counts['completion_tokens']:
                self.diagnostics['reasoning_tokens']=reasoning
            choices=raw.get('choices')
            if isinstance(choices,list):
                if len(choices)<=100:self.diagnostics['choice_count']=len(choices)
                known={'stop','length','content_filter','tool_calls','function_call'}
                self.diagnostics['finish_reasons']=[c.get('finish_reason')if isinstance(c,dict)and type(c.get('finish_reason'))is str and c['finish_reason']in known else 'OTHER_OR_MISSING'for c in choices[:10]]
            message=choices[0].get('message')if isinstance(choices,list)and len(choices)==1 and isinstance(choices[0],dict)else None
            content=message.get('content')if isinstance(message,dict)else None
            self.diagnostics['content_kind']='EMPTY'if content==''else 'TEXT'if isinstance(content,str)else 'MISSING_OR_NON_TEXT'
            if isinstance(content,str)and len(content)<=64000:
                self.diagnostics.update(content_chars=len(content),content_utf8_bytes=len(content.encode()))
            if not isinstance(choices,list)or len(choices)!=1 or not isinstance(choices[0],dict)or choices[0].get('finish_reason')!='stop':
                raise MeteredPortError('INCOMPLETE_ANSWER_NO_RETRY')
            if not isinstance(content,str)or len(content)>(32000 if phase=='planning'else 64000):
                raise MeteredPortError('CONTENT_BOUND_EXCEEDED')
            rated=(counts['prompt_tokens']*INPUT_RATE+counts['completion_tokens']*OUTPUT_RATE)/1000000
            return dict(text=content,actual_usd=str(rated),usage=counts)
        except MeteredPortError as error:
            error.diagnostics={k:v for k,v in self.diagnostics.items()if k in ('usage','choice_count','finish_reasons')}
            raise
        except Exception:
            error=MeteredPortError('PROVIDER_TRANSPORT_OR_SHAPE_FAILURE_NO_RETRY')
            error.diagnostics={k:v for k,v in self.diagnostics.items()if k in ('usage','choice_count','finish_reasons')}
            raise error from None
