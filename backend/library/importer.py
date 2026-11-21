"""Validate and copy an uploaded PDF without modifying the source file."""
import hashlib
import os
from pathlib import Path
import re
import tempfile
import unicodedata

import pymupdf

from .locking import library_lock
from .scanner import scan_library

MAX_PDF_BYTES = 50 * 1024 * 1024


class PDFImportError(ValueError):
    pass


def import_pdf(paths, filename, content):
    if not isinstance(filename, str) or not filename.lower().endswith('.pdf'):
        raise PDFImportError('请选择 PDF 文件')
    if any(c in filename for c in ('/', '\\', '\x00')) or len(filename) > 240:
        raise PDFImportError('文件名无效')
    if not 0 < len(content) <= MAX_PDF_BYTES:
        raise PDFImportError('单个 PDF 不能超过 50 MB，且不能为空')
    try:
        with pymupdf.open(stream=content, filetype='pdf') as document:
            if not document.is_pdf or document.needs_pass or document.page_count < 1:
                raise PDFImportError('暂不支持加密或没有页面的 PDF')
    except PDFImportError:
        raise
    except Exception:
        raise PDFImportError('文件不是可读取的 PDF') from None

    stem = unicodedata.normalize('NFC', Path(filename).stem)
    stem = re.sub(r'[<>:"|?*\x00-\x1f]', '_', stem).strip(' .')[:100] or 'paper'
    while len(stem.encode('utf-8')) > 200:
        stem = stem[:-1]
    if stem.lower() in {'con', 'prn', 'aux', 'nul'} or re.fullmatch(r'(com|lpt)[1-9]', stem.lower()):
        stem = 'paper_' + stem
    with library_lock(paths.library_root):
        folder = Path(paths.papers) / 'imported'
        try:
            folder.resolve().relative_to(Path(paths.library_root).resolve())
        except ValueError:
            raise PDFImportError('导入目录不能位于论文库之外') from None
        if Path(paths.papers).is_symlink() or folder.is_symlink():
            raise PDFImportError('导入目录不能是符号链接')
        folder.mkdir(parents=True, exist_ok=True)
        names = {p.name.lower(): p for p in folder.iterdir()}
        target = folder / (stem + '.pdf')
        duplicate = False
        counter = 1
        while target.name.lower() in names:
            existing = names[target.name.lower()]
            if not existing.is_symlink() and existing.is_file() and existing.stat().st_size == len(content):
                if hashlib.sha256(existing.read_bytes()).digest() == hashlib.sha256(content).digest():
                    target, duplicate = existing, True
                    break
            counter += 1
            target = folder / f'{stem} ({counter}).pdf'
        if not duplicate:
            fd, temporary = tempfile.mkstemp(prefix='.upload-', suffix='.tmp', dir=folder)
            try:
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
                # Hard-link publication fails instead of overwriting an existing file.
                os.link(temporary, target)
            finally:
                Path(temporary).unlink(missing_ok=True)
        key = 'imported/' + target.name.lower()
        result = {'ok': True, 'file_key': key, 'duplicate': duplicate, 'indexed': True}
        try:
            scan_library(paths.library_root)
        except Exception:
            # The durable PDF is preserved even if indexing fails. A later scan retries.
            result.update(indexed=False, warning='PDF 已保存，但索引更新失败；请稍后重新导入同一文件以重试')
        return result
