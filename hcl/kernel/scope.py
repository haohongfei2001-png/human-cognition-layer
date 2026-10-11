"""Shared exact dependency checks; narrative claims never confer access."""
from collections.abc import Mapping

from hcl.kernel.types import HCLFailure, Principal, RULE_VERSION


def failure(status, code, field, message, stage="commit"):
    return HCLFailure(status, stage, code, field, message)


def identifier(value):
    if type(value) is not str or not value.strip():
        raise ValueError("nonempty identifier required")
    value.encode("utf-8")
    return value


def principal_identity(principal):
    if type(principal) is not Principal:
        raise ValueError("typed principal required")
    identifier(principal.tenant_id)
    identifier(principal.subject_id)


def version_map(read_set):
    if not isinstance(read_set, Mapping) or any(
        type(key) is not str or not key or type(version) is not int or version < 1
        for key, version in read_set.items()
    ):
        raise failure("INVALID_REQUEST", "INVALID_READ_SET", "read_set", "Exact positive source versions are required.")
    return dict(read_set)


def check_commit_contract(expected_revision, read_set, access_epoch, delta):
    version_map(read_set)
    if (type(expected_revision) is not int or expected_revision < 0
            or type(access_epoch) is not int or access_epoch < 0
            or type(delta.base_revision) is not int or type(delta.access_epoch) is not int
            or expected_revision != delta.base_revision or access_epoch != delta.access_epoch
            or dict(read_set) != version_map(delta.read_set)):
        raise failure("FAILED", "DELTA_CONTRACT_MISMATCH", "delta", "The commit contract is inconsistent.")
    if delta.rule_version != RULE_VERSION:
        raise failure("STALE_STATE", "RULE_VERSION_CHANGED", "rule_version", "The rule version is no longer current.")

