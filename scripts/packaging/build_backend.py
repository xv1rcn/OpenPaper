"""Run on each target OS/architecture after building frontend/dist."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]

def main():
    if not (ROOT / 'frontend/dist/index.html').is_file():
        raise SystemExit('Build frontend/dist first: cd frontend && npm ci && npm run build')
    adapter = {'darwin': 'macOS', 'win32': 'Windows'}.get(sys.platform, 'SecretService')
    subprocess.run([
        sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir',
        '--name', 'openpaper-backend', '--paths', str(ROOT),
        '--distpath', str(ROOT / 'desktop/packaged'),
        '--workpath', str(ROOT / 'desktop/target/pyinstaller'),
        '--specpath', str(ROOT / 'desktop/target'),
        '--add-data', f'{ROOT / "frontend/dist"}:frontend/dist',
        '--hidden-import', f'keyring.backends.{adapter}',
        str(ROOT / 'scripts/packaging/backend_entry.py'),
    ], cwd=ROOT, check=True)

if __name__ == '__main__':
    main()
