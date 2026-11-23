"""Collect only distributable artifacts, preserving macOS links and executable bits."""
import hashlib
from pathlib import Path
import platform
import shutil
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]
kind = sys.argv[1]
source = ROOT / 'desktop/target/release/bundle'
output = ROOT / 'desktop/artifacts'
output.mkdir(parents=True, exist_ok=True)
if kind == 'app':
    target = output / f'OpenPaper-macos-{platform.machine()}.tar.gz'
    with tarfile.open(target, 'w:gz') as archive:
        archive.add(source / 'macos/OpenPaper.app', arcname='OpenPaper.app')
    artifacts = [target]
else:
    extension = '*.deb' if kind == 'deb' else '*.exe'
    artifacts = []
    for package in (source / kind).glob(extension):
        target = output / package.name
        shutil.copy2(package, target)
        artifacts.append(target)
if not artifacts:
    raise SystemExit('No distributable artifacts found')
lines = []
for artifact in artifacts:
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    lines.append(f'{digest}  {artifact.name}\n')
(output / 'SHA256SUMS.txt').write_text(''.join(lines), encoding='utf-8')
