"""Per-library locks shared by HTTP mutations and the filesystem scanner.

These coordinate threads in one process, not separate backend instances.
"""
from pathlib import Path
from threading import Lock, RLock

_guard = Lock()
_locks = {}


def library_lock(root):
    key = str(Path(root).resolve())
    with _guard:
        return _locks.setdefault(key, RLock())
