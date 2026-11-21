"""Desktop foundation regressions using isolated resources and user libraries."""
import json
import os
from pathlib import Path
import selectors
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import ProxyHandler, build_opener

from backend.library.scanner import scan_library
from backend.runtime.bootstrap import bootstrap
from backend.runtime.paths import RuntimePaths
from backend.server import create_server
from backend.utils import safe_rel
from backend.watcher import PDFHandler

REPO = Path(__file__).resolve().parents[1]


class RuntimeTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="openpaper-runtime-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.resources = self.root / "resources"
        self.resources.mkdir()
        (self.resources / "index.html").write_text("<html>fixture</html>", encoding="utf-8")
        (self.resources / "backend.py").write_text("private source", encoding="utf-8")
        (self.resources / "frontend/dist").mkdir(parents=True)
        (self.resources / "frontend/dist/index.html").write_text("<html>fixture</html>")
        self.library = self.root / "library"
        self.paths = RuntimePaths.resolve(self.library, self.resources)

    def make_paper(self, name="Topic/paper-icml24.pdf"):
        pdf = Path(self.paths.papers) / name
        pdf.parent.mkdir(parents=True, exist_ok=True)
        pdf.write_bytes(b"%PDF-1.4 test fixture")
        return pdf

    def start_server(self, paths=None):
        server = create_server(paths or self.paths, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def stop():
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        self.addCleanup(stop)
        return "http://127.0.0.1:" + str(server.server_address[1])


class RuntimeIsolationTests(RuntimeTestCase):
    def test_resolving_paths_does_not_create_or_change_directories(self):
        cwd = os.getcwd()
        self.assertFalse(self.library.exists())
        self.assertNotEqual(self.paths.resource_root, self.paths.library_root)
        self.assertEqual(os.getcwd(), cwd)

    def test_importing_server_does_not_bootstrap_data(self):
        isolated = self.root / "isolated"
        isolated.mkdir()
        shutil.copytree(REPO / "backend", isolated / "backend", ignore=shutil.ignore_patterns("__pycache__"))
        (isolated / "metadata.json").write_text("{}", encoding="utf-8")
        env = dict(os.environ, PYTHONPATH=str(isolated), PYTHONDONTWRITEBYTECODE="1")
        subprocess.run([sys.executable, "-c", "import backend.server"], cwd=self.root,
                       env=env, check=True, capture_output=True, timeout=20)
        self.assertFalse((isolated / "papers").exists())
        self.assertTrue((isolated / "metadata.json").exists())

    def test_scan_external_library_preserves_fields_and_does_not_build_ui(self):
        self.make_paper()
        metadata = {"topic/paper-icml24.pdf": {"title": "User title", "tags": [], "research": {"stage": "reading"}}}
        Path(self.paths.metadata).write_text(json.dumps(metadata), encoding="utf-8")
        cwd = os.getcwd()
        scanned = scan_library(self.paths.library_root)
        paper = scanned["topic/paper-icml24.pdf"]
        self.assertEqual(paper["title"], "User title")
        self.assertEqual(paper["tags"], [])
        self.assertEqual(paper["research"], {"stage": "reading"})
        self.assertEqual(paper["venue"], "ICML")
        self.assertEqual(paper["pdf"], "papers/Topic/paper-icml24.pdf")
        self.assertFalse((self.library / "index.html").exists())
        self.assertFalse((self.resources / "papers").exists())
        self.assertEqual(os.getcwd(), cwd)

    def test_scan_ignores_hidden_results_and_symlink_escape(self):
        self.make_paper()
        hidden = Path(self.paths.speedreads) / "report.pdf"
        hidden.parent.mkdir(parents=True)
        hidden.write_bytes(b"exported report")
        outside = self.root / "outside.pdf"
        outside.write_bytes(b"private")
        (Path(self.paths.papers) / "escape.pdf").symlink_to(outside)
        self.assertEqual(len(scan_library(self.paths.library_root)), 1)

    def test_bootstrap_keeps_legacy_source_and_does_not_import_demo_into_external_library(self):
        self.library.mkdir()
        old_meta = self.library / "metadata.json"
        old_meta.write_text("{}", encoding="utf-8")
        (self.resources / "metadata.demo.json").write_text('{"demo": {}}', encoding="utf-8")
        bootstrap(self.paths)
        self.assertTrue(old_meta.exists())
        self.assertEqual(json.loads(Path(self.paths.metadata).read_text()), {})
        self.assertFalse((self.resources / "papers").exists())

    def test_failed_inline_migration_does_not_discard_original_result(self):
        self.make_paper()
        original = {"topic/paper-icml24.pdf": {"speed_read": {"status": "success", "content": {"summary": "keep"}}}}
        Path(self.paths.metadata).write_text(json.dumps(original), encoding="utf-8")
        with patch("backend.runtime.bootstrap.write_speedread_cache", side_effect=OSError("disk full")):
            bootstrap(self.paths)
        self.assertEqual(json.loads(Path(self.paths.metadata).read_text()), original)

    def test_successful_inline_migration_retains_backup(self):
        self.make_paper()
        original = {"topic/paper-icml24.pdf": {"speed_read": {"status": "success"}}}
        Path(self.paths.metadata).write_text(json.dumps(original), encoding="utf-8")
        bootstrap(self.paths)
        self.assertNotIn("speed_read", json.loads(Path(self.paths.metadata).read_text())["topic/paper-icml24.pdf"])
        backup = Path(self.paths.metadata + ".before-inline-migration.bak")
        self.assertEqual(json.loads(backup.read_text()), original)

    def test_duplicate_legacy_results_are_preserved(self):
        old = self.library / ".speedread_cache" / "abc"
        new = Path(self.paths.speedreads) / "abc"
        old.mkdir(parents=True)
        new.mkdir(parents=True)
        (old / "speed_read.json").write_text("old", encoding="utf-8")
        (new / "speed_read.json").write_text("new", encoding="utf-8")
        bootstrap(self.paths)
        self.assertEqual((old / "speed_read.json").read_text(), "old")
        self.assertEqual((new / "speed_read.json").read_text(), "new")

    def test_relative_paths_reject_escape_and_absolute_inputs(self):
        self.make_paper()
        for path in ("../private", "/etc/passwd", "C:\\private", "bad\x00path"):
            self.assertIsNone(safe_rel(path, self.paths.library_root))

    def test_restart_does_not_resurrect_deleted_migrated_results(self):
        old = self.library / ".speedread_cache" / "abc"
        old.mkdir(parents=True)
        (old / "speed_read.json").write_text('{"status": "success"}', encoding="utf-8")
        bootstrap(self.paths)
        shutil.rmtree(Path(self.paths.speedreads) / "abc")
        bootstrap(self.paths)
        self.assertFalse((Path(self.paths.speedreads) / "abc").exists())
        self.assertTrue((old / "speed_read.json").exists())

    def test_watcher_shutdown_cancels_pending_callback(self):
        calls = []
        watcher = PDFHandler(lambda: calls.append(True), self.paths.library_root)
        watcher._schedule("test", "paper.pdf")
        watcher.close()
        watcher._schedule("test", "later.pdf")
        self.assertFalse(watcher._timer.is_alive())
        self.assertEqual(calls, [])


class RuntimeHTTPTests(RuntimeTestCase):
    def setUp(self):
        super().setUp()
        self.make_paper()
        bootstrap(self.paths)
        scan_library(self.paths.library_root)
        self.http = build_opener(ProxyHandler({}))

    def read(self, url):
        with self.http.open(url, timeout=5) as response:
            return response.read()

    def test_library_status_is_derived_without_changing_metadata(self):
        original = Path(self.paths.metadata).read_bytes()
        metadata = json.loads(original)
        key = next(iter(metadata))
        cache = Path(self.paths.speedreads)
        cache.mkdir(parents=True, exist_ok=True)
        index = cache / "index.json"
        base = self.start_server()
        for value, expected in [({"items": {key: {"status": "running"}}}, "running"),
                                ({"items": {key: {"status": "success"}}}, "success"),
                                ({"items": {key: None}}, ""), ({"items": []}, "")]:
            index.write_text(json.dumps(value))
            paper = json.loads(self.read(base + "/api/library"))["papers"][0]
            self.assertEqual(paper["speedread_status"], expected)
            self.assertEqual(Path(self.paths.metadata).read_bytes(), original)
        index.write_text("broken")
        self.assertEqual(json.loads(self.read(base + "/api/library"))["papers"][0]["speedread_status"], "")

    def test_static_and_library_api_use_different_roots(self):
        base = self.start_server()
        self.assertIn(b"fixture", self.read(base + "/"))
        self.assertTrue(json.loads(self.read(base + "/api/ping"))["ok"])
        papers = json.loads(self.read(base + "/api/library"))["papers"]
        self.assertEqual(len(papers), 1)
        self.assertTrue(self.read(base + "/" + papers[0]["pdf"]).startswith(b"%PDF"))

    def test_private_and_traversal_paths_are_not_served(self):
        base = self.start_server()
        outside = self.root / "secret.pdf"
        outside.write_bytes(b"private")
        (Path(self.paths.papers) / "leak.pdf").symlink_to(outside)
        for path in ("/backend.py", "/.git/config", "/.venv/pyvenv.cfg", "/papers/",
                     "/papers/metadata.json.before-inline-migration.bak", "/.recycle_bin/",
                     "/papers/%2e%2e/backend.py", "/papers/leak.pdf", "/papers/secret.json"):
            with self.subTest(path=path), self.assertRaises(HTTPError) as error:
                self.read(base + path)
            self.assertEqual(error.exception.code, 404)

    def test_built_frontend_is_allowlisted_without_exposing_sources(self):
        dist = self.resources / "frontend" / "dist"
        (dist / "assets").mkdir(parents=True, exist_ok=True)
        (dist / "index.html").write_text("<html>Vue app</html>")
        (dist / "assets" / "app.js").write_text("/* compiled */")
        (dist / "assets" / "app.js.map").write_text("private map")
        (self.resources / "frontend" / "package.json").write_text("private config")
        base = self.start_server()
        for path in ("/app", "/app/", "/app/index.html"):
            self.assertIn(b"Vue app", self.read(base + path))
        self.assertIn(b"compiled", self.read(base + "/app/assets/app.js"))
        for path in ("/frontend/package.json", "/app/assets/app.js.map", "/app/../package.json", "/app/src/main.ts"):
            with self.subTest(path=path), self.assertRaises(HTTPError) as error:
                self.read(base + path)
            self.assertEqual(error.exception.code, 404)
        (dist / "assets" / "escape.js").symlink_to(self.resources / "backend.py")
        with self.assertRaises(HTTPError):
            self.read(base + "/app/assets/escape.js")

    def test_two_servers_do_not_share_library_or_change_cwd(self):
        cwd = os.getcwd()
        other = RuntimePaths.resolve(self.root / "other-library", self.resources)
        bootstrap(other)
        scan_library(other.library_root)
        first, second = self.start_server(), self.start_server(other)
        self.assertEqual(len(json.loads(self.read(first + "/api/library"))["papers"]), 1)
        self.assertEqual(json.loads(self.read(second + "/api/library"))["papers"], [])
        self.assertEqual(os.getcwd(), cwd)

    def test_cli_ready_event_and_sigterm_release_port(self):
        proc = subprocess.Popen(
            [sys.executable, "-u", "-m", "backend", "--port", "0", "--ready-json",
             "--resource-root", str(self.resources), "--library-root", str(self.library)],
            cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        self.addCleanup(lambda: proc.poll() is None and proc.kill())
        try:
            ready = None
            output = b""
            with selectors.DefaultSelector() as selector:
                selector.register(proc.stdout, selectors.EVENT_READ)
                deadline = time.monotonic() + 60
                while time.monotonic() < deadline and ready is None:
                    for key, _ in selector.select(timeout=0.25):
                        chunk = os.read(key.fd, 65536)
                        if not chunk:
                            self.fail("server exited before readiness: " + output.decode())
                        output += chunk
                        for line in output.splitlines():
                            if line.startswith(b'{"event": "ready"'):
                                ready = json.loads(line)
            self.assertIsNotNone(ready, output.decode())
            self.assertGreater(ready["port"], 0)
            self.assertTrue(json.loads(self.read(f'http://127.0.0.1:{ready["port"]}/api/ping'))["ok"])
            proc.terminate()
            self.assertEqual(proc.wait(timeout=10), 0)
            self.assertFalse((self.resources / "papers").exists())
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5)
            proc.stdout.close()


if __name__ == "__main__":
    unittest.main()
