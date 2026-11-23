"""Non-secret view state; keys never become filesystem paths."""
from collections import OrderedDict
import json
import os
from pathlib import Path
import tempfile
from threading import RLock
from .store import SettingsError


def validate(key, value):
    if not isinstance(key, str) or len(key) > 2048 or not isinstance(value, str) or len(value) > 16384:
        raise SettingsError('阅读状态格式无效')
    if key == 'openpaper-grouped':
        valid = value in ('true', 'false')
    elif key == 'openpaper-library-layout':
        valid = value in ('grid', 'list')
    elif key == 'openpaper-group-order':
        items = json.loads(value)
        valid = isinstance(items, list) and len(items) <= 1000 and all(isinstance(x, str) and len(x) <= 256 for x in items)
    elif key.startswith('openpaper-reader-') and key.endswith('-zoom'):
        valid = value in ('page-width', 'page-fit', '0.5', '0.75', '1', '1.25', '1.5', '2')
    elif key.startswith('openpaper-reader-'):
        item = json.loads(value)
        valid = (isinstance(item, dict) and set(item) == {'page', 'width', 'showPdf'}
                 and type(item['page']) is int and 1 <= item['page'] <= 100000
                 and type(item['width']) in (int, float) and 25 <= item['width'] <= 70
                 and type(item['showPdf']) is bool)
    else:
        valid = False
    if not valid:
        raise SettingsError('阅读状态格式无效')


class ViewStateStore:
    def __init__(self, root):
        self.path = Path(root) / 'view-state.json'
        self.lock = RLock()
        self.clients = OrderedDict()

    def read(self):
        with self.lock:
            if not self.path.exists():
                return {}
            try:
                data = json.loads(self.path.read_text(encoding='utf-8'))
                if data['schemaVersion'] != 1 or not isinstance(data['values'], dict):
                    raise ValueError()
                for key, value in data['values'].items():
                    validate(key, value)
                return data['values']
            except Exception:
                raise SettingsError('阅读状态文件损坏或版本不受支持，原文件已保留') from None

    def save(self, key, value, only_missing=False, client=None, sequence=None):
        validate(key, value)
        if client is not None and (not isinstance(client, str) or not 1 <= len(client) <= 64
                                   or type(sequence) is not int or not 0 < sequence <= 9007199254740991):
            raise SettingsError('阅读状态更新序号无效')
        with self.lock:
            values = self.read()
            if client is not None:
                previous = self.clients.get(client, {}).get(key, 0)
                if sequence <= previous:
                    return values.get(key, value)
            if only_missing and key in values:
                return values[key]
            if key not in values and len(values) >= 20000:
                raise SettingsError('阅读状态数量已达上限')
            values[key] = value
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, name = tempfile.mkstemp(prefix='.view-state-', dir=self.path.parent)
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                    json.dump({'schemaVersion': 1, 'values': values}, stream)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(name, self.path)
            finally:
                if os.path.exists(name):
                    os.unlink(name)
            if client is not None:
                self.clients.setdefault(client, {})[key] = sequence
                self.clients.move_to_end(client)
                if len(self.clients) > 128:
                    self.clients.popitem(last=False)
            return value
