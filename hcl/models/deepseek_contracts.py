"""Separate native-CNY contracts. Decoding these never grants network authority.

All monetary integers are nanoyuan (1 CNY = 10**9), never simulated USD nanos.
A host must verify the current tariff and existing account's CNY denomination;
this module has no credential discovery, currency conversion or account setup.
"""
from dataclasses import dataclass
from pathlib import Path
from hcl.kernel.types import freeze

PROTOCOL = "hcl-deepseek-cny-1"
MODE = "NATIVE_CNY_USAGE_UPPER_BOUND"
MODEL = "deepseek-v4-pro"
MODEL_VERSION = "DeepSeek-V4-Pro-0813"
ENDPOINT = "https://api.deepseek.com/chat/completions"
PRICING_URL = "https://api-docs.deepseek.com/zh-cn/quick_start/pricing/"
API_URL = "https://api-docs.deepseek.com/api/create-chat-completion/"
RATE_VERSION = "deepseek-v4-pro-0813-cny-peak-9-0.30-27-20261017"
CONTEXT_TOKENS = 1048576
OUTPUT_TOKENS = 16384
OUTPUT_MARGIN = 32
INPUT_RATE, CACHE_RATE, OUTPUT_RATE = 9000, 300, 27000
RESERVATION_NANOYUAN = CONTEXT_TOKENS * INPUT_RATE + (OUTPUT_TOKENS + OUTPUT_MARGIN) * OUTPUT_RATE
MAX_REQUEST_BYTES = 1048576
MAX_RESPONSE_BYTES = 1048576
MAX_VISIBLE_BYTES = 262144


def digest(value):
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError("exact SHA256 required")


@dataclass(frozen=True)
class DeepSeekBatchAuthorization:
    batch_id: str
    ledger_path: str
    state_store_path: str
    task_fingerprints: tuple
    verified_at: int
    expires_at: int
    account_currency: str
    account_scope: str
    source_policy: str
    max_calls: int = 2
    max_cost_nanoyuan: int = 20000000000
    rate_version: str = RATE_VERSION
    model: str = MODEL
    model_version: str = MODEL_VERSION
    mode: str = MODE

    def __post_init__(self):
        from hcl.kernel.scope import identifier
        identifier(self.batch_id)
        if len(self.batch_id) > 128:
            raise ValueError("bounded batch identity required")
        for path in (self.ledger_path, self.state_store_path):
            if type(path) is not str or not Path(path).is_absolute() or str(Path(path).resolve()) != path:
                raise ValueError("canonical absolute host paths required")
        if self.ledger_path == self.state_store_path:
            raise ValueError("separate CNY ledger required")
        if type(self.task_fingerprints) is not tuple or not 1 <= len(self.task_fingerprints) <= 2:
            raise ValueError("bounded explicit task bindings required")
        if len(set(self.task_fingerprints)) != len(self.task_fingerprints):
            raise ValueError("duplicate task binding")
        for value in self.task_fingerprints:
            digest(value)
        if (type(self.verified_at) is not int or type(self.expires_at) is not int
                or not 0 < self.expires_at - self.verified_at <= 900):
            raise ValueError("fresh host tariff/account verification with at most 15 minute validity required")
        if (self.account_currency != "CNY" or self.account_scope != "HCL_CORE_DEEPSEEK_DIRECT"
                or self.source_policy != "SYNTHETIC_ONLY" or self.rate_version != RATE_VERSION
                or self.model != MODEL or self.model_version != MODEL_VERSION or self.mode != MODE):
            raise ValueError("unknown account, scope, tariff, model or currency")
        if (type(self.max_calls) is not int or not 1 <= self.max_calls <= 2
                or type(self.max_cost_nanoyuan) is not int
                or not RESERVATION_NANOYUAN <= self.max_cost_nanoyuan <= 20000000000):
            raise ValueError("bounded native-CNY grant required")


@dataclass(frozen=True)
class DeepSeekCandidateRequest:
    protocol: str
    batch_id: str
    authorization_hash: str
    claim_id: str
    task_fingerprint: str
    source_versions: object
    context: str
    body: str
    reservation_nanoyuan: int = RESERVATION_NANOYUAN

    def __post_init__(self):
        from hcl.kernel.scope import identifier, version_map
        if self.protocol != PROTOCOL or self.reservation_nanoyuan != RESERVATION_NANOYUAN:
            raise ValueError("native-CNY request required")
        identifier(self.batch_id)
        for value in (self.authorization_hash, self.claim_id, self.task_fingerprint):
            digest(value)
        version_map(self.source_versions)
        object.__setattr__(self, "source_versions", freeze(self.source_versions))


@dataclass(frozen=True)
class DeepSeekCandidateReturn:
    protocol: str
    visible_text: str | None
    provider_response_id: str | None
    model: str | None
    finish_reason: str | None
    input_tokens: int | None
    cached_input_tokens: int | None
    uncached_input_tokens: int | None
    output_tokens: int | None
    reasoning_tokens: int | None
    usage_cost_upper_nanoyuan: int | None
    validation_code: str | None

    def __post_init__(self):
        if self.protocol != PROTOCOL:
            raise ValueError("native-CNY return required")
