"""Frozen desktop entry point; writable data must always be supplied by the host."""
import multiprocessing
import sys
from pathlib import Path

if __name__ == '__main__':
    multiprocessing.freeze_support()
    for stream in (sys.stdout, sys.stderr):
        if stream is not None:
            stream.reconfigure(encoding='utf-8', errors='replace')
    if '--self-check-vault' in sys.argv:
        from uuid import uuid4
        from backend.settings.store import NativeVault
        vault = NativeVault()
        vault.SERVICE = 'org.openpaper.acceptance'
        account = uuid4().hex
        value = 'synthetic-' + uuid4().hex
        written = False
        try:
            vault.set(account, value)
            written = True
            assert vault.get(account) == value
        finally:
            if written:
                vault.delete(account)
        assert vault.get(account) is None
        print('Native credential vault write/read/delete passed (isolated synthetic entry)')
    elif '--self-check' in sys.argv:
        import io
        import json
        import pymupdf
        from pptx import Presentation
        from PIL import Image
        from backend.settings.store import NativeVault
        with pymupdf.open() as document:
            document.new_page()
            assert document.tobytes().startswith(b'%PDF')
        output = io.BytesIO()
        Presentation().save(output)
        Image.new('RGB', (2, 2)).save(io.BytesIO(), format='PNG')
        vault = NativeVault()._backend()  # Import adapter without accessing credentials.
        print(json.dumps({'ok': True, 'vault': type(vault).__name__}))
    else:
        if '--library-root' not in sys.argv or '--config-root' not in sys.argv:
            raise SystemExit('Frozen backend requires --library-root and --config-root')
        if '--resource-root' not in sys.argv:
            sys.argv.extend(['--resource-root', str(Path(sys._MEIPASS))])
        from backend.server import main
        main()
