# OpenPaper 桌面开发宿主

开发模式需要仓库 `.venv`、已安装的 Python 依赖、Rust 和已构建的 `frontend/dist`。本地打包模式见下文；当前构建产物尚未签名、公证。

```sh
cd frontend
npm ci
npm run build
cd ../desktop
cargo run
```

可用 `OPENPAPER_PYTHON` 指定 Python，`OPENPAPER_DATA_DIR` 指定测试数据目录。默认使用 Tauri 应用数据目录，内部为 `library/`、`config/`。不会自动复制浏览器版本的论文和凭据。

宿主等待 Python 动态端口就绪，然后加载同源 WebView。会话 token 通过子进程环境传入，后端启动后从环境移除；一次启动入口将其换为 HttpOnly、SameSite=Strict Cookie。静态资源和全部 API 均要求该会话。WebView 不授予远程页面 Tauri IPC 权限，顶层导航限制在当前服务地址。单实例插件用于激活已有窗口。

关闭宿主时关闭子进程 stdin；Python 检测 EOF 后停止监控和 HTTP 服务。宿主清理等待最多 5 秒，然后强制回收子进程。异常终止宿主同样会关闭管道。

## 尚未完成

- 发行签名、公证、Windows / Linux 安装包及跨平台实机验收。
- 启动错误的原生可视提示、子进程运行中崩溃后的恢复界面。
- 阅读页码、缩放、对照布局及书库视图/分组顺序已迁入 config/view-state.json，不再依赖动态端口的 localStorage。旧状态仅在原 origin 可访问且后端对应项不存在时迁入；其他旧端口的浏览器存储无法自动读取。
- 原生窗口关闭时的未保存草稿确认尚需 WebView 实机验收。
- 外链打开、文件下载的 WebView 原生体验仍待验收。

安全边界是本地单用户，不承诺抵御已控制同一用户账户的恶意进程。普通浏览器开发服务继续兼容原启动方式，只有 `--desktop` 强制桌面会话。

## Windows / Linux 开发与验证

三平台均需 Python 虚拟环境、Node.js 和 Rust。系统编译依赖见 [Tauri 官方前置条件](https://v2.tauri.app/start/prerequisites/)。Windows 使用 MSVC 工具链和 WebView2；Linux 需要 WebKitGTK 4.1 等系统库。Linux 密钥保存还需可用且已解锁的 Secret Service；缺失时明确报错，不降级到明文文件。

在仓库根目录创建虚拟环境并安装依赖：

```powershell
# Windows PowerShell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

```sh
# macOS / Linux
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

随后执行本文开头的前端构建和 `cargo run`。Windows 辅助进程使用 CREATE_NO_WINDOW；三平台辅助进程均启用 Python UTF-8 模式。启动/退出回归覆盖中文和空格数据目录、动态端口就绪和父进程管道关闭清理。

CI 桌面任务在 Windows、macOS、Ubuntu 24.04 上执行 `cargo build --locked`，检查编译及链接；后端任务在三平台运行 Python 3.10 / 3.12 测试。POSIX SIGTERM 测试只在 Unix 运行，Windows 的正常退出由父进程管道测试覆盖。符号链接安全测试需要 Windows 运行账户拥有创建符号链接的权限（开发者模式或相应权限）；不会为了通过测试跳过安全断言。

这些检查不替代原生窗口实机验收，也不产生可分发安装包。下一阶段依次完成：Python 冻结与资源打包、脱离源码目录启动、安装卸载验证、凭据库与导入导出及窗口交互验收。

## 内置 Python 的应用包

使用 PyInstaller onedir 打包当前系统/架构的 Python、依赖及 `frontend/dist`，再作为 Tauri 资源放入 `backend/`。包内后端自行定位只读资源，用户数据仍写入应用数据目录。发布构建缺失后端时直接报错，绝不回退到源码或系统 Python；`cargo run` 开发构建仍支持 venv。每个目标系统/架构必须分别构建。

先构建前端，然后在仓库根目录执行（Windows 用 `.venv\Scripts\python.exe` 替换 Python 路径）：

```sh
.venv/bin/python -m pip install -r scripts/packaging/requirements.txt
.venv/bin/python scripts/packaging/build_backend.py
.venv/bin/python scripts/packaging/smoke_backend.py desktop/packaged/openpaper-backend
cd desktop
cargo tauri build --config tauri.bundle.conf.json --bundles app
```

最后一条适用于 macOS，需事先安装 Tauri CLI 2（`cargo install tauri-cli --version 2.11.4 --locked`）。输出为 `desktop/target/release/bundle/macos/OpenPaper.app`，可搬移后启动，无需用户安装 Python、Node.js、Rust 或保留源码。Windows / Linux 的冻结后端由 CI 测试；安装包输出尚待验收，不视为已发布支持。

应用包不包含用户论文、密钥或配置，也不包含 Chromium。当前 PDF 导出仍依赖系统安装的 Chrome / Edge / Chromium；PDF 阅读本身使用包内 PDF.js。macOS 本地构建未做 Developer ID 签名和公证，不是面向他人的正式发行包。

打包冒烟测试将整个后端移至中文/空格目录，从源码目录之外启动，验证依赖加载、会话鉴权、前端入口及入口引用资源、书库 API 和管道关闭退出。它不调用模型、不写入系统凭据库，也不替代交互与安装卸载测试。

受限环境无法使用系统文件事件时，可设置 `OPENPAPER_POLLING_WATCHER=1` 改用轮询监控；默认仍使用原生监控。轮询会增加目录扫描开销。

原生验收：已通过原生应用控制观察到 release OpenPaper.app 的书库窗口正常加载。此前启动测试可能被手动关闭，原因未确认；不作为启动故障结论。完整导入/阅读/退出交互与真实凭据库读写仍待验收。
