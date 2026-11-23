"""Copy an offline legacy library into a NEW desktop library; never merge or move."""
import argparse
from pathlib import Path
import shutil
import tempfile

DATA_NAMES = ("papers", "metadata.json", "stats.data.json", ".speedread_cache",
              ".recycle_bin", ".legacy-speedread-migrated-v1")


def migrate(source, destination):
    source = Path(source).expanduser().resolve()
    destination = Path(destination).expanduser().absolute()
    if not (source / "papers").is_dir():
        raise ValueError("源目录必须包含 papers/，不要直接选择 papers/。")
    if destination.exists() or destination.is_symlink():
        raise ValueError("目标目录已存在；请先备份并移走，禁止合并或覆盖现有书库。")
    resolved = destination.resolve()
    if source == resolved or source in resolved.parents or resolved in source.parents:
        raise ValueError("源目录和目标目录不能互相包含。")
    selected = [source / name for name in DATA_NAMES if (source / name).exists() or (source / name).is_symlink()]
    for path in selected:
        if path.is_symlink() or (path.is_dir() and any(p.is_symlink() for p in path.rglob("*"))):
            raise ValueError("书库包含符号链接；请先在副本中替换为实际文件后迁移。")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".openpaper-migration-", dir=destination.parent) as temporary:
        staged = Path(temporary) / "library"
        staged.mkdir()
        for path in selected:
            target = staged / path.name
            if path.is_dir():
                shutil.copytree(path, target)
            else:
                shutil.copy2(path, target)
        # No bootstrap here: preserve bytes and let the normal startup migration
        # retain inline metadata backups. Destination must remain absent offline.
        if destination.exists() or destination.is_symlink():
            raise ValueError("目标目录在复制期间被创建，已中止迁移。")
        staged.rename(destination)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--destination", required=True)
    args = parser.parse_args()
    try:
        result = migrate(args.source, args.destination)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"迁移未完成：{exc}\n")
    print(f"书库副本已保存到 {result}；源文件未更改。模型配置请在应用设置中重新填写。")


if __name__ == "__main__":
    main()
