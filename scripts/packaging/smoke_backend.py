"""Exercise a relocated frozen helper, without a venv or source working directory."""
import http.client
import json
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading


def main():
    source = Path(sys.argv[1]).resolve()
    with tempfile.TemporaryDirectory(prefix='openpaper-frozen-') as temp:
        root = Path(temp)
        bundle = root / '应用 bundle'
        shutil.copytree(source, bundle, symlinks=True)
        executable = bundle / ('openpaper-backend.exe' if os.name == 'nt' else 'openpaper-backend')
        env = {k: v for k, v in os.environ.items() if k not in ('PYTHONHOME', 'PYTHONPATH', 'VIRTUAL_ENV')}
        env.update(OPENPAPER_DESKTOP_TOKEN='c' * 32, PYTHONUTF8='1')
        subprocess.run([str(executable), '--self-check'], cwd=root, env=env, check=True, timeout=60)
        proc = subprocess.Popen([str(executable), '--desktop', '--port', '0', '--ready-json',
            '--library-root', str(root / '论文 library'), '--config-root', str(root / '配置 config')],
            cwd=root, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding='utf-8')
        events = queue.Queue()
        output = []
        def read():
            for line in proc.stdout:
                output.append(line)
                try:
                    value = json.loads(line)
                    if value.get('event') == 'ready':
                        events.put(value)
                except ValueError:
                    pass
            events.put(None)
        thread = threading.Thread(target=read, daemon=True)
        thread.start()
        connection = None
        try:
            ready = events.get(timeout=60)
            assert ready, ''.join(output)
            connection = http.client.HTTPConnection('127.0.0.1', ready['port'], timeout=10)
            def get(path, cookie=None):
                connection.request('GET', path, headers={'Cookie': cookie} if cookie else {})
                response = connection.getresponse()
                return response.status, response.getheader('Set-Cookie'), response.read()
            assert get('/app/')[0] == 401
            status, cookie, _ = get('/desktop/session?token=' + 'c' * 32)
            assert status == 302 and cookie
            cookie = cookie.split(';', 1)[0]
            assert get('/api/ping', cookie)[0] == 200
            status, _, page = get('/app/', cookie)
            assert status == 200
            assets = re.findall(r'(?:src|href)="(/app/assets/[^\"]+)"', page.decode())
            assert assets, page
            for asset in assets:
                assert get(asset, cookie)[0] == 200, asset
            assert get('/api/library', cookie)[0] == 200
            proc.stdin.close()
            assert proc.wait(timeout=15) == 0, ''.join(output)
            print('Frozen backend: relocated launch, dependencies, session, UI assets, library and shutdown passed')
        finally:
            if connection:
                connection.close()
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=10)
            thread.join(5)
            proc.stdout.close()
            if not proc.stdin.closed:
                proc.stdin.close()

if __name__ == '__main__':
    main()
