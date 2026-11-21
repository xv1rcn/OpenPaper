"""Versioned configuration with verified native-vault credential rotation.

One SettingsStore owns writes within a backend process. Multiple processes must
use separate config roots until the desktop single-instance guard is available.
"""
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
from urllib.parse import urlsplit
from uuid import uuid4


class SettingsError(Exception):
    pass


class ConflictError(SettingsError):
    pass


class NativeVault:
    SERVICE = "org.openpaper.desktop"

    def _backend(self):
        try:
            if sys.platform == "darwin":
                from keyring.backends.macOS import Keyring
            elif sys.platform == "win32":
                from keyring.backends.Windows import WinVaultKeyring as Keyring
            else:
                from keyring.backends.SecretService import Keyring
            return Keyring()
        except Exception:
            raise SettingsError("系统凭据库不可用；不会改用明文存储") from None

    def get(self, account):
        try:
            return self._backend().get_password(self.SERVICE, account)
        except Exception:
            raise SettingsError("无法读取系统凭据库") from None

    def set(self, account, secret):
        try:
            self._backend().set_password(self.SERVICE, account, secret)
        except Exception:
            raise SettingsError("无法写入系统凭据库") from None

    def delete(self, account):
        try:
            self._backend().delete_password(self.SERVICE, account)
        except Exception:
            raise SettingsError("无法清理系统凭据库条目") from None


def default_config_root():
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/OpenPaper"
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming")) / "OpenPaper"
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "openpaper"


DEFAULTS = {"apiBaseUrl": "", "model": "", "timeoutSec": 120,
            "contextWindow": 128000, "maxOutputTokens": 8192}


def validate(values):
    if not isinstance(values, dict) or set(values) - set(DEFAULTS):
        raise SettingsError("配置包含未知字段")
    result = {**DEFAULTS, **values}
    for field in ("apiBaseUrl", "model"):
        if not isinstance(result[field], str) or len(result[field]) > 2048:
            raise SettingsError("配置文本无效")
        result[field] = result[field].strip()
    url = result["apiBaseUrl"]
    if url:
        try:
            parsed = urlsplit(url)
            valid = (parsed.scheme in ("http", "https") and parsed.hostname
                     and not parsed.username and not parsed.password
                     and not parsed.query and not parsed.fragment)
            parsed.port
        except ValueError:
            valid = False
        if not valid:
            raise SettingsError("API 地址必须是无凭据、查询参数或片段的 HTTP(S) 地址")
        result["apiBaseUrl"] = url.rstrip("/")
    for field, ceiling in (("timeoutSec", 3600), ("contextWindow", 10000000), ("maxOutputTokens", 1000000)):
        value = result[field]
        if type(value) is not int or not 1 <= value <= ceiling:
            raise SettingsError("数值配置超出范围: " + field)
    return result


class SettingsStore:
    def __init__(self, root=None, vault=None):
        self.path = Path(root if root is not None else default_config_root()) / "settings.json"
        self.vault = vault if vault is not None else NativeVault()
        self.lock = threading.RLock()

    def _read(self):
        if not self.path.exists():
            return {"schemaVersion": 1, "revision": "0", "provider": dict(DEFAULTS), "credentialRef": None}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if data["schemaVersion"] != 1 or not isinstance(data["revision"], str):
                raise ValueError()
            validate(data["provider"])
            ref = data["credentialRef"]
            if ref is not None and (not isinstance(ref, str) or len(ref) != 32):
                raise ValueError()
            return data
        except Exception:
            raise SettingsError("配置文件损坏或版本不受支持；原文件已保留") from None

    @staticmethod
    def _public(data):
        return {"schemaVersion": 1, "revision": data["revision"],
                "provider": data["provider"], "hasCredential": bool(data["credentialRef"])}

    def read(self):
        with self.lock:
            return self._public(self._read())

    def _write(self, data):
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix=".settings-", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(data, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.path)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def save(self, provider, revision, api_key=None):
        provider = validate(provider)
        if api_key is not None and (not isinstance(api_key, str) or not api_key.strip() or len(api_key) > 16384):
            raise SettingsError("密钥不能为空")
        with self.lock:
            old = self._read()
            if revision != old["revision"]:
                raise ConflictError("配置已被修改，请重新加载")
            if old["credentialRef"] and old["provider"]["apiBaseUrl"] != provider["apiBaseUrl"] and api_key is None:
                raise SettingsError("更换 API 地址时必须重新提供密钥")
            ref = old["credentialRef"]
            fresh = uuid4().hex if api_key is not None else None
            try:
                if fresh:
                    self.vault.set(fresh, api_key)
                    if self.vault.get(fresh) != api_key:
                        raise SettingsError("凭据读回校验失败")
                    ref = fresh
                data = {"schemaVersion": 1, "revision": uuid4().hex,
                        "provider": provider, "credentialRef": ref}
                self._write(data)
            except Exception:
                if fresh:
                    try:
                        self.vault.delete(fresh)
                    except Exception:
                        pass
                raise SettingsError("配置保存失败；旧配置仍然有效") from None
            result = self._public(data)
            if fresh and old["credentialRef"]:
                try:
                    self.vault.delete(old["credentialRef"])
                except Exception:
                    result["warning"] = "新配置已保存，但旧凭据未能清理"
            return result

    def resolve(self):
        """Backend-only: never serialize this result into an HTTP response."""
        with self.lock:
            data = self._read()
            if not data["credentialRef"]:
                raise SettingsError("尚未保存 API 密钥")
            secret = self.vault.get(data["credentialRef"])
            if not secret:
                raise SettingsError("系统凭据已丢失，请重新保存密钥")
            return {**data["provider"], "apiKey": secret}
