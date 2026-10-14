"""Additive bounded lossless capsule for v3's repeated finite proof branches.

The existing JSON contract and old proofs are unchanged. This is compression,
not authentication or read authority; callers still rebind sources and replay.
"""
import base64
from hashlib import sha256
import zlib
from hcl.kernel.types import InferenceResult, thaw
from hcl.memory import codec

SCHEMA = "hcl-concept-proof-capsule-1"
MAX_BYTES = 4 * 1024 * 1024
REPAIR_KIND = "CONDITIONAL_CONCEPT_REPAIR_JUDGMENT"


def pack_proof(result):
    if result.kind != REPAIR_KIND:
        return codec.encode(result)
    body = codec.dumps(result)
    if len(body)>MAX_BYTES:
        raise ValueError("repair proof exceeds the existing audit capacity")
    return dict(schema=SCHEMA,uncompressed_bytes=len(body),sha256=sha256(body).hexdigest(),
        zlib_base64=base64.b64encode(zlib.compress(body,9)).decode("ascii"))


def unpack_proof(encoded):
    encoded=thaw(encoded)
    if type(encoded) is not dict or encoded.get("schema")!=SCHEMA:
        return codec.decode(encoded)
    if set(encoded)!={"schema","uncompressed_bytes","sha256","zlib_base64"}:
        raise ValueError("proof capsule fields changed")
    size=encoded["uncompressed_bytes"]
    if type(size) is not int or not 0<size<=MAX_BYTES or type(encoded["zlib_base64"]) is not str or len(encoded["zlib_base64"])>2*MAX_BYTES:
        raise ValueError("bounded proof capsule required")
    compressed=base64.b64decode(encoded["zlib_base64"],validate=True)
    decoder=zlib.decompressobj()
    try:
        body=decoder.decompress(compressed,size+1)
    except zlib.error:
        raise ValueError("invalid compressed proof") from None
    if (len(body)!=size or not decoder.eof or decoder.unconsumed_tail or decoder.unused_data
            or sha256(body).hexdigest()!=encoded["sha256"]):
        raise ValueError("proof capsule integrity or size changed")
    result=codec.loads(body)
    if type(result) is not InferenceResult or result.kind!=REPAIR_KIND:
        raise ValueError("capsule only holds additive repair proofs")
    # Require one deterministic wire representation, not equivalent encodings.
    if pack_proof(result)!=encoded:
        raise ValueError("noncanonical proof capsule")
    return result
