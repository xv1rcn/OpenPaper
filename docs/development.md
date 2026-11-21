# 开发与验证

## 当前状态

目前已实现 Vue 书库/阅读页面与系统凭据库。Tauri、桌面令牌和安装包尚未实现。不要将本地开发 HTTP 服务暴露到外网。

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
- 原管理和速读接口保留；模型请求使用 apiConfig: {useSaved: true}，由后端读取凭据。
- 旧页面链接跳转 Vue；仅提供明确允许的编译页面、assets、论文 PDF、元数据和速读图像/JSON。源码、虚拟环境、备份、日志及回收站不通过静态路径公开；原 `/api/log` 仍是开发接口。

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

## Vue 论文库

需要 Node.js 24（CI 使用此版本）。首次运行：

```sh
cd frontend
npm ci
npm run build
```

然后启动 Python 服务，访问 `http://127.0.0.1:8001/app/`。构建产物不提交 Git；首次 clone 或修改前端后需重新 build。
开发热更新：`npm run dev`，访问 `http://127.0.0.1:5173/app/`，同时保留后端 8001 服务。
开发代理仅绑定本机；API 的 Host/Origin 由开发代理改写为后端地址，不是生产 Tauri 通信策略。

```sh
npm test
npx playwright install chromium
npm run test:e2e
```

端到端测试从 `frontend/e2e/server.py` 启动隔离服务，使用 8765 端口和临时论文库；默认 Python 为 `../.venv/bin/python`，可通过 `OPENPAPER_TEST_PYTHON` 覆盖。不复用用户 8001 服务。
截图保存在忽略的 `frontend/test-results/`。测试入口不属于生产静态文件白名单。

## Vue 设置与导入

新书库侧栏“设置”直接调用既有 `/api/settings`，无需转到旧首页。只有点击“测试接口”才调用模型；选择/保存配置不会进行付费模型调用。
旧浏览器配置导入必须在原来的 origin 中操作；开发预览 5173 与实际应用 8001 的浏览器存储互相隔离。

`POST /api/import-pdf` 使用原始 PDF 请求体，要求 `Content-Type: application/pdf`、`X-OpenPaper-Request: 1`，以及经过百分号编码的 `X-File-Name`。上限 50 MB；当前不接受加密 PDF。
成功返回 `{ok, file_key, duplicate, indexed, warning?}`。`indexed: false` 表示文件已经保存、索引失败，不应当作“未保存”或删除源文件；同名同内容重试可修复索引。

论文导入与 HTTP 书库修改和文件监控扫描共用进程内锁。不要运行多个后端/CLI 同时修改同一论文库；锁不是跨进程安全机制。
浏览器自动化测试的配置凭据使用内存替身；服务商连接测试通过可控响应验证请求协议，不验证真实服务商可用性。

## 外观与统一入口

`/` 自动跳转 `/app/`；旧阅读链接保留 `file_key`，旧统计链接打开 Vue 统计视图。没有构建产物时返回 503。旧模板仅保留源码参考。

设置中的“外观”通过 `/api/preferences` 保存到配置目录的 `preferences.json`，与密钥存储分离；使用修订号避免旧页面覆盖新配置。主题在重开页面时应用。浏览器分组顺序、卡片/列表、阅读布局仍保存在 localStorage。

速读使用已有 Python 缓存与生成流程；原文已使用本地打包的 PDF.js，支持文本选择、搜索、缩放与页码恢复；Tauri/WebView 实机验证仍待后续完成。

## PDF.js 阅读组件

`PdfReader.vue` 按需加载 PDF.js 6.5.438 的 viewer、worker 与样式，支持连续滚动、文本选择、搜索高亮、前后匹配、翻页、适合宽度/整页和固定缩放。页码沿用原文档的本地布局记录，缩放独立记录；当前恢复粒度是页码，不保存页内像素偏移。关闭原文面板会销毁文档任务。

Vite 将 cmaps、standard_fonts、wasm 和许可证复制到 dist/pdfjs，开发服务提供对应资源；后端仅允许指定目录及扩展，继续拒绝源码和 source map。Worker 随构建输出到 assets，不需要在线 CDN。完整阅读器按需加载，当前约 617 kB JS、1.27 MB worker（未压缩传输大小），仍会产生 Vite 大块提示。

扫描 PDF 无文本层时不提供 OCR。密码文件给出提示；当前不包含书签管理、手写批注或表单编辑流程。引用回跳只定位页码。

参考：https://mozilla.github.io/pdf.js/examples/
