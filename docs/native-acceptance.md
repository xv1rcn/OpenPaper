# 原生生命周期验收

状态：待执行。2026-11-26 的应用控制连接超时；备用 System Events 返回 -10827，执行环境不允许查询进程。以下为测试步骤，不是通过记录。

## 准备

使用本地应用包 `desktop/target/release/bundle/macos/OpenPaper.app`，或代码提交 `7d21b1f` 对应的 CI 测试包。先保存个人应用中的修改并正常退出 OpenPaper，防止单实例机制将测试启动转交给个人实例。不要终止不明归属的后端进程。

在普通 macOS 终端、仓库根目录执行：

```sh
acceptance_root=$(mktemp -d /tmp/openpaper-native-XXXXXX)
app_executable="$PWD/desktop/target/release/bundle/macos/OpenPaper.app/Contents/MacOS/openpaper-desktop"
printf '%s\n' "$acceptance_root"
```

所有测试只使用此临时目录。不要复制个人 config/settings.json，不需要填写 API Key 或调用模型。保留测试目录和日志到复核结束。

## A. 启动失败与恢复

```sh
printf 'blocked path\n' > "$acceptance_root/blocked"
OPENPAPER_DATA_DIR="$acceptance_root/blocked" "$app_executable" \
  > "$acceptance_root/startup.log" 2>&1 &
```

观察窗口是否由启动状态进入“无法连接本地服务”，且有“重启应用”入口。将阻塞文件改名，创建同名数据目录，再点击窗口内的重启：

```sh
mv "$acceptance_root/blocked" "$acceptance_root/blocked.fixture"
mkdir "$acceptance_root/blocked"
```

通过条件：失败时窗口可见且未直接消失；点击重启后进入空书库；数据仅写入临时目录。重启的进程 PID 可能变化，后续测试重新启动，不能沿用旧 PID。

正常退出测试应用后执行 B。

## B. 运行中后端退出及草稿保护

```sh
OPENPAPER_DATA_DIR="$acceptance_root/data" "$app_executable" \
  > "$acceptance_root/runtime.log" 2>&1 &
acceptance_host_pid=$!
printf 'test host PID: %s\n' "$acceptance_host_pid"
```

打开设置，在模型名称中填入 `native-unsaved-check`，不要保存。确认当前是测试空书库。仅查询上述测试宿主的直接子进程：

```sh
pgrep -P "$acceptance_host_pid" -fl openpaper-backend
```

确认输出唯一且为测试宿主的 openpaper-backend 后，使用输出中的准确 PID 终止该测试子进程。不要按名称批量终止进程。若无法确认归属，停止此步骤。

观察服务停止提示是否出现在设置对话框内，输入是否仍为 `native-unsaved-check`。点击重启，先取消，确认草稿和当前对话框保持不变；再次重启并确认，验证进入可用书库，放弃的草稿没有被保存。

补充：在论文编辑对话框内对临时论文修改标题，重复同样检查。重启后应显示最后一次已保存的标题，而不是丢弃的草稿。

## C. 正常关闭及退出确认

分别测试窗口关闭按钮与 ⌘Q：

1. 无草稿时正常退出，确认测试后端也结束。
2. 设置中修改模型名称但不保存，退出时取消，内容保留。
3. 再次退出并确认，宿主和后端结束；重新启动验证草稿未保存。
4. 外观选项和论文编辑草稿分别重复。
5. 重复按退出快捷键，不应叠加多个确认框。
6. 正常保存后立即退出并重启，已保存数据恢复；日志不出现配置锁冲突。

## D. 原生阅读与下载

只导入测试 PDF。检查多页翻页、搜索、缩放、原文引用回跳、关闭重开后非第一页恢复，以及文件定位。已有合成速读缓存可用于导出；不需要重新生成或使用真实密钥。导出失败时区分应用问题和缺少系统 Chrome/Edge/Chromium。

## 记录格式

| 项目 | 操作与预期 | 实际结果 | 证据 | 状态 |
| --- | --- | --- | --- | --- |
| A | 启动失败可见，修复路径后重启成功 | 待执行 | — | 待测 |
| B | 后端退出不丢草稿，重启有确认 | 待执行 | — | 待测 |
| C | 关闭与 ⌘Q 的取消/确认均正确 | 待执行 | — | 待测 |
| D | 原生阅读、下载及状态恢复 | 待执行 | — | 待测 |

证据应记录应用提交、系统版本、窗口操作结果与必要日志；不要记录密钥、会话 Cookie 或 token。浏览器模拟协议测试、后端 API 测试和进程存活均不能单独证明原生交互通过。

Windows/Linux 使用相同验收任务，但必须在对应桌面会话执行。另行检查系统凭据库、WebView2/Secret Service 可用性、文件下载和文件管理器行为；在独立测试配置中填写合成凭据并清理，不能用内存替身声称系统凭据库已通过。
