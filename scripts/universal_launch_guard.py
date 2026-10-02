"""One grant, one admitted run across manual and exact marker-trigger routes."""
import json,os,subprocess
from pathlib import Path

MARKER=Path('.github/HCL_UNIVERSAL_DEVELOPMENT_TRIGGER.json')
AUTHORIZATION='OWNER_APPROVED_2026_10_02_NEW_2_50_18_CALLS'


def verify_run_history(run_id,attempt,runs):
    if str(attempt)!='1':raise ValueError('NO_WORKFLOW_RETRY')
    eligible=[r for r in runs if r.get('event')in ('push','workflow_dispatch')]
    if not eligible or any(type(r.get('id'))is not int or not isinstance(r.get('created_at'),str)for r in eligible):
        raise ValueError('COMPLETE_CURRENT_RUN_HISTORY_REQUIRED')
    first=min(eligible,key=lambda r:(r['created_at'],r['id']))
    if str(first['id'])!=str(run_id):raise ValueError('GRANT_ALREADY_HAS_EARLIER_RUN')
    return True


def verify_marker(marker,package_sha256,grant_sha256,parent,changed_paths):
    expected=dict(schema='hcl-universal-single-launch-marker-v1',authorization_ref=AUTHORIZATION,
        package_sha256=package_sha256,grant_sha256=grant_sha256,executor_commit=parent)
    if (marker!=expected or not isinstance(parent,str)or len(parent)!=40
            or any(c not in '0123456789abcdef'for c in parent)
            or changed_paths!=[str(MARKER)]):
        raise ValueError('EXACT_REVIEWED_EXECUTOR_MARKER_ONLY_COMMIT_REQUIRED')
    return True


def verify_execution_event(package_sha256,grant_sha256):
    event=os.environ.get('GITHUB_EVENT_NAME')
    if event=='workflow_dispatch':return True
    if event!='push':raise ValueError('UNSUPPORTED_LAUNCH_EVENT')
    ancestry=subprocess.check_output(['git','rev-list','--parents','-n','1','HEAD'],text=True).split()
    if len(ancestry)!=2:raise ValueError('SINGLE_PARENT_MARKER_COMMIT_REQUIRED')
    parent=ancestry[1]
    paths=subprocess.check_output(['git','diff-tree','--no-commit-id','--name-only','-r','HEAD'],text=True).splitlines()
    return verify_marker(json.loads(MARKER.read_text()),package_sha256,grant_sha256,parent,paths)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--run-history',required=True);args=parser.parse_args()
    pages=json.loads(Path(args.run_history).read_text())
    runs=[run for page in pages for run in page['workflow_runs']]
    verify_run_history(os.environ['GITHUB_RUN_ID'],os.environ['GITHUB_RUN_ATTEMPT'],runs)
    print('SINGLE_GRANT_RUN_ADMISSION_PASS')
