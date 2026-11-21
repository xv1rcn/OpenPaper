import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from backend.settings.preferences import PreferencesStore, DEFAULTS
from backend.settings.store import SettingsError, ConflictError


class PreferencesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = PreferencesStore(Path(self.temp.name) / 'config')

    def test_defaults_and_restart(self):
        self.assertEqual(self.store.read()['values'], DEFAULTS)
        self.assertFalse(self.store.path.exists())
        values = dict(DEFAULTS, theme='dark', background='#112233')
        saved = self.store.save(values, '0')
        self.assertEqual(PreferencesStore(self.store.path.parent).read(), saved)
        with self.assertRaises(ConflictError):
            self.store.save(DEFAULTS, '0')
        self.assertEqual(self.store.read(), saved)

    def test_validation_and_future_version_preserve_file(self):
        with self.assertRaises(SettingsError):
            self.store.save(dict(DEFAULTS, accent='url(https://example.com)'), '0')
        self.assertFalse(self.store.path.exists())
        self.store.path.parent.mkdir()
        raw = json.dumps({'schemaVersion': 99, 'revision': 'future', 'values': DEFAULTS})
        self.store.path.write_text(raw)
        with self.assertRaises(SettingsError):
            self.store.save(DEFAULTS, 'future')
        self.assertEqual(self.store.path.read_text(), raw)

    def test_failed_replace_keeps_previous_preferences(self):
        saved = self.store.save(DEFAULTS, '0')
        with patch('backend.settings.preferences.os.replace', side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):
                self.store.save(dict(DEFAULTS, theme='dark'), saved['revision'])
        self.assertEqual(self.store.read(), saved)
        self.assertEqual(list(self.store.path.parent.glob('.preferences-*')), [])
