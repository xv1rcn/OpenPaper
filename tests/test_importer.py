import json
from pathlib import Path
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pymupdf
from backend.library.importer import import_pdf, PDFImportError, MAX_PDF_BYTES
from backend.runtime.paths import RuntimePaths
from backend.runtime.bootstrap import bootstrap


def pdf_bytes(text='test'):
    with pymupdf.open() as doc:
        doc.new_page().insert_text((72, 72), text)
        return doc.tobytes()


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.paths = RuntimePaths.resolve(self.temp.name)
        bootstrap(self.paths)
        self.content = pdf_bytes()

    def test_import_indexes_and_identical_retry_does_not_duplicate(self):
        first = import_pdf(self.paths, '论文.pdf', self.content)
        second = import_pdf(self.paths, '论文.pdf', self.content)
        self.assertFalse(first['duplicate'])
        self.assertTrue(second['duplicate'])
        self.assertEqual(first['file_key'], second['file_key'])
        metadata = json.loads(Path(self.paths.metadata).read_text())
        self.assertIn(first['file_key'], metadata)
        self.assertEqual(len(metadata), 1)

    def test_collision_never_overwrites_existing_pdf(self):
        first = import_pdf(self.paths, 'test.pdf', self.content)
        second = import_pdf(self.paths, 'TEST.pdf', pdf_bytes('different'))
        self.assertNotEqual(first['file_key'], second['file_key'])
        self.assertEqual((Path(self.paths.papers) / first['file_key']).read_bytes(), self.content)

    def test_invalid_paths_and_documents_are_rejected_without_files(self):
        for filename, content in [('../bad.pdf', self.content), ('bad\\name.pdf', self.content),
                                  ('note.txt', self.content), ('fake.pdf', b'not a PDF'), ('empty.pdf', b'')]:
            with self.subTest(filename=filename), self.assertRaises(PDFImportError):
                import_pdf(self.paths, filename, content)
        self.assertFalse((Path(self.paths.papers) / 'imported').exists())

    def test_encrypted_document_is_rejected(self):
        with pymupdf.open() as doc:
            doc.new_page()
            content = doc.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw='owner', user_pw='user')
        with self.assertRaises(PDFImportError):
            import_pdf(self.paths, 'locked.pdf', content)

    def test_oversize_is_rejected_before_pdf_parsing(self):
        with patch('backend.library.importer.MAX_PDF_BYTES', 2), self.assertRaises(PDFImportError):
            import_pdf(self.paths, 'large.pdf', self.content)

    def test_symlink_directory_cannot_escape_library(self):
        with tempfile.TemporaryDirectory() as outside:
            (Path(self.paths.papers) / 'imported').symlink_to(outside)
            with self.assertRaises(PDFImportError):
                import_pdf(self.paths, 'test.pdf', self.content)
            self.assertEqual(list(Path(outside).iterdir()), [])

    def test_index_failure_keeps_pdf_and_retry_recovers(self):
        with patch('backend.library.importer.scan_library', side_effect=OSError('disk full')):
            result = import_pdf(self.paths, 'test.pdf', self.content)
        self.assertFalse(result['indexed'])
        self.assertTrue((Path(self.paths.papers) / result['file_key']).exists())
        retried = import_pdf(self.paths, 'test.pdf', self.content)
        self.assertTrue(retried['indexed'])
        self.assertTrue(retried['duplicate'])

    def test_parallel_imports_preserve_both_metadata_entries(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(import_pdf, self.paths, 'same.pdf', data) for data in (self.content, pdf_bytes('other'))]
            results = [future.result() for future in futures]
        metadata = json.loads(Path(self.paths.metadata).read_text())
        self.assertEqual(set(metadata), {r['file_key'] for r in results})

    def test_publish_failure_leaves_no_partial_file(self):
        with patch('backend.library.importer.os.link', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                import_pdf(self.paths, 'test.pdf', self.content)
        self.assertEqual(list((Path(self.paths.papers) / 'imported').iterdir()), [])

    def test_unicode_filename_respects_filesystem_byte_limit(self):
        result = import_pdf(self.paths, '论' * 100 + '.pdf', self.content)
        self.assertTrue(result['indexed'])

    def test_http_import_guards_and_valid_upload(self):
        from http.client import HTTPConnection
        from threading import Thread
        from urllib.parse import quote
        from backend.server import create_server
        server = create_server(self.paths, 0)
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            def request(headers, body=b''):
                connection = HTTPConnection('127.0.0.1', server.server_port, timeout=5)
                try:
                    connection.request('POST', '/api/import-pdf', body=body, headers=headers)
                    response = connection.getresponse()
                    return response.status, json.loads(response.read())
                finally:
                    connection.close()
            headers = {'Content-Type': 'application/pdf', 'X-OpenPaper-Request': '1', 'X-File-Name': quote('论文.pdf')}
            self.assertEqual(request({}, self.content)[0], 403)
            self.assertEqual(request({**headers, 'Origin': 'https://evil.example'}, self.content)[0], 403)
            self.assertEqual(request({**headers, 'Content-Length': str(MAX_PDF_BYTES+1)})[0], 413)
            status, result = request(headers, self.content)
            self.assertEqual(status, 200)
            self.assertTrue(result['indexed'])
        finally:
            server.shutdown()
            worker.join(5)
            server.server_close()
