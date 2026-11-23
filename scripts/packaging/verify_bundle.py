"""Verify the helper actually shipped in a macOS app, Debian package or NSIS install."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def smoke(directory):
    executable = 'openpaper-backend.exe' if os.name == 'nt' else 'openpaper-backend'
    matches = list(directory.rglob(executable))
    if len(matches) != 1:
        raise RuntimeError(f'Expected one bundled helper in {directory}; found {len(matches)}')
    subprocess.run([sys.executable, str(ROOT / 'scripts/packaging/smoke_backend.py'),
                    str(matches[0].parent)], check=True, timeout=180)


def main():
    kind = sys.argv[1]
    bundle = ROOT / 'desktop/target/release/bundle'
    if kind == 'app':
        smoke(bundle / 'macos/OpenPaper.app')
    elif kind == 'deb':
        packages = list((bundle / 'deb').glob('*.deb'))
        if len(packages) != 1:
            raise RuntimeError('Expected exactly one Debian package')
        with tempfile.TemporaryDirectory(prefix='openpaper-deb-') as temp:
            subprocess.run(['dpkg-deb', '-x', str(packages[0]), temp], check=True)
            smoke(Path(temp))
    elif kind == 'nsis':
        installers = list((bundle / 'nsis').glob('*.exe'))
        if len(installers) != 1:
            raise RuntimeError('Expected exactly one NSIS installer')
        with tempfile.TemporaryDirectory(prefix='openpaper-install-') as temp:
            destination = Path(temp) / 'OpenPaper'
            # NSIS requires /D to be last, unquoted, even when the path contains spaces.
            command = f'"{installers[0]}" /S /D={destination}'
            subprocess.run(command, check=True, timeout=180)
            try:
                if not (destination / 'openpaper-desktop.exe').is_file():
                    raise RuntimeError('Installed desktop executable missing')
                smoke(destination)
            finally:
                uninstaller = destination / 'uninstall.exe'
                if uninstaller.exists():
                    subprocess.run(f'"{uninstaller}" /S _?={destination}', check=True, timeout=120)
    else:
        raise ValueError('Expected app, deb or nsis')


if __name__ == '__main__':
    main()
