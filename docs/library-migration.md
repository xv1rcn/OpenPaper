# 从旧浏览器书库迁移到桌面版

桌面程序默认使用独立数据目录，不会自动寻找并搬移旧仓库。迁移保留源文件，禁止直接合并覆盖已使用的桌面书库。以下流程为离线复制；不属于跨版本安装器升级验证。

## 数据位置

| 平台 | 默认桌面数据目录 |
| --- | --- |
| macOS | `~/Library/Application Support/org.openpaper.desktop/` |
| Windows | `%APPDATA%/org.openpaper.desktop/` |
| Linux | `$XDG_DATA_HOME/org.openpaper.desktop/`，通常为 `~/.local/share/org.openpaper.desktop/` |

设置过 `OPENPAPER_DATA_DIR` 时使用其指定位置。目录中 `library/` 保存论文、元数据和速读，`config/` 保存普通设置、外观和视图状态。API Key 在系统凭据库中；复制目录不等于复制密钥。

浏览器服务未指定 `--library-root` 时，旧书库根是仓库目录（其下包含 `papers/`）；指定过时以该参数为准。传给迁移工具的是包含 papers/ 的根目录，不能直接传 papers/。

## 操作步骤

1. 完整退出桌面程序和旧浏览器后端，避免复制过程中继续写入。
2. 备份旧书库及现有桌面数据目录。若桌面已有 `library/`，将其改名为例如 `library.before-migration`；不要删除。工具会拒绝已经存在的目标，即使目标为空。
3. 在仓库根目录执行复制（下面为 macOS 示例，替换源目录）：

```sh
.venv/bin/python scripts/migrate_library.py \
  --source /absolute/path/to/old-OpenPaper \
  --destination "$HOME/Library/Application Support/org.openpaper.desktop/library"
```

Windows 使用 `.venv\Scripts\python.exe` 和对应的绝对路径；Linux 使用上表中的目标路径。工具会复制 papers/（包含隐藏速读缓存）、旧根元数据、旧速读目录和回收站；不复制源码、虚拟环境、日志或配置目录。符号链接会被拒绝，请先在备份副本中整理为实际文件。

4. 启动桌面应用。正常 bootstrap 将旧元数据及速读转换为当前布局；原目录不变，内嵌结果迁移前的 metadata 备份保留在目标书库。
5. 对照论文数量，并抽查 PDF、标题、标签、笔记、已读状态、速读内容及图像、回收站。关闭并重启，确认结果仍在。
6. 模型端点和密钥在桌面设置中重新填写/验证。旧网页 localStorage 属于原浏览器 origin，桌面不能自动读取。已在桌面保存过的设置不受书库复制影响；不要手工复制带 credentialRef 的 settings.json 来迁移密钥。

## 回退

完整退出应用，将新 `library/` 改名保留，再把 `library.before-migration` 改回 `library/`。源书库从未移动，可继续用旧入口启动。回退前后不要同时运行两个进程修改同一书库。

迁移脚本先复制到目标父目录下的临时目录，复制成功后再发布到目标路径。磁盘不足或复制失败不会留下半个目标书库；源文件不改变。迁移不是在线合并工具，目标父目录和书库必须在迁移期间保持离线。
