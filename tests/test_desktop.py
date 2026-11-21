"""Desktop session and parent lifetime tests; no native UI or real credentials."""
import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from backend.server import create_server
from backend.runtime.paths import RuntimePaths
from backend.settings.store import SettingsStore

class DesktopTests(unittest.TestCase):
    def test_session_guards_static_api_and_head(self):
        with tempfile.TemporaryDirectory() as temp:
            paths=RuntimePaths.resolve(temp)
            server=create_server(paths,0,SettingsStore(Path(temp)/'config'), 'a'*32)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            self.addCleanup(lambda: (server.shutdown(),server.server_close(),thread.join()))
            port=server.server_port
            conn=http.client.HTTPConnection('127.0.0.1',port)
            self.addCleanup(conn.close)
            for method,path in [('GET','/api/ping'),('GET','/app/'),('HEAD','/app/'),('POST','/api/update-paper')]:
                conn.request(method,path);response=conn.getresponse();self.assertEqual(response.status,401);response.read()
            conn.request('GET','/desktop/session?token=wrong');response=conn.getresponse();self.assertEqual(response.status,403);response.read()
            conn.request('GET','/desktop/session?token='+'a'*32);response=conn.getresponse();self.assertEqual(response.status,302)
            cookie=response.getheader('Set-Cookie');self.assertIn('HttpOnly',cookie);self.assertIn('SameSite=Strict',cookie);response.read()
            conn.request('GET','/api/ping',headers={'Cookie':cookie});response=conn.getresponse();self.assertEqual(response.status,200);response.read()
            conn.request('GET','/api/ping',headers={'Cookie':cookie,'Origin':'https://untrusted.example'});response=conn.getresponse();self.assertEqual(response.status,403);response.read()

    def test_parent_pipe_closure_stops_backend(self):
        with tempfile.TemporaryDirectory() as temp:
            proc=subprocess.Popen([sys.executable,'-m','backend','--desktop','--port','0','--ready-json','--library-root',temp,'--config-root',str(Path(temp)/'config')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=dict(os.environ,OPENPAPER_DESKTOP_TOKEN='b'*32),text=True)
            try:
                ready=threading.Event();events=[]
                def read():
                    for line in proc.stdout:
                        try:
                            value=json.loads(line)
                            if value.get('event')=='ready':events.append(value);ready.set()
                        except ValueError:pass
                thread=threading.Thread(target=read,daemon=True);thread.start()
                self.assertTrue(ready.wait(60),'backend did not become ready')
                self.assertGreater(events[0]['port'],0)
                proc.stdin.close()
                self.assertEqual(proc.wait(timeout=10),0)
                thread.join(5)
            finally:
                if proc.poll() is None:proc.kill();proc.wait()
                proc.stdout.close();proc.stderr.close()
