"""Resource and user-data locations. Resolution is pure; creation is explicit."""
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimePaths:
    resource_root: str
    library_root: str

    @classmethod
    def resolve(cls, library_root=None, resource_root=None):
        resources = Path(resource_root or Path(__file__).resolve().parents[2]).expanduser().resolve()
        # Compatibility default only. The desktop host will always pass a user library.
        library = Path(library_root).expanduser().resolve() if library_root else resources
        return cls(str(resources), str(library))

    @property
    def papers(self):
        return str(Path(self.library_root) / "papers")

    @property
    def metadata(self):
        return str(Path(self.papers) / "metadata.json")

    @property
    def stats(self):
        return str(Path(self.papers) / "stats.data.json")

    @property
    def speedreads(self):
        # Kept for compatibility; these are durable user results, not disposable cache.
        return str(Path(self.papers) / ".quick_reading_cache")

    @property
    def recycle(self):
        return str(Path(self.library_root) / ".recycle_bin")

    @property
    def log_file(self):
        return str(Path(self.library_root) / "watchdog.log")

    @property
    def legacy_log_file(self):
        return str(Path(self.library_root) / "waatchdog.log")

    @property
    def build_script(self):
        # Compatibility argument for old recycle APIs; no longer executed by them.
        return str(Path(self.resource_root) / "build.py")
