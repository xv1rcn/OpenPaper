# 开发与验证

## 当前状态

M1 是 Python 运行基础改造，旧前端仍可使用。Vue/Tauri、系统凭据库、桌面令牌和安装包尚未实现。不要将本地开发 HTTP 服务暴露到外网。

## 本地环境

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
```

测试需要允许监听本机临时端口。测试使用临时目录，不修改真实论文和模型配置，不调用付费模型。最终结果记录在迭代计划中。

## 兼容启动

```sh
.venv/bin/python -m backend --port 8001
```

未传 `--library-root` 时使用现有仓库论文库，保持既有浏览器 origin 和 localStorage 配置的兼容性。显式指定已占用端口会报错退出，不终止其他程序。

## 独立论文库

以下路径仅为示例；目录应可写，根目录中存放 `papers/`，不是直接传入 `papers/` 子目录。

```sh
.venv/bin/python -m backend --library-root /path/to/my-library --port 0 --ready-json
```

资源默认从仓库加载，也可用 `--resource-root` 指向只读资源目录。端口 0 由系统选择空闲端口，标准输出包含：

```json
{"event":"ready","api_version":1,"host":"127.0.0.1","port":12345}
```

该事件表示 bootstrap、论文扫描、HTTP 服务和目录监控均已启动。stdout 也有普通日志，未来桌面宿主按 JSON 行的 event 字段识别就绪事件。这里不输出长期凭据；临时会话认证在 M4 实施。

服务收到 SIGINT/SIGTERM 后停止监控、取消待执行扫描并释放监听端口。正在执行的业务请求尚无统一取消协议，任务退出策略列入后续里程碑。

## HTTP 接口增量

- `GET /api/ping`：兼容旧 service 字段，新增 `api_version: 1`。
- `GET /api/library`：返回 `{ok: true, papers: [...]}`，为后续 Vue 客户端提供数据入口。
- 原管理和速读接口保留；此阶段仍使用旧 apiConfig 请求格式。
- 仅提供明确允许的旧页面、assets、论文 PDF、元数据和速读图像/JSON。源码、虚拟环境、备份、日志及回收站不通过静态路径公开；原 `/api/log` 仍是开发接口。

`build.py` 仅是旧页面模板构建兼容入口。运行服务、文件监控与恢复论文不再执行这个脚本；新前端构建将由 Vite 独立负责。

## 数据迁移

显式 bootstrap 才会检查旧布局。旧速读目录采用复制且不覆盖现有结果；保留原件，并写迁移标记避免下次启动重新导入已删除的结果。内嵌速读成功保存后才移除 metadata 内旧字段，修改前保留备份。

浏览器 API Key 本轮不读取、不复制、不迁移。生产级配置和凭据迁移安排在 M2。

## 配置服务开发

`--config-root /path/to/private-config` 可隔离配置，默认路径为 macOS 的
`~/Library/Application Support/OpenPaper`、Windows 的 `%APPDATA%/OpenPaper`、
Linux 的 `$XDG_CONFIG_HOME/openpaper`（默认 `~/.config/openpaper`）。不要将该目录放在论文库或静态资源目录中。

GET `/api/settings` 返回 `provider`、`revision`、`hasCredential`。
POST 同一路径提交 `{provider, revision, apiKey?}`，设置 `Content-Type: application/json`
和 `X-OpenPaper-Request: 1`。`provider` 是完整普通配置，包含 `apiBaseUrl`、`model`、
`timeoutSec`、`contextWindow`、`maxOutputTokens`；省略 `apiKey` 表示保留已保存密钥。
`hasCredential` 仅表示保存了引用，读取此接口不会触发钥匙串访问，也不保证钥匙串当前解锁或条目仍存在。

仅一个后端进程可拥有某个配置目录。不要把 `SettingsStore.resolve()` 的返回值发送给浏览器或写入日志。
首页与独立阅读页已接入此服务。刷新页面后，在“设置 → 速读”显式导入旧浏览器配置；未点击导入前旧密钥仍在浏览器。
生成、连接测试与模型列表请求仅接收 `apiConfig: {useSaved: true}`，并要求与设置写入相同的自定义请求头。
清空配置发送 `{revision, reset: true}`；预算字段允许 0 表示自动配置。
运行前端检查：`node --test tests/settings-client.test.cjs`。
