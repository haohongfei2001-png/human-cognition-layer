"""Construction states do not inherit historical efficacy dispositions."""
from types import MappingProxyType

PACKAGES = MappingProxyType({
    'A03': MappingProxyType(dict(
        implementation='CORRECTNESS_VERIFIED', ordinary_input='REPLAY_VERIFIED',
        efficacy='UNTESTED', activation='OPT_IN',
        entrypoint='hcl.cognition.assess_positions',
        limitation='source-local public expressions; challenges are disputes, not proof of negation')),
    'A02': MappingProxyType(dict(
        implementation='CORRECTNESS_VERIFIED', ordinary_input='REPLAY_VERIFIED',
        efficacy='UNTESTED', activation='OPT_IN',
        entrypoint='hcl.cognition.prepare_semantics',
        limitation='local explicit speech forms; general backend proposals remain unverified')),
    'A01': MappingProxyType(dict(
        implementation='CORRECTNESS_VERIFIED', ordinary_input='REPLAY_VERIFIED',
        efficacy='UNTESTED', activation='OPT_IN',
        entrypoint='hcl.cognition.CognitionWorkspace',
        limitation='bounded retained v1 ordinary grammar; analyst view only')),
})
