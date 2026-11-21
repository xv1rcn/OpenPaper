# OpenPaper 桌面开发宿主

这是开发启动链路，不是可分发安装包。需要仓库 `.venv`、已安装的 Python 依赖、Rust 和已构建的 `frontend/dist`。

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

- Python sidecar 冻结与随安装包分发、签名、公证、跨平台实机测试。
- 启动错误的原生可视提示、子进程运行中崩溃后的恢复界面。
- 动态端口使浏览器 localStorage 按不同 origin 隔离；页码/视图偏好需迁入后端后才能保证桌面跨次启动恢复。服务端外观、模型配置与论文数据已独立持久化。
- 原生窗口关闭时的未保存草稿确认尚需 WebView 实机验收。
- 外链打开、文件下载的 WebView 原生体验仍待验收。

安全边界是本地单用户，不承诺抵御已控制同一用户账户的恶意进程。普通浏览器开发服务继续兼容原启动方式，只有 `--desktop` 强制桌面会话。
