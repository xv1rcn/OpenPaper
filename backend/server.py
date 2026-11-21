from __future__ import annotations

import os
import argparse
import signal
import time
from pathlib import Path
import sys
import subprocess
import threading
import json
import re
from urllib.parse import urlparse, parse_qs, unquote, quote
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from watchdog.observers import Observer

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.utils import configure_stdio, log, safe_rel
from backend.metadata import (
    delete_paper, delete_speedread, delete_tag, list_recycle_bin, restore_recycle_item, purge_paper, purge_all_papers,
    save_metadata, update_paper, load_metadata,
)
from backend.quick_reading import (
    generate_speedread, test_speedread_config, get_speedread_cache,
    list_speedread_cache,
    export_speedread,
)
from backend.quick_reading.model_catalog import list_models
from backend.watcher import PDFHandler
from backend.runtime.paths import RuntimePaths
from backend.runtime.files import public_file
from backend.runtime.bootstrap import bootstrap
from backend.library.scanner import scan_library
from backend.library.locking import library_lock
from backend.library.importer import import_pdf, PDFImportError, MAX_PDF_BYTES
from backend.settings.store import SettingsStore, SettingsError, ConflictError
from backend.settings.preferences import PreferencesStore

HTTP_PORT = 8000
SPEEDREAD_MAX_IMAGE_PAGES = 5
SPEEDREAD_IMAGE_WIDTH = 3200
SPEEDREAD_MAX_SOURCE_CHARS = 24000


def _resolve_log_file(paths):
    if os.path.exists(paths.log_file):
        return paths.log_file
    if os.path.exists(paths.legacy_log_file):
        return paths.legacy_log_file
    return paths.log_file


def _bring_explorer_to_front(target_path: str) -> None:
    """Best-effort attempt to focus the Explorer window for target_path."""
    if not sys.platform.startswith("win"):
        return
    try:
        import ctypes
        from ctypes import wintypes
    except Exception:
        return

    user32 = ctypes.windll.user32
    target_dir = os.path.basename(os.path.dirname(target_path)) or os.path.basename(target_path)
    if not target_dir:
        return

    EnumWindows = user32.EnumWindows
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    GetWindowText = user32.GetWindowTextW
    GetWindowTextLength = user32.GetWindowTextLengthW
    IsWindowVisible = user32.IsWindowVisible
    GetClassName = user32.GetClassNameW

    found = []

    def callback(hwnd, _lparam):
        if not IsWindowVisible(hwnd):
            return True
        cls = ctypes.create_unicode_buffer(256)
        GetClassName(hwnd, cls, 256)
        if cls.value not in ("CabinetWClass", "ExploreWClass"):
            return True
        length = GetWindowTextLength(hwnd)
        if length <= 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        GetWindowText(hwnd, buf, length + 1)
        if target_dir.lower() in buf.value.lower():
            found.append(hwnd)
            return False
        return True

    # Give Explorer a brief moment to create the target window.
    for _ in range(20):
        time.sleep(0.1)
        found.clear()
        EnumWindows(EnumWindowsProc(callback), 0)
        if found:
            hwnd = found[0]
            try:
                user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                user32.SetForegroundWindow(hwnd)
                user32.BringWindowToTop(hwnd)
            except Exception:
                pass
            return


class PaperRequestHandler(SimpleHTTPRequestHandler):
    """Static file handler with extra local management APIs."""

    @property
    def runtime(self):
        return self.server.runtime

    def translate_path(self, path):
        # send_head checks authorization before this method is called.
        return public_file(self.runtime, path) or str(Path(self.runtime.resource_root) / ".denied")

    def send_head(self):
        target = public_file(self.runtime, self.path)
        if target is None or not os.path.isfile(target):
            self.send_error(404, "Not found")
            return None
        return super().send_head()

    def list_directory(self, path):
        self.send_error(403, "Directory listing is disabled")
        return None

    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_binary(self, status, body, content_type, filename):
        fallback = re.sub(r"[^A-Za-z0-9_.-]+", "_", filename or "openpaper_speedread_export")
        fallback = fallback.strip("._") or "openpaper_speedread_export"
        self.send_response(status)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Disposition", f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quote(filename or fallback)}")
        self.end_headers()
        self.wfile.write(body)

    def _settings_access(self, write=False, content_type="application/json"):
        expected = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
        host = self.headers.get("Host", "")
        origin = self.headers.get("Origin")
        if host not in expected or (origin is not None and origin != "http://" + host):
            self._send_json(403, {"ok": False, "error": "不允许的请求来源"})
            return False
        if write and (self.headers.get_content_type() != content_type
                      or self.headers.get("X-OpenPaper-Request") != "1"):
            self._send_json(403, {"ok": False, "error": "写入需要合法的本地请求"})
            return False
        return True

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html", "/quick-reading.html", "/stats.html"):
            target = "/app/"
            if parsed.path == "/quick-reading.html":
                key = (parse_qs(parsed.query).get("file_key") or [""])[0]
                if key: target += "?file_key=" + quote(key, safe="")
            elif parsed.path == "/stats.html":
                target += "?view=stats"
            if not (Path(self.runtime.resource_root) / "frontend/dist/index.html").is_file():
                self._send_json(503, {"ok": False, "error": "前端尚未构建，请在 frontend 中运行 npm ci && npm run build"})
                return
            self.send_response(302)
            self.send_header("Location", target)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if parsed.path == "/api/preferences":
            if not self._settings_access(): return
            try:
                self._send_json(200, {"ok": True, **self.server.preferences.read()})
            except SettingsError as exc:
                self._send_json(400, {"ok": False, "error": str(exc)})
            return
        if parsed.path == "/api/settings":
            if not self._settings_access():
                return
            try:
                self._send_json(200, {"ok": True, **self.server.settings.read()})
            except SettingsError as exc:
                self._send_json(400, {"ok": False, "error": str(exc)})
            return
        if parsed.path == "/api/open-folder":
            self.handle_open_folder(parse_qs(parsed.query))
            return
        if parsed.path == "/api/log":
            self.handle_getlog(parse_qs(parsed.query))
            return
        if parsed.path == "/api/recycle-list":
            self.handle_recycle_list()
            return
        if parsed.path == "/api/speedread-cache":
            self.handle_speedread_cache(parse_qs(parsed.query))
            return
        if parsed.path == "/api/quick-reading":
            self.handle_speedread_cache(parse_qs(parsed.query))
            return
        if parsed.path == "/api/quick-reading/export":
            self.handle_speedread_export(parse_qs(parsed.query))
            return
        if parsed.path == "/api/library":
            metadata = load_metadata(self.runtime.metadata)
            self._send_json(200, {"ok": True, "papers": list(metadata.values())})
            return
        if parsed.path == "/api/ping":
            self._send_json(200, {"ok": True, "service": "watchdog", "api_version": 1})
            return
        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/import-pdf":
            if not self._settings_access(write=True, content_type="application/pdf"):
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= MAX_PDF_BYTES or self.headers.get("Transfer-Encoding"):
                    self._send_json(413, {"ok": False, "error": "单个 PDF 不能超过 50 MB，且不能为空"})
                    return
                data = self.rfile.read(length)
                if len(data) != length:
                    raise PDFImportError("文件上传不完整")
                result = import_pdf(self.runtime, unquote(self.headers.get("X-File-Name", "")), data)
                self._send_json(200, result)
            except ValueError as exc:
                self._send_json(400, {"ok": False, "error": str(exc)})
            except OSError:
                self._send_json(500, {"ok": False, "error": "无法写入论文库，请检查目录权限或磁盘空间"})
            return
        if parsed.path == "/api/preferences":
            if not self._settings_access(write=True): return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 8192 or self.headers.get("Transfer-Encoding"):
                    raise SettingsError("外观请求大小无效")
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict): raise SettingsError("外观请求格式无效")
                result = self.server.preferences.save(payload.get("values"), payload.get("revision"))
                self._send_json(200, {"ok": True, **result})
            except ConflictError as exc:
                self._send_json(409, {"ok": False, "error": str(exc)})
            except (ValueError, SettingsError):
                self._send_json(400, {"ok": False, "error": "外观配置无效，未保存"})
            except OSError:
                self._send_json(500, {"ok": False, "error": "外观保存失败，请检查磁盘权限"})
            return
        if parsed.path == "/api/settings":
            if not self._settings_access(write=True):
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 65536 or self.headers.get("Transfer-Encoding"):
                    raise SettingsError("配置请求大小无效")
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict) or set(payload) - {"provider", "revision", "apiKey", "reset"}:
                    raise SettingsError("配置请求格式无效")
                result = (self.server.settings.reset(payload.get("revision")) if payload.get("reset") is True
                          else self.server.settings.save(payload.get("provider"), payload.get("revision"), payload.get("apiKey")))
                self._send_json(200, {"ok": True, **result})
            except ConflictError as exc:
                self._send_json(409, {"ok": False, "error": str(exc)})
            except (SettingsError, ValueError) as exc:
                message = str(exc) if isinstance(exc, SettingsError) else "配置 JSON 格式无效"
                self._send_json(400, {"ok": False, "error": message})
            return
        protected = parsed.path in ("/api/list-models", "/api/test-speedread-config",
                                    "/api/generate-speedread", "/api/quick-reading/generate")
        if protected and not self._settings_access(write=True):
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except (TypeError, ValueError):
            length = 0
        if length < 0 or length > 1048576 or self.headers.get("Transfer-Encoding"):
            self._send_json(413, {"ok": False, "error": "请求大小无效"})
            return
        body = self.rfile.read(length) if length > 0 else b""
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            self._send_json(400, {"ok": False, "error": "JSON 解析失败"})
            return

        if not isinstance(payload, dict):
            self._send_json(400, {"ok": False, "error": "请求必须是 JSON 对象"})
            return
        if protected:
            try:
                if payload.get("apiConfig") != {"useSaved": True}:
                    raise SettingsError("请刷新页面并使用已保存的后端配置")
                payload["apiConfig"] = self.server.settings.resolve()
            except SettingsError as exc:
                self._send_json(400, {"ok": False, "error": str(exc)})
                return
        if parsed.path in {"/api/delete-paper", "/api/delete-speedread", "/api/delete-tag",
                           "/api/recycle-restore", "/api/recycle-purge", "/api/recycle-purge-all",
                           "/api/save-metadata", "/api/update-paper"}:
            with library_lock(self.runtime.library_root):
                self._dispatch_post(parsed, payload)
        else:
            self._dispatch_post(parsed, payload)

    def _dispatch_post(self, parsed, payload):
        if parsed.path == "/api/delete-paper":
            self.handle_delete_paper(payload)
            return
        if parsed.path == "/api/delete-speedread":
            self.handle_delete_speedread(payload)
            return
        if parsed.path == "/api/delete-tag":
            self.handle_delete_tag(payload)
            return
        if parsed.path == "/api/list-models":
            self.handle_list_models(payload)
            return
        if parsed.path == "/api/recycle-restore":
            self.handle_recycle_restore(payload)
            return
        if parsed.path == "/api/recycle-purge":
            self.handle_recycle_purge(payload)
            return
        if parsed.path == "/api/recycle-purge-all":
            self.handle_recycle_purge_all()
            return
        if parsed.path == "/api/save-metadata":
            self.handle_save_metadata(payload)
            return
        if parsed.path == "/api/update-paper":
            self.handle_update_paper(payload)
            return
        if parsed.path == "/api/generate-speedread":
            self.handle_generate_speedread(payload)
            return
        if parsed.path == "/api/quick-reading/generate":
            self.handle_generate_speedread(payload)
            return
        if parsed.path == "/api/list-speedread-cache":
            self.handle_list_speedread_cache(payload)
            return
        if parsed.path == "/api/test-speedread-config":
            self.handle_test_speedread_config(payload)
            return
        self._send_json(404, {"ok": False, "error": "未知接口"})

    # ------- recycle bin -------
    def handle_delete_paper(self, payload):
        file_key = (payload.get("file_key") or "").strip()
        result = delete_paper(file_key, self.runtime.library_root, self.runtime.metadata, self.runtime.recycle)
        self._send_json(result.status, result.payload)

    def handle_delete_speedread(self, payload):
        file_key = (payload.get("file_key") or "").strip()
        result = delete_speedread(file_key, self.runtime.library_root, self.runtime.metadata, self.runtime.speedreads, self.runtime.recycle)
        self._send_json(result.status, result.payload)

    def handle_recycle_list(self):
        result = list_recycle_bin(self.runtime.recycle)
        self._send_json(result.status, result.payload)

    def handle_delete_tag(self, payload):
        result = delete_tag(payload.get("tag"), self.runtime.library_root, self.runtime.metadata, self.runtime.recycle)
        self._send_json(result.status, result.payload)

    def handle_recycle_restore(self, payload):
        rid = payload.get("id")
        result = restore_recycle_item(rid, self.runtime.library_root, self.runtime.build_script, self.runtime.metadata, self.runtime.recycle, self.runtime.speedreads)
        self._send_json(result.status, result.payload)

    def handle_recycle_purge(self, payload):
        rid = payload.get("id")
        result = purge_paper(rid, self.runtime.recycle)
        self._send_json(result.status, result.payload)

    def handle_recycle_purge_all(self):
        result = purge_all_papers(self.runtime.recycle)
        self._send_json(result.status, result.payload)

    # ------- metadata persistence -------
    def handle_save_metadata(self, payload):
        data = payload.get("data")
        result = save_metadata(data, self.runtime.metadata)
        self._send_json(result.status, result.payload)

    def handle_update_paper(self, payload):
        file_key = (payload.get("file_key") or "").strip()
        fields = payload.get("fields")
        result = update_paper(file_key, fields, self.runtime.metadata)
        self._send_json(result.status, result.payload)

    # ------- paper speed-read -------
    # ------- paper speed-read -------
    def handle_speedread_cache(self, query):
        file_key = (query.get("file_key") or [""])[0].strip()
        result = get_speedread_cache(file_key, self.runtime.library_root, self.runtime.speedreads)
        self._send_json(result.status, result.payload)

    def handle_list_speedread_cache(self, payload):
        file_keys = payload.get("file_keys") or []
        result = list_speedread_cache(file_keys, self.runtime.library_root, self.runtime.speedreads)
        self._send_json(result.status, result.payload)

    def handle_generate_speedread(self, payload):
        file_key = (payload.get("file_key") or "").strip()
        api_config = payload.get("apiConfig") or {}
        options = payload.get("options") or {}
        force = bool(payload.get("force"))
        result = generate_speedread(
            file_key, api_config, force,
            self.runtime.library_root, self.runtime.metadata, self.runtime.speedreads,
            SPEEDREAD_MAX_IMAGE_PAGES, SPEEDREAD_IMAGE_WIDTH, SPEEDREAD_MAX_SOURCE_CHARS,
            options=options,
        )
        self._send_json(result.status, result.payload)

    def handle_speedread_export(self, query):
        file_key = (query.get("file_key") or [""])[0].strip()
        export_format = (query.get("format") or [""])[0].strip()
        result = export_speedread(file_key, export_format, self.runtime.library_root, self.runtime.metadata, self.runtime.speedreads)
        payload = result.payload if isinstance(result.payload, dict) else {}
        if result.status == 200 and isinstance(payload.get("data"), (bytes, bytearray)):
            self._send_binary(result.status, payload["data"], payload.get("content_type"), payload.get("filename"))
            return
        self._send_json(result.status, payload or {"ok": False, "error": "导出失败"})

    def handle_test_speedread_config(self, payload):
        api_config = payload.get("apiConfig") or {}
        result = test_speedread_config(api_config, self.runtime.library_root)
        self._send_json(result.status, result.payload)

    def handle_list_models(self, payload):
        if not isinstance(payload, dict) or not isinstance(payload.get("apiConfig"), dict):
            self._send_json(400, {"ok": False, "error": "apiConfig 格式不正确"})
            return
        api_config = payload["apiConfig"]
        try:
            result = list_models(api_config, force=payload.get("force") is True)
            self._send_json(200, result)
        except (ValueError, RuntimeError) as exc:
            message = str(exc)
            key = api_config.get("apiKey")
            if isinstance(key, str) and key.strip():
                message = message.replace(key.strip(), "[API Key 已隐藏]")
            self._send_json(400 if isinstance(exc, ValueError) else 502, {"ok": False, "error": message[:600]})

    def handle_getlog(self, query):
        try:
            tail = int((query.get("tail") or ["500"])[0])
        except (TypeError, ValueError):
            tail = 500
        tail = max(1, min(tail, 5000))

        log_file = _resolve_log_file(self.runtime)
        if not os.path.exists(log_file):
            self._send_json(200, {"ok": True, "path": log_file, "lines": [], "truncated": False})
            return
        try:
            with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()
        except Exception as exc:
            self._send_json(500, {"ok": False, "error": f"读取日志失败: {exc}"})
            return
        truncated = len(all_lines) > tail
        lines = all_lines[-tail:]
        self._send_json(200, {
            "ok": True,
            "path": log_file,
            "total": len(all_lines),
            "returned": len(lines),
            "truncated": truncated,
            "lines": [ln.rstrip("\n") for ln in lines],
        })

    def handle_open_folder(self, query):
        raw = (query.get("path") or [""])[0]
        rel_path = unquote(raw).replace("/", os.sep).replace("\\", os.sep)
        if not rel_path:
            self._send_json(400, {"ok": False, "error": "缺少 path 参数"})
            return

        # Prevent path traversal outside the workspace.
        if rel_path == "papers":
            rel_path = "."
        elif rel_path.startswith("papers" + os.sep):
            rel_path = rel_path[len("papers") + 1:]
        abs_path = safe_rel(rel_path, self.runtime.papers)
        if not abs_path:
            self._send_json(403, {"ok": False, "error": "禁止访问论文库外的路径"})
            return

        if not os.path.exists(abs_path):
            self._send_json(404, {"ok": False, "error": f"路径不存在: {abs_path}"})
            return

        try:
            if sys.platform.startswith("win"):
                # Let the new process request foreground window focus.
                try:
                    import ctypes
                    ASFW_ANY = -1
                    ctypes.windll.user32.AllowSetForegroundWindow(ASFW_ANY)
                except Exception:
                    pass

                if os.path.isdir(abs_path):
                    os.startfile(abs_path)  # type: ignore[attr-defined]
                else:
                    # Open the parent folder and select the target file.
                    subprocess.Popen(
                        ["explorer", "/select,", abs_path],
                        close_fds=True,
                    )

                # Second pass: bring the matching Explorer window forward.
                threading.Thread(
                    target=_bring_explorer_to_front,
                    args=(abs_path,),
                    daemon=True,
                ).start()
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-R", abs_path] if os.path.isfile(abs_path) else ["open", abs_path])
            else:
                # Linux: try to reveal/select the file in the file manager.
                if os.path.isfile(abs_path):
                    # GNOME / Nautilus via org.freedesktop.FileManager1 DBus
                    try:
                        subprocess.Popen([
                            "dbus-send", "--print-reply",
                            "--dest=org.freedesktop.FileManager1",
                            "/org/freedesktop/FileManager1",
                            "org.freedesktop.FileManager1.ShowItems",
                            f"array:string:file://{abs_path}",
                            "string:openpaper",
                        ])
                    except FileNotFoundError:
                        pass
                    else:
                        self._send_json(200, {"ok": True, "path": abs_path})
                        return
                    # KDE / Dolphin
                    try:
                        subprocess.Popen(["dolphin", "--select", abs_path])
                    except FileNotFoundError:
                        pass
                    else:
                        self._send_json(200, {"ok": True, "path": abs_path})
                        return
                # Fallback: open parent directory
                target = abs_path if os.path.isdir(abs_path) else os.path.dirname(abs_path)
                subprocess.Popen(["xdg-open", target])
        except Exception as exc:
            self._send_json(500, {"ok": False, "error": f"打开失败: {exc}"})
            return

        self._send_json(200, {"ok": True, "path": abs_path})

    def log_message(self, format, *args):  # 静默模式
        return


class QuietThreadingHTTPServer(ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        exc_type, exc, _traceback = sys.exc_info()
        if isinstance(exc, (BrokenPipeError, ConnectionAbortedError, ConnectionResetError)):
            return
        super().handle_error(request, client_address)

def create_server(paths, port=HTTP_PORT, settings=None):
    """Construct an isolated server. Call bootstrap/scan explicitly before serving."""
    server = QuietThreadingHTTPServer(("127.0.0.1", port), PaperRequestHandler)
    server.runtime = paths
    server.settings = settings if settings is not None else SettingsStore()
    server.preferences = PreferencesStore(server.settings.path.parent)
    return server


def main(argv=None):
    configure_stdio()
    parser = argparse.ArgumentParser(description="OpenPaper local service")
    parser.add_argument("--port", "-p", type=int, default=HTTP_PORT)
    parser.add_argument("--library-root", help="User library containing papers/; defaults to the legacy repository library")
    parser.add_argument("--config-root", help="Private settings directory; defaults to OS user application data")
    parser.add_argument("--resource-root", help="Read-only legacy frontend assets")
    parser.add_argument("--ready-json", action="store_true", help="Emit a JSON readiness event for a future desktop host")
    args = parser.parse_args(argv)
    if not 0 <= args.port <= 65535:
        parser.error("port must be between 0 and 65535")
    paths = RuntimePaths.resolve(args.library_root, args.resource_root)
    try:
        httpd = create_server(paths, args.port, SettingsStore(args.config_root))
    except OSError as exc:
        parser.exit(1, f"无法绑定 127.0.0.1:{args.port}: {exc}\n")

    stopped = threading.Event()
    observer = Observer()
    serving = False
    watching = False
    old_signals = {}
    try:
        bootstrap(paths)
        scan_library(paths.library_root)
        handler = PDFHandler(
            build_callback=lambda: scan_library(paths.library_root),
            workspace_root=paths.library_root,
        )
        observer.schedule(handler, paths.papers, recursive=True)
        observer.start()
        watching = True
        http_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        http_thread.start()
        serving = True
        if threading.current_thread() is threading.main_thread():
            for signum in (signal.SIGINT, signal.SIGTERM):
                old_signals[signum] = signal.signal(signum, lambda *_: stopped.set())
        port = httpd.server_address[1]
        log(f"HTTP 服务已启动: http://127.0.0.1:{port}")
        log(f"监控已启动: {paths.papers}")
        if args.ready_json:
            print(json.dumps({"event": "ready", "api_version": 1, "host": "127.0.0.1", "port": port}), flush=True)
        stopped.wait()
    finally:
        if watching:
            observer.stop()
            observer.join()
        if 'handler' in locals():
            handler.close()
        if serving:
            httpd.shutdown()
            http_thread.join()
        httpd.server_close()
        for signum, previous in old_signals.items():
            signal.signal(signum, previous)


if __name__ == "__main__":
    main()
