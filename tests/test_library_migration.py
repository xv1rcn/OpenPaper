import json
from pathlib import Path
import tempfile
import unittest
from scripts.migrate_library import migrate
from backend.runtime.bootstrap import bootstrap
from backend.runtime.paths import RuntimePaths
from backend.quick_reading.storage import load_speedread_cache


class LibraryMigrationTests(unittest.TestCase):
    def test_copy_then_bootstrap_retains_pdf_metadata_results_and_originals(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, target = root / '旧库', root / '桌面/library'
            (source / 'papers/topic').mkdir(parents=True)
            pdf = source / 'papers/topic/paper.pdf'
            pdf.write_bytes(b'%PDF-fixture')
            original = {'topic/paper.pdf': {'title': '原始标题', 'tags': ['实验'], 'notes': '笔记', 'read': True,
                'custom': {'keep': 0}, 'speed_read': {'status': 'success', 'content': {'summary': '原有结果'}}}}
            (source / 'metadata.json').write_text(json.dumps(original), encoding='utf-8')
            (source / '.recycle_bin/item').mkdir(parents=True)
            (source / '.recycle_bin/item/data.json').write_text('{}')
            (source / 'config').mkdir()
            (source / 'config/settings.json').write_text('private-placeholder')
            (source / '.speedread_cache/legacy').mkdir(parents=True)
            (source / '.speedread_cache/legacy/image.png').write_bytes(b'image-fixture')
            before = {str(p.relative_to(source)): p.read_bytes() for p in source.rglob('*') if p.is_file()}
            migrate(source, target)
            paths = RuntimePaths.resolve(target)
            bootstrap(paths)
            self.assertEqual((target / 'papers/topic/paper.pdf').read_bytes(), pdf.read_bytes())
            metadata = json.loads(Path(paths.metadata).read_text())
            self.assertEqual(metadata['topic/paper.pdf'], {k: v for k, v in original['topic/paper.pdf'].items() if k != 'speed_read'})
            self.assertEqual(load_speedread_cache('topic/paper.pdf', paths.library_root, paths.speedreads)['content']['summary'], '原有结果')
            self.assertEqual(json.loads(Path(paths.metadata + '.before-inline-migration.bak').read_text()), original)
            self.assertEqual((Path(paths.speedreads) / 'legacy/image.png').read_bytes(), b'image-fixture')
            self.assertTrue((target / '.recycle_bin/item/data.json').exists())
            self.assertFalse((target / 'config').exists())
            self.assertEqual(before, {str(p.relative_to(source)): p.read_bytes() for p in source.rglob('*') if p.is_file()})
            bootstrap(paths)
            self.assertEqual(json.loads(Path(paths.metadata).read_text()), metadata)

    def test_refuses_existing_destination_and_nested_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'source'
            (source / 'papers').mkdir(parents=True)
            for target in (source, source / 'copy', source.parent):
                with self.subTest(target=target), self.assertRaises(ValueError):
                    migrate(source, target)

    def test_refuses_symlinks_without_creating_partial_library(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'source/papers').mkdir(parents=True)
            (root / 'outside').write_text('private')
            (root / 'source/papers/link.pdf').symlink_to(root / 'outside')
            with self.assertRaises(ValueError):
                migrate(root / 'source', root / 'destination')
            self.assertFalse((root / 'destination').exists())
