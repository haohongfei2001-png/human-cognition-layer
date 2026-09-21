"""Apply a reviewed patch only to the pinned upstream file; never guess at drift."""
from pathlib import Path
import hashlib
import subprocess
import sys

ORIGINAL = '2b8895ce9b3d49dcc2a89c12bf283863139153f897da5bf2013d892dcca3ae0b'
PATCHED = 'd9692373e6522b02884671d80bec1ce3ba99ba62888e8e9c137b20761737a583'
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
