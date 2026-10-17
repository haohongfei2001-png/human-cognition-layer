"""DeepSeek's documented wire, separate from the disconnected OpenAI fixture.

API and tariff references are in deepseek_contracts. Only final visible content
and mechanical usage survive parsing. Reasoning text is never retained.
"""
import json
from hcl.models.candidate_protocol import SYSTEM, strict_json
from hcl.models.deepseek_contracts import (
    PROTOCOL, MODEL, MODEL_VERSION, CONTEXT_TOKENS, OUTPUT_TOKENS, MAX_RESPONSE_BYTES,
    INPUT_RATE, CACHE_RATE, OUTPUT_RATE, RESERVATION_NANOYUAN, DeepSeekCandidateReturn,
)


def request_body(context):
    return json.dumps(dict(model=MODEL,
        messages=[dict(role="system", content=SYSTEM), dict(role="user", content=context)],
        response_format=dict(type="json_object"), max_tokens=OUTPUT_TOKENS,
        thinking=dict(type="disabled"), reasoning_effort="none", temperature=0,
        tool_choice="none", stream=False), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def parse_return(raw, max_visible_bytes):
    content = response_id = model = finish = None
    prompt = cached = uncached = output = reasoning = cost = None
    error = None
    try:
        if type(raw) is not bytes or len(raw) > MAX_RESPONSE_BYTES:
            raise ValueError("response capacity")
        data = strict_json(raw.decode("utf-8"))
        if type(data) is not dict:
            raise ValueError("response object required")
        def text(value):
            return value if type(value) is str and 0 < len(value) <= 256 and all(ord(c) >= 32 for c in value) else None
        response_id, model = text(data.get("id")), text(data.get("model"))
        choices = data.get("choices")
        if type(choices) is list and len(choices) == 1 and type(choices[0]) is dict:
            choice = choices[0]
            finish = text(choice.get("finish_reason"))
            message = choice.get("message")
            if type(message) is dict:
                value = message.get("content")
                if type(value) is str and len(value.encode("utf-8")) <= max_visible_bytes:
                    content = value
                if (message.get("role") != "assistant" or message.get("tool_calls")
                        or message.get("function_call") or message.get("refusal") is not None
                        or message.get("reasoning_content") not in (None, "")):
                    error = "DEEPSEEK_UNEXPECTED_MESSAGE"
            if type(choice.get("index")) is not int or choice["index"] != 0:
                error = "DEEPSEEK_CHOICE_INVALID"
        else:
            error = "DEEPSEEK_CHOICE_INVALID"
        usage = data.get("usage")
        if type(usage) is dict:
            p, c, t, h, m = (usage.get(k) for k in ("prompt_tokens", "completion_tokens", "total_tokens",
                                                  "prompt_cache_hit_tokens", "prompt_cache_miss_tokens"))
            details, completion_details = usage.get("prompt_tokens_details"), usage.get("completion_tokens_details")
            r = completion_details.get("reasoning_tokens", 0) if type(completion_details) is dict else 0
            allowed = {"prompt_tokens", "completion_tokens", "total_tokens", "prompt_cache_hit_tokens",
                       "prompt_cache_miss_tokens", "prompt_tokens_details", "completion_tokens_details"}
            valid = (set(usage) <= allowed and all(type(v) is int and 0 <= v <= 10**12 for v in (p,c,t,h,m,r))
                     and p > 0 and c > 0 and t == p+c and h+m == p and r <= c)
            valid = valid and (details is None or (type(details) is dict and set(details) == {"cached_tokens"}
                             and type(details["cached_tokens"]) is int and details["cached_tokens"] == h))
            valid = valid and (completion_details is None or (type(completion_details) is dict
                             and set(completion_details) <= {"reasoning_tokens"}))
            if valid:
                prompt, output, cached, uncached, reasoning = p, c, h, m, r
        if model not in (MODEL, MODEL_VERSION):
            error = "DEEPSEEK_MODEL_MISMATCH"
        elif response_id is None or data.get("object") != "chat.completion":
            error = "DEEPSEEK_IDENTITY_INVALID"
        elif prompt is None:
            error = "DEEPSEEK_USAGE_UNKNOWN"
        else:
            cost = uncached*INPUT_RATE + cached*CACHE_RATE + output*OUTPUT_RATE
            if prompt > CONTEXT_TOKENS or output > OUTPUT_TOKENS or prompt+output > CONTEXT_TOKENS:
                error = "DEEPSEEK_TOKEN_OVERSPEND"
            elif cost > RESERVATION_NANOYUAN:
                error = "DEEPSEEK_COST_OVERSPEND"
            elif reasoning:
                error = "DEEPSEEK_UNEXPECTED_REASONING"
            elif finish != "stop":
                error = "DEEPSEEK_FINISH_REJECTED"
            elif not content or not content.strip():
                error = "DEEPSEEK_VISIBLE_CONTENT_INVALID"
    except (ValueError, TypeError, RecursionError, UnicodeError, OverflowError):
        error = "DEEPSEEK_PROTOCOL_INVALID"
        content = None
    return DeepSeekCandidateReturn(PROTOCOL, content, response_id, model, finish,
                                  prompt, cached, uncached, output, reasoning, cost, error)
