"""Construction states do not inherit historical efficacy dispositions."""
from types import MappingProxyType

PACKAGES = MappingProxyType({
    'A01': MappingProxyType(dict(
        implementation='CORRECTNESS_VERIFIED', ordinary_input='REPLAY_VERIFIED',
        efficacy='UNTESTED', activation='OPT_IN',
        entrypoint='hcl.cognition.CognitionWorkspace',
        limitation='bounded retained v1 ordinary grammar; analyst view only')),
})
