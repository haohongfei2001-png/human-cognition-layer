"""Immutable DRE001 input replay; no provider transport or historical rescoring."""
import hashlib,json,os,subprocess,sys,tempfile,zipfile
from pathlib import Path
CERT=Path('reports/HCL_DRE001_CERTIFIED_REPLAY.json')
ARCHIVE=Path('reports/HCL_DRE001_CERTIFIED_REPLAY.zip')
PACKAGE=Path('reports/HCL_DRE001_PACKAGE.json')
GRANT=Path('.github/HCL_DRE001_GRANT.json')
CERT_SHA='a80931b83f02d46c2e4e2e8e97fd9836d969ca5e28fbdaf817628ce8772580a8'
RUN_SHA='14e24dcb43549b8bd28a78254a1d62e306a483f0'
def digest(raw):return hashlib.sha256(raw).hexdigest()
def validate_archive():
    raw=CERT.read_bytes()
    if digest(raw)!=CERT_SHA:raise ValueError('DRE001 certificate drift')
    cert=json.loads(raw)
    if cert['run_sha']!=RUN_SHA or cert['replay_allowed']!='PROVIDER_FREE_ONLY_NEVER_EXECUTE':raise ValueError('replay boundary drift')
    raw=ARCHIVE.read_bytes()
    if digest(raw)!=cert['archive_sha256'] or len(raw)!=cert['archive_size_bytes']:raise ValueError('archive drift')
    with zipfile.ZipFile(ARCHIVE) as archive:
        names=archive.namelist()
        if len(names)!=len(set(names)) or set(names)!=set(cert['files']):raise ValueError('archive membership drift')
        runtime={}
        for name,row in cert['files'].items():
            if Path(name).is_absolute() or '..' in Path(name).parts or 'longmemeval' in name.casefold() or not name.startswith(('hcl/','scripts/','tests/','reports/','docs/','.github/')):raise ValueError('unsafe archive path')
            body=archive.read(name)
            blob=hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()
            if digest(body)!=row['sha256'] or len(body)!=row['size_bytes'] or blob!=row['git_blob_sha1']:raise ValueError('certified Git blob drift')
            if name.startswith('hcl/') and name.endswith('.py'):runtime[name]=digest(body)
        body=archive.read(str(PACKAGE));p=json.loads(body)
        actual=digest(json.dumps(p,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())
        runtime_sha=digest(json.dumps(runtime,sort_keys=True,separators=(',',':')).encode())
        if PACKAGE.read_bytes()!=body or actual!=cert['package_sha256'] or runtime_sha!=cert['runtime_sha256'] or runtime_sha!=p['runtime_sha256']:raise ValueError('frozen package/runtime drift')
        if any(cert['files'][n]['sha256']!=sha for n,sha in p['execution_files'].items()):raise ValueError('execution drift')
    return cert

def replay():
    cert=validate_archive();grant=json.loads(GRANT.read_text())
    if grant.get('status')!='CLOSED' or grant.get('remaining_usd')!=0 or grant.get('maximum_calls')!=0 or Path('.github/workflows/hcl-dre001-once.yml').exists():raise ValueError('closed grant/removed trigger required')
    env=dict(os.environ)
    for key in list(env):
        if key.endswith(('_API_KEY','_AUTHORIZED')) or key in ('PYTHONPATH','GITHUB_RUN_ATTEMPT'):env.pop(key,None)
    with tempfile.TemporaryDirectory(prefix='hcl-dre001-replay-') as tmp:
        root=Path(tmp)
        with zipfile.ZipFile(ARCHIVE) as archive:
            for name in cert['files']:
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(archive.read(name))
        path=root/GRANT;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(GRANT.read_bytes())
        subprocess.run([sys.executable,'-m','scripts.development_reader_live_entry','--preflight','--output','replay.json'],cwd=root,env=env,check=True,stdout=subprocess.DEVNULL)
        # The archived preflight rebuilds exact source/profile/execution/runtime.
        # It returns before importing or creating any provider client.
    return dict(status='PASS_EXACT_DRE001_FROZEN_INPUTS_PROVIDER_FREE',run_sha=RUN_SHA,package_sha256=cert['package_sha256'],runtime_sha256=cert['runtime_sha256'],provider_calls=0,latest_runtime_substituted=False,outputs_rescored=False,longmemeval='SEALED_NOT_ACCESSED')
if __name__=='__main__':print(json.dumps(replay(),sort_keys=True))
