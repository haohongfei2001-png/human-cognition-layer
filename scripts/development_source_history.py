"""Current provider-free entry for fresh development-source history screening.

This gate is not a rights decision, freshness proof, final qualification or live
experiment grant. Consumed replay packages keep their exact historical scanners.
"""
import subprocess

from scripts.i02_exposure_history_v3 import audit_history, _git


def screen_development_source(repository, source):
    # A shallow checkout can omit the very prior path needed to identify a
    # renamed sealed blob. Refuse it before the scanner reads any blob content.
    shallow = _git(repository, 'rev-parse', '--is-shallow-repository').decode().strip()
    if shallow != 'false':
        raise ValueError('complete reachable history required before source screening')
    try:
        partial = _git(repository, 'config', '--get-regexp',
            r'^(extensions\.partialclone|remote\..*\.(promisor|partialclonefilter))$')
    except subprocess.CalledProcessError as error:
        if error.returncode != 1:
            raise
        partial = b''  # Git status 1 means no matching configuration key.
    if partial.strip():
        raise ValueError('partial/promisor repositories require complete local history before screening')
    receipt = audit_history(repository, source)
    return dict(schema='hcl-development-source-history-preflight-v1',
        history=receipt,
        history_clear=receipt['status'] == 'REACHABLE_HISTORY_NO_TEXT_MATCH',
        rights_verified=False, source_qualified=False, confirmation_qualified=False,
        provider_calls=0, maximum_authorized_calls=0, authorized_spend_usd=0,
        live_execution_enabled=False,
        remaining_gates=['SOURCE_RIGHTS_AND_NATIVE_TASK_REVIEW',
                         'SUBSET_MODEL_SCORER_AND_INPUT_FREEZE',
                         'NEW_EXPLICIT_BOUNDED_BUDGET'],
        limits='CURRENTLY_REACHABLE_FULL_CHECKOUT_ONLY_NOT_DELETED_REFS_OR_MODEL_TRAINING')
