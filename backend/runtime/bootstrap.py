"""Legacy data migration, called explicitly once during application startup."""
import os
import shutil
from backend.metadata import load_metadata, atomic_write_metadata
from backend.quick_reading import write_speedread_cache, rebuild_speedread_index
from backend.utils import log
from backend.quick_reading.storage import load_speedread_cache

def _copy_if_missing(src, dst):
    if os.path.isfile(src) and not os.path.exists(dst):
        shutil.copy2(src, dst)


def _merge_tree(src, dst):
    """Copy legacy results without deleting originals or replacing newer results."""
    if not os.path.isdir(src) or os.path.realpath(src) == os.path.realpath(dst):
        return
    os.makedirs(dst, exist_ok=True)
    for name in os.listdir(src):
        source = os.path.join(src, name)
        target = os.path.join(dst, name)
        if os.path.islink(source):
            continue
        if os.path.isdir(source):
            _merge_tree(source, target)
        else:
            _copy_if_missing(source, target)


def _normalize_quick_reading_image_path(image_path: str) -> str:
    if not isinstance(image_path, str):
        return image_path
    normalized = image_path.replace("\\", "/")
    prefixes = (
        ".speedread_cache/",
        "papers/.cache/.quick_reading_cache/",
    )
    for prefix in prefixes:
        if normalized.startswith(prefix):
            suffix = normalized[len(prefix):].lstrip("/")
            return f"papers/.quick_reading_cache/{suffix}" if suffix else "papers/.quick_reading_cache"
    return normalized


def _rewrite_quick_reading_paths(speed_read: dict) -> bool:
    changed = False

    def rewrite_assets(items) -> None:
        nonlocal changed
        if not isinstance(items, list):
            return
        for item in items:
            if not isinstance(item, dict):
                continue
            image_path = item.get("image_path")
            normalized = _normalize_quick_reading_image_path(image_path)
            if normalized != image_path:
                item["image_path"] = normalized
                changed = True

    rewrite_assets(speed_read.get("candidate_pages"))
    content = speed_read.get("content")
    if isinstance(content, dict):
        rewrite_assets(content.get("core_figures"))
        rewrite_assets(content.get("figure_insights"))
    return changed


def _bootstrap_runtime_data_files(paths) -> None:
    os.makedirs(paths.papers, exist_ok=True)
    _copy_if_missing(os.path.join(paths.library_root, "metadata.json"), paths.metadata)
    _copy_if_missing(os.path.join(paths.library_root, "stats.data.json"), paths.stats)
    if (paths.library_root == paths.resource_root and not os.path.exists(paths.metadata)
            and os.path.exists(os.path.join(paths.resource_root, "metadata.demo.json"))):
        shutil.copy2(os.path.join(paths.resource_root, "metadata.demo.json"), paths.metadata)


def _bootstrap_quick_reading_cache(paths) -> None:
    # Keep originals for recovery, but never re-import a result the user later deletes.
    marker = os.path.join(paths.library_root, ".legacy-speedread-migrated-v1")
    if not os.path.exists(marker):
        _merge_tree(os.path.join(paths.library_root, ".speedread_cache"), paths.speedreads)
        _merge_tree(os.path.join(paths.papers, ".cache", ".quick_reading_cache"), paths.speedreads)
        with open(marker, "w", encoding="utf-8") as file_obj:
            file_obj.write("Legacy directories copied; originals retained as backups.\n")

    try:
        metadata = load_metadata(paths.metadata)
    except Exception as exc:
        log(f"读取速读缓存元数据失败: {exc}")
        return

    changed = False
    for file_key, entry in metadata.items():
        if not isinstance(entry, dict):
            continue
        if "speed_read" not in entry:
            continue
        speed_read = entry.get("speed_read")
        if isinstance(speed_read, dict):
            _rewrite_quick_reading_paths(speed_read)
            try:
                existing = load_speedread_cache(file_key, paths.library_root, paths.speedreads)
                if not existing:
                    write_speedread_cache(file_key, speed_read, paths.library_root, paths.speedreads)
                entry.pop("speed_read", None)
                changed = True
            except Exception as exc:
                log(f"迁移速读缓存失败 {file_key}: {exc}")

    if not changed:
        try:
            rebuild_speedread_index(list(metadata), paths.library_root, paths.speedreads)
        except Exception as exc:
            log(f"重建速读缓存索引失败: {exc}")
        return

    try:
        _copy_if_missing(paths.metadata, paths.metadata + ".before-inline-migration.bak")
        atomic_write_metadata(metadata, paths.metadata)
    except Exception as exc:
        log(f"写回速读缓存元数据失败: {exc}")
    try:
        rebuild_speedread_index(list(metadata), paths.library_root, paths.speedreads)
    except Exception as exc:
        log(f"重建速读缓存索引失败: {exc}")


def bootstrap(paths):
    _bootstrap_runtime_data_files(paths)
    _bootstrap_quick_reading_cache(paths)
