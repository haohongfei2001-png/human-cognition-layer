"""Additive, credential-free candidate transport contracts; no live authority.

These classes do not change any historical wire class or SQLite column. Only
an explicitly installed host gateway can register a grant; decoding one cannot.
"""
from dataclasses import dataclass
from hcl.kernel.types import freeze

MODE = "DISCONNECTED_PROTOCOL_SIMULATION"
PROTOCOL = "hcl-metered-candidate-call-1"


@dataclass(frozen=True)
class CandidateAuthorization:
    authorization_id: str
    provider: str
    model: str
    source_versions: object
    max_calls: int
    max_cost_nanos: int
    max_input_tokens: int
    max_output_tokens: int
    rate_version: str
    input_nanos_per_token: int
    cached_input_nanos_per_token: int
    output_nanos_per_token: int
    task_fingerprint: str
    mode: str = MODE

    def __post_init__(self):
        from hcl.kernel.scope import identifier, version_map
        for value in (self.authorization_id, self.provider, self.model, self.rate_version):
            identifier(value)
            if len(value) > 256:
                raise ValueError("bounded authorization identity required")
        if (type(self.task_fingerprint) is not str or len(self.task_fingerprint) != 64
                or any(c not in "0123456789abcdef" for c in self.task_fingerprint)):
            raise ValueError("exact task fingerprint required")
        version_map(self.source_versions)
        if not self.source_versions or self.mode != MODE:
            raise ValueError("only source-bound disconnected authorization is installed")
        bounds = dict(max_calls=64, max_cost_nanos=10**15, max_input_tokens=4194304,
                      max_output_tokens=1048576, input_nanos_per_token=10**9,
                      cached_input_nanos_per_token=10**9, output_nanos_per_token=10**9)
        for name, limit in bounds.items():
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= limit:
                raise ValueError("finite integer authorization limits required")
        if min(self.max_calls, self.max_input_tokens, self.max_output_tokens) < 1:
            raise ValueError("positive call and token limits required")
        if self.cached_input_nanos_per_token > self.input_nanos_per_token:
            raise ValueError("cached input rate cannot exceed reserved input rate")
        object.__setattr__(self, "source_versions", freeze(self.source_versions))

    @classmethod
    def for_request(cls, request, **limits):
        """Host convenience: explicitly bind all ordinary-input/task fields."""
        from hashlib import sha256
        from hcl.memory import codec
        return cls(source_versions={h.source_id: h.version for h in request.source_handles},
                   task_fingerprint=sha256(codec.dumps(request)).hexdigest(), **limits)

    @property
    def reservation_nanos(self):
        return (self.max_input_tokens * self.input_nanos_per_token
                + self.max_output_tokens * self.output_nanos_per_token)


@dataclass(frozen=True)
class MeteredCandidateRequest:
    protocol: str
    authorization: CandidateAuthorization
    task_fingerprint: str
    context: str
    body: str

    def __post_init__(self):
        if (self.protocol != PROTOCOL or type(self.authorization) is not CandidateAuthorization
                or self.task_fingerprint != self.authorization.task_fingerprint):
            raise ValueError("versioned candidate call required")


@dataclass(frozen=True)
class MeteredCandidateReturn:
    protocol: str
    visible_text: str | None
    provider_response_id: str | None
    model: str | None
    finish_reason: str | None
    input_tokens: int | None
    cached_input_tokens: int | None
    output_tokens: int | None
    settled_nanos: int | None
    validation_code: str | None

    def __post_init__(self):
        if self.protocol != PROTOCOL:
            raise ValueError("versioned candidate return required")
