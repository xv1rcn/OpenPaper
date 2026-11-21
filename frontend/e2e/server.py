"""Disposable library for real HTTP browser tests; never touches user files."""
import json
import fitz
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.server import create_server
from backend.runtime.paths import RuntimePaths
from backend.runtime.bootstrap import bootstrap
from backend.settings.store import SettingsStore
from backend.quick_reading.storage import write_speedread_cache

class TestVault:
    def __init__(self): self.values = {}
    def get(self, key): return self.values.get(key)
    def set(self, key, value): self.values[key] = value
    def delete(self, key): self.values.pop(key, None)

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
        with fitz.open() as doc:
            for page_number in range(2):
                page = doc.new_page()
                page.insert_text((72,72), f"{title} - page {page_number+1}")
            doc.save(Path(paths.papers) / filename)
        metadata[filename] = dict(file_key=filename, title=title, tags=tags, read=read,
            authors="Test Author", year=str(2024 + index), venue="RESEARCH", notes="",
            pdf="papers/" + filename, added_at=f"2026-01-0{index+1}")
    Path(paths.metadata).write_text(json.dumps(metadata), encoding="utf-8")
    write_speedread_cache('fixture-2.pdf', {
        'status': 'success', 'version': 1, 'model': 'test-model',
        'content': {'problem_and_motivation': 'Long motivation evidence. ' * 300 + 'LONG-CONTENT-END', 'one_sentence': 'Verified cached summary', 'quick_takeaways': ['Evidence survives export'],
            'method_overview': 'A reproducible test method', 'method_steps': ['First step', 'Second step'],
            'technical_detail_read': {'summary': 'Technical context', 'modules': [{'name': 'Module A', 'role': 'Testing', 'mechanism': 'Controlled fixture', 'page_refs': [2]}]},
            'experiment_read': {'summary': 'Experimental evidence'}, 'limitations': ['Synthetic fixture only']},
        'options': {'depth': 'deep', 'focus': ['experiment'], 'include_figure_insights': False, 'max_figures': 7, 'extra_prompt': 'Keep evidence'}
    }, paths.library_root, paths.speedreads)
    create_server(paths, 8765, SettingsStore(Path(temp) / "config", TestVault())).serve_forever()
