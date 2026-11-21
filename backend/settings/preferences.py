"""Non-secret application preferences, shared by the Vue library and reader."""
import json
import os
from pathlib import Path
import re
import tempfile
from threading import RLock
from uuid import uuid4
from .store import SettingsError, ConflictError

DEFAULTS = {'theme': 'light', 'accent': '#43684e', 'background': '#fafbf8', 'readBackground': '#eef3e8'}


class PreferencesStore:
    def __init__(self, root):
        self.path = Path(root) / 'preferences.json'
        self.lock = RLock()

    def read(self):
        with self.lock:
            if not self.path.exists():
                return {'schemaVersion': 1, 'revision': '0', 'values': dict(DEFAULTS)}
            try:
                value = json.loads(self.path.read_text(encoding='utf-8'))
                if value['schemaVersion'] != 1 or not isinstance(value['revision'], str):
                    raise ValueError()
                self.validate(value['values'])
                return value
            except Exception:
                raise SettingsError('外观配置损坏或版本不受支持，原文件已保留') from None

    @staticmethod
    def validate(values):
        if not isinstance(values, dict) or set(values) != set(DEFAULTS) or values['theme'] not in ('light', 'dark'):
            raise SettingsError('外观配置格式无效')
        if any(not isinstance(values[key], str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', values[key]) for key in ('accent', 'background', 'readBackground')):
            raise SettingsError('请选择有效的颜色')

    def save(self, values, revision):
        self.validate(values)
        with self.lock:
            if self.read()['revision'] != revision:
                raise ConflictError('外观配置已在其他页面修改，请重新加载')
            data = {'schemaVersion': 1, 'revision': uuid4().hex, 'values': values}
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, name = tempfile.mkstemp(prefix='.preferences-', dir=self.path.parent)
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                    json.dump(data, stream)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(name, self.path)
            finally:
                if os.path.exists(name): os.unlink(name)
            return data
