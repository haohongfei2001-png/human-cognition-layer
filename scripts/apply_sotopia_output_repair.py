"""Apply a reviewed patch only to the pinned upstream file; never guess at drift."""
from pathlib import Path
import hashlib
import subprocess
import sys

ORIGINAL = '46829dad9a17cc267be068a7cd28daeee7607b8eac14b4a35b40d2fe5234eaea'
PATCHED = 'f9b73e5f19ff6f2329673f08407e1f27cc5b1d06673a9c2fc252a8be207ad18f'
ROOT = Path(__file__).resolve().parents[1]

def apply(root: Path) -> None:
    source = root / 'sotopia/generation_utils/generate.py'
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest == PATCHED:
        return
    if digest != ORIGINAL:
        raise RuntimeError('Unrecognized SOTOPIA source; refusing output repair patch')
    subprocess.run(['git', 'apply', '--check', str(ROOT / 'patches/sotopia-same-provider-output-repair.patch')], cwd=root, check=True)
    subprocess.run(['git', 'apply', str(ROOT / 'patches/sotopia-same-provider-output-repair.patch')], cwd=root, check=True)
    if hashlib.sha256(source.read_bytes()).hexdigest() != PATCHED:
        raise RuntimeError('Patched SOTOPIA source digest mismatch')
    print('Pinned SOTOPIA same-provider output repair applied')

if __name__ == '__main__':
    apply(Path(sys.argv[1]).resolve())
