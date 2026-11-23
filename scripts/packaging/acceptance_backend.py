"""Packaged integration acceptance in disposable data, with no model calls or real keys."""
from contextlib import contextmanager
import hashlib
import http.client
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
from urllib.parse import quote
from uuid import uuid4
import pymupdf


@contextmanager
def running(bundle, root):
    exe = bundle / ('openpaper-backend.exe' if os.name == 'nt' else 'openpaper-backend')
    token = uuid4().hex
    env = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV')}
    env.update(OPENPAPER_DESKTOP_TOKEN=token, PYTHONUTF8='1')
    proc = subprocess.Popen([str(exe), '--desktop', '--port', '0', '--ready-json',
        '--library-root', str(root/'library'), '--config-root', str(root/'config')],
        cwd=root, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding='utf-8')
    events=queue.Queue(); output=[]
    def read():
        for line in proc.stdout:
            output.append(line)
            try:
                data=json.loads(line)
                if data.get('event') == 'ready': events.put(data)
            except ValueError: pass
        events.put(None)
    thread=threading.Thread(target=read, daemon=True);thread.start()
    conn=None
    try:
        ready=events.get(timeout=60)
        assert ready, ''.join(output)
        conn=http.client.HTTPConnection('127.0.0.1',ready['port'],timeout=15)
        conn.request('GET','/desktop/session?token='+token)
        response=conn.getresponse();assert response.status==302
        cookie=response.getheader('Set-Cookie').split(';',1)[0];response.read()
        def call(path, body=None, raw=False, headers=None):
            request_headers={'Cookie':cookie,'X-OpenPaper-Request':'1'}
            if body is not None:
                request_headers['Content-Type']='application/pdf' if raw else 'application/json'
                if not raw: body=json.dumps(body)
            request_headers.update(headers or {})
            conn.request('GET' if body is None else 'POST',path,body,request_headers)
            response=conn.getresponse();content=response.read()
            assert response.status==200, (path,response.status,content[:500])
            return content if raw else json.loads(content)
        yield call
        proc.stdin.close()
        assert proc.wait(timeout=15)==0, ''.join(output)
    finally:
        if conn:conn.close()
        if proc.poll() is None:proc.kill();proc.wait(timeout=10)
        thread.join(5);proc.stdout.close()
        if not proc.stdin.closed:proc.stdin.close()


def main():
    source=Path(sys.argv[1]).resolve()
    with tempfile.TemporaryDirectory(prefix='openpaper-acceptance-') as temp:
        root=Path(temp);bundle=root/'应用 A'
        shutil.copytree(source,bundle,symlinks=True)
        with pymupdf.open() as doc:
            for i in range(3):
                page=doc.new_page();page.insert_text((72,72),f'Acceptance evidence page {i+1}')
            pdf=doc.tobytes()
        expected_hash=hashlib.sha256(pdf).hexdigest()
        with running(bundle,root) as call:
            imported=call('/api/import-pdf',pdf,True,{'X-File-Name':quote('验收 test.pdf')})
            imported=json.loads(imported)
            key=imported['file_key']
            assert json.loads(call('/api/import-pdf',pdf,True,{'X-File-Name':quote('验收 test.pdf')}))['duplicate']
            call('/api/update-paper',{'file_key':key,'fields':{'title':'Acceptance paper','notes':'Keep notes after replacement','tags':['验收'],'read':True}})
            prefs=call('/api/preferences');appearance={**prefs['values'],'theme':'dark'}
            call('/api/preferences',{'values':appearance,'revision':prefs['revision']})
            settings=call('/api/settings');provider={**settings['provider'],'apiBaseUrl':'https://example.invalid/v1','model':'acceptance-model'}
            call('/api/settings',{'provider':provider,'revision':settings['revision']})
            state=json.dumps({'page':3,'width':60,'showPdf':True})
            call('/api/view-state',{'key':'openpaper-reader-'+key,'value':state})
            call('/api/view-state',{'key':'openpaper-reader-'+key+'-zoom','value':'1.25'})
        # Same-version replacement, not a claim of cross-version schema migration.
        shutil.rmtree(bundle)
        bundle=root/'应用 B';shutil.copytree(source,bundle,symlinks=True)
        with running(bundle,root) as call:
            papers=call('/api/library')['papers'];assert len(papers)==1
            paper=papers[0]
            assert paper['file_key']==key and paper['notes']=='Keep notes after replacement'
            assert paper['read'] is True and paper['tags']==['验收']
            assert hashlib.sha256(call('/'+paper['pdf'],raw=True)).hexdigest()==expected_hash
            assert call('/api/preferences')['values']==appearance
            settings=call('/api/settings');assert settings['provider']==provider and not settings['hasCredential']
            states=call('/api/view-state')['values']
            assert json.loads(states['openpaper-reader-'+key])['page']==3
            assert states['openpaper-reader-'+key+'-zoom']=='1.25'
        print('Packaged acceptance passed: PDF import/dedup/readback, metadata, preferences, provider configuration, reader state, restart and same-version replacement')


if __name__=='__main__':main()
