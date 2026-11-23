import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from backend.settings.view_state import ViewStateStore
from backend.settings.store import SettingsError, SettingsStore
from backend.runtime.paths import RuntimePaths
from backend.server import create_server


class ViewStateTests(unittest.TestCase):
    def test_restart_merge_migration_and_invalid_input(self):
        with tempfile.TemporaryDirectory() as root:
            store = ViewStateStore(root)
            store.save('openpaper-library-layout', 'list')
            store.save('openpaper-grouped', 'true')
            self.assertEqual(store.save('openpaper-library-layout', 'grid', True), 'list')
            self.assertEqual(ViewStateStore(root).read()['openpaper-library-layout'], 'list')
            with self.assertRaises(SettingsError): store.save('../../secret', 'x')
            with self.assertRaises(SettingsError): store.save('openpaper-reader-demo', '{"page":0,"width":50,"showPdf":true}')
            with patch('backend.settings.view_state.os.replace', side_effect=OSError('disk')):
                with self.assertRaises(OSError): store.save('openpaper-grouped', 'false')
            self.assertEqual(store.read()['openpaper-grouped'], 'true')
            raw = '{"schemaVersion":99,"values":{}}'
            store.path.write_text(raw)
            with self.assertRaises(SettingsError): store.save('openpaper-grouped', 'false')
            self.assertEqual(store.path.read_text(), raw)

    def test_new_port_and_new_session_keep_state(self):
        with tempfile.TemporaryDirectory() as root:
            ports=[]
            for index in range(2):
                token = str(index) * 32
                server = create_server(RuntimePaths.resolve(root), 0, SettingsStore(Path(root)/'config'), token)
                thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
                ports.append(server.server_port)
                conn=http.client.HTTPConnection('127.0.0.1',server.server_port)
                try:
                    conn.request('GET','/api/view-state');r=conn.getresponse();self.assertEqual(r.status,401);r.read()
                    conn.request('GET','/desktop/session?token='+token);r=conn.getresponse();cookie=r.getheader('Set-Cookie').split(';')[0];r.read()
                    if index == 0:
                        body=json.dumps({'key':'openpaper-reader-demo.pdf','value':json.dumps({'page':3,'width':60,'showPdf':False})})
                        conn.request('POST','/api/view-state',body,{'Cookie':cookie,'Content-Type':'application/json','X-OpenPaper-Request':'1'})
                        r=conn.getresponse();self.assertEqual(r.status,200);r.read()
                    else:
                        conn.request('GET','/api/view-state',headers={'Cookie':cookie});r=conn.getresponse()
                        self.assertEqual(json.loads(json.loads(r.read())['values']['openpaper-reader-demo.pdf'])['page'],3)
                finally:
                    conn.close();server.shutdown();server.server_close();thread.join()
