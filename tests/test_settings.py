import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from backend.settings.store import SettingsStore, SettingsError, ConflictError, DEFAULTS, NativeVault


class Vault:
    def __init__(self):
        self.values = {}

    def set(self, ref, secret):
        self.values[ref] = secret

    def get(self, ref):
        return self.values.get(ref)

    def delete(self, ref):
        del self.values[ref]


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'config'
        self.vault = Vault()
        self.store = SettingsStore(self.root, self.vault)
        self.provider = {**DEFAULTS, 'apiBaseUrl': 'https://example.com/v1', 'model': 'test'}

    def save(self, key='synthetic-secret'):
        return self.store.save(self.provider, self.store.read()['revision'], key)

    def test_read_is_side_effect_free(self):
        self.assertFalse(self.store.read()['hasCredential'])
        self.assertFalse(self.root.exists())

    def test_restart_and_redaction(self):
        public = self.save()
        reopened = SettingsStore(self.root, self.vault)
        self.assertEqual(reopened.read(), public)
        self.assertEqual(reopened.resolve()['apiKey'], 'synthetic-secret')
        self.assertNotIn('synthetic-secret', self.store.path.read_text())
        self.assertNotIn('credentialRef', public)
        self.assertNotIn('apiKey', json.dumps(public))

    def test_rotation_removes_previous_entry(self):
        self.save()
        self.save('synthetic-new')
        self.assertEqual(list(self.vault.values.values()), ['synthetic-new'])

    def test_nonsecret_update_retains_key(self):
        self.save()
        self.provider['model'] = 'other'
        self.save(None)
        self.assertEqual(self.store.resolve()['apiKey'], 'synthetic-secret')

    def test_stale_revision_has_no_side_effect(self):
        before = self.save()
        with self.assertRaises(ConflictError):
            self.store.save(self.provider, '0', 'new')
        self.assertEqual(self.store.read(), before)
        self.assertEqual(len(self.vault.values), 1)

    def test_write_failure_preserves_old_configuration(self):
        before = self.save()
        with patch.object(self.store, '_write', side_effect=OSError('disk full')):
            with self.assertRaises(SettingsError):
                self.save('synthetic-new')
        self.assertEqual(self.store.read(), before)
        self.assertEqual(list(self.vault.values.values()), ['synthetic-secret'])

    def test_vault_verification_failure_preserves_old_configuration(self):
        before = self.save()
        with patch.object(self.vault, 'get', return_value=None):
            with self.assertRaises(SettingsError):
                self.save('synthetic-new')
        self.assertEqual(self.store.read(), before)
        self.assertEqual(list(self.vault.values.values()), ['synthetic-secret'])

    def test_vault_failure_never_falls_back_to_plaintext(self):
        with patch.object(self.vault, 'set', side_effect=RuntimeError('synthetic-secret')):
            with self.assertRaises(SettingsError) as caught:
                self.save()
        self.assertNotIn('synthetic-secret', str(caught.exception))
        self.assertFalse(self.store.path.exists())

    def test_cleanup_failure_reports_committed_state(self):
        self.save()
        with patch.object(self.vault, 'delete', side_effect=RuntimeError()):
            result = self.save('synthetic-new')
        self.assertIn('warning', result)
        self.assertEqual(self.store.resolve()['apiKey'], 'synthetic-new')

    def test_endpoint_change_requires_new_key(self):
        self.save()
        self.provider['apiBaseUrl'] = 'https://other.example/v1'
        with self.assertRaises(SettingsError):
            self.save(None)

    def test_corrupt_and_future_config_preserved(self):
        self.root.mkdir()
        for content in ('{broken', '{"schemaVersion": 999}'):
            self.store.path.write_text(content)
            with self.assertRaises(SettingsError):
                self.save()
            self.assertEqual(self.store.path.read_text(), content)

    def test_reject_invalid_provider_values(self):
        for field, value in [('apiKey', 'secret'), ('timeoutSec', True), ('contextWindow', -1),
                             ('apiBaseUrl', 'https://user:pass@example.com'),
                             ('apiBaseUrl', 'https://example.com?key=secret')]:
            with self.subTest(field=field, value=value):
                with self.assertRaises(SettingsError):
                    self.store.save({**self.provider, field: value}, '0')

    def test_missing_vault_entry_is_not_empty_key(self):
        self.save()
        self.vault.values.clear()
        with self.assertRaises(SettingsError):
            self.store.resolve()

    def test_native_adapter_redacts_errors(self):
        vault = NativeVault()
        with patch.object(vault, '_backend', side_effect=RuntimeError('synthetic-secret')):
            for operation in (lambda: vault.get('x'), lambda: vault.set('x', 'y'), lambda: vault.delete('x')):
                with self.assertRaises(SettingsError) as caught:
                    operation()
                self.assertNotIn('synthetic-secret', str(caught.exception))


class SettingsHTTPTests(unittest.TestCase):
    def setUp(self):
        import threading
        from backend.server import create_server
        from backend.runtime.paths import RuntimePaths
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = SettingsStore(self.temp.name, Vault())
        self.server = create_server(RuntimePaths.resolve(self.temp.name), 0, self.store)
        worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        worker.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(worker.join, 5)
        self.addCleanup(self.server.shutdown)
        self.host = '127.0.0.1:' + str(self.server.server_port)

    def request(self, method='GET', body=None, **headers):
        from http.client import HTTPConnection
        connection = HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        try:
            connection.request(method, '/api/settings', body=body, headers=headers)
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def test_save_read_conflict_and_no_secret_response(self):
        self.assertEqual(self.request()[0], 200)
        body = json.dumps({'provider': DEFAULTS, 'revision': '0', 'apiKey': 'synthetic-secret'})
        headers = {'Content-Type': 'application/json', 'X-OpenPaper-Request': '1', 'Origin': 'http://' + self.host}
        status, result = self.request('POST', body, **headers)
        self.assertEqual(status, 200)
        self.assertTrue(result['hasCredential'])
        self.assertNotIn('synthetic-secret', json.dumps(result))
        self.assertEqual(self.request('POST', body, **headers)[0], 409)
        self.assertNotIn('apiKey', json.dumps(self.request()[1]))

    def test_host_origin_content_type_and_size_boundaries(self):
        for headers in ({'Host': 'evil.example'}, {'Origin': 'https://evil.example'}, {'Origin': 'null'}):
            self.assertEqual(self.request(**headers)[0], 403)
        self.assertEqual(self.request('POST', '{}')[0], 403)
        headers = {'Content-Type': 'application/json', 'X-OpenPaper-Request': '1'}
        for body in ('[]', '{bad', 'x' * 65537):
            self.assertEqual(self.request('POST', body, **headers)[0], 400)
        self.assertFalse(self.store.path.exists())
