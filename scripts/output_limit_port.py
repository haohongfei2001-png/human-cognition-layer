"""Diagnostic-only 8192/16384 planning bounds; no production-runtime mutation."""
import json
from hcl.cognition.deepseek_metered import DeepSeekMeteredPort,MeteredPortError
from scripts.bounded_diagnostic_port import DiagnosticPort
from scripts.bounded_diagnostic_protocol import MAX_WAIT_SECONDS
from scripts.output_limit_protocol import MAX_REQUEST_BYTES


class OutputLimitPort(DiagnosticPort):
    def __init__(self,client,*,planning_tokens):
        if type(planning_tokens)is not int or planning_tokens not in (8192,16384):
            raise ValueError('FROZEN_OUTPUT_LIMIT_CONFIGURATION_REQUIRED')
        self.planning_tokens=planning_tokens;self.diagnostics={}
        DeepSeekMeteredPort.__init__(self,client,maximum_wait_seconds=MAX_WAIT_SECONDS)

    def request(self,phase,messages):
        request,_=DeepSeekMeteredPort.request(self,phase,messages)
        request['max_tokens']=self.planning_tokens if phase=='planning'else 8192
        encoded=json.dumps(request,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
        if len(encoded)>MAX_REQUEST_BYTES:raise MeteredPortError('REQUEST_BOUND_EXCEEDED_NO_TRUNCATION')
        return request,encoded
