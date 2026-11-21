"""Disposable library for real HTTP browser tests; never touches user files."""
import json
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.server import create_server
from backend.runtime.paths import RuntimePaths
from backend.runtime.bootstrap import bootstrap
from backend.settings.store import SettingsStore

with tempfile.TemporaryDirectory(prefix="openpaper-e2e-") as temp:
    paths = RuntimePaths.resolve(temp)
    bootstrap(paths)
    metadata = {}
    for index, (title, tags, read) in enumerate([
        ("Understanding Out-of-Distribution Detection", ["OOD", "Vision"], False),
        ("Learning Visual Representations from Language", ["Vision", "Multimodal"], True),
        ("Exploring Virtual Reality Scenes", ["Testing"], False),
    ]):
        filename = f"fixture-{index}.pdf"
        (Path(paths.papers) / filename).write_bytes(b"%PDF-1.4\n%%EOF")
        metadata[filename] = dict(file_key=filename, title=title, tags=tags, read=read,
            authors="Test Author", year=str(2024 + index), venue="RESEARCH", notes="",
            pdf="papers/" + filename, added_at=f"2026-01-0{index+1}")
    Path(paths.metadata).write_text(json.dumps(metadata), encoding="utf-8")
    create_server(paths, 8765, SettingsStore(Path(temp) / "config")).serve_forever()
