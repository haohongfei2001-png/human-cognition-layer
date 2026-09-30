"""Replay consumed Gaskell code/runtime against current negative history, zero transport."""
import hashlib,io,json,os,subprocess,sys,tarfile,tempfile,zipfile
from pathlib import Path
BASE='c8bf7fecf859fd456f39b21482a809028824d037'
PACKAGE='reports/HCL_I02_GASKELL_HOLDER_PACKAGE.json'
PUBLISHER_CACHE=Path('reports/HCL_I02_GASKELL_PINNED_PUBLISHER.zip')
PUBLISHER_CACHE_SHA256='34be2aacfb9167d63fda175fbedc9b68fb319bbaf147beefbd1819061fdd6a4d'

def pinned_publisher_material():
    raw=PUBLISHER_CACHE.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PUBLISHER_CACHE_SHA256:raise ValueError('pinned historical publisher archive drift')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        if len(z.namelist())!=2 or set(z.namelist())!={'raw.txt','publisher.rdf'}:raise ValueError('publisher cache members drift')
        body,rdf=z.read('raw.txt'),z.read('publisher.rdf')
    # These are the original raw-data identities in the canonical one-run preflight.
    expected=json.loads(Path('reports/HCL_I02_GASKELL_HOLDER_EXECUTION_PREFLIGHT.json').read_text())['source_gate']
    if (hashlib.sha256(body).hexdigest()!=expected['raw_sha256'] or
        hashlib.sha256(rdf).hexdigest()!=expected['publisher_metadata_sha256']):raise ValueError('historical publisher byte identities drift')
    return body,rdf

def replay(repository='.'):
    repository=Path(repository).resolve()
    def git(*args):return subprocess.check_output(['git','-C',str(repository),*args],timeout=30)
    raw=git('show',BASE+':'+PACKAGE);package=json.loads(raw)
    if Path(PACKAGE).read_bytes()!=raw:raise ValueError('consumed Gaskell package changed')
    files=set(package['execution_files'])|{PACKAGE,
        'tests/test_i02_obp_metaethics.py','tests/test_i02_native_choice_candidate.py',
        'reports/HCL_I02_NATIVE_CHOICE_DEVELOPMENT_ENTRY.json',
        'reports/HCL_I02_OBP_METAETHICS_RECONSTRUCTION.json',
        'reports/HCL_I01_EVALUATION_FREEZE.json','reports/HCL_I02_RUNTIME_AMENDMENT.json'}
    files.update(f'reports/HCL_I02_RUNTIME_AMENDMENT_V{i}.json' for i in range(2,7))
    obp_path='reports/HCL_I02_OBP_METAETHICS_CPG_PACKAGE.json'
    obp=json.loads(git('show',BASE+':'+obp_path));files.update(obp['execution_files']);files.add(obp_path)
    files.update(p for p in git('ls-tree','-r','--name-only',BASE,'scripts').decode().splitlines() if p.endswith('.py') and 'longmemeval' not in p.lower())
    if any('longmemeval' in p.lower() for p in files):raise ValueError('sealed paths forbidden')
    archive=git('archive',BASE,'hcl',*sorted(files))
    env=dict(os.environ,GIT_DIR=str(repository/'.git'))
    for key in ('DEEPSEEK_API_KEY','OPENAI_API_KEY','HCL_I02_GASKELL_HOLDER_AUTHORIZED'):env.pop(key,None)
    with tempfile.TemporaryDirectory() as folder:
        with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
            if any(m.issym() or m.islnk() or m.name.startswith('/') or '..' in Path(m.name).parts for m in bundle.getmembers()):raise ValueError('unsafe replay archive')
            bundle.extractall(folder,filter='data')
        for name,expected in package['execution_files'].items():
            if hashlib.sha256(Path(folder,name).read_bytes()).hexdigest()!=expected:raise ValueError('certified Gaskell execution mismatch')
        subprocess.run([sys.executable,'-m','unittest','tests.test_i02_gaskell_holder_once','tests.test_i02_obp_metaethics','tests.test_i02_native_choice_candidate'],cwd=folder,env=env,check=True,timeout=60)
        body,rdf=pinned_publisher_material()
        Path(folder,'pinned-publisher.txt').write_bytes(body);Path(folder,'pinned-publisher.rdf').write_bytes(rdf)
        # Supply identical already-pinned external bytes to frozen code; no network,
        # source rewrite, model call, code mutation or latest-runtime substitution.
        program="""import runpy,sys
from pathlib import Path
from scripts import i02_gaskell_development_candidate as holder
def cached(url):
    if url==holder.RAW_URL:return Path('pinned-publisher.txt').read_bytes()
    if url==holder.RDF_URL:return Path('pinned-publisher.rdf').read_bytes()
    raise ValueError('no other historical publisher lookup allowed')
holder.download=cached
sys.argv=['certified-gaskell','--preflight','--metadata','preflight.json']
runpy.run_module('scripts.run_i02_gaskell_holder_once',run_name='__main__')
"""
        subprocess.run([sys.executable,'-c',program],cwd=folder,env=env,check=True,timeout=180)
        subprocess.run([sys.executable,'-m','scripts.i02_obp_metaethics_preflight'],cwd=folder,env=env,check=True,timeout=30)
        gate=json.loads(Path(folder,'preflight.json').read_text());probe=gate['source_gate']['h_ordinary_entry_probe']
        if probe['runtime_sha256']!=package['h_runtime_sha256'] or probe['status']!='REFUSED_COMPLETE_LONG_SOURCE':raise ValueError('historical H source boundary replaced')
    return dict(schema='hcl-i02-gaskell-certified-replay-v1',baseline_sha=BASE,current_negative_history_head=git('rev-parse','HEAD').decode().strip(),historical_runtime_sha256=package['h_runtime_sha256'],status='PASS_CERTIFIED_V6_NOT_CURRENT_RUNTIME',provider_calls=0,provider_spend_usd=0,longmemeval='SEALED_NOT_ACCESSED')
if __name__=='__main__':print(json.dumps(replay(),indent=2))
