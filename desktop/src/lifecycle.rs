use std::sync::atomic::{AtomicBool, AtomicU16, Ordering};
use tauri::{AppHandle, Manager};

#[derive(Default)]
pub struct Lifecycle {
    pub port: AtomicU16,
    pub ui_ready: AtomicBool,
    pub failed: AtomicBool,
    pub approved_exit: AtomicBool,
}

pub fn status_url(failed: bool) -> tauri::Url {
    let (title, message, action) = if failed {
        (
            "无法连接本地服务",
            "请重启应用后重试。已保存的论文和配置会保留。",
            "<a href='https://openpaper.invalid/restart'>重启应用</a>",
        )
    } else {
        ("正在打开 OpenPaper", "正在启动本地服务…", "")
    };
    let html = format!("<!doctype html><html lang='zh-CN'><meta charset='utf-8'><meta name='viewport' content='width=device-width'><title>OpenPaper</title><style>html{{color-scheme:light dark}}body{{font:16px/1.7 system-ui;margin:15vh auto;padding:24px;max-width:520px}}h1{{font-size:22px}}a{{color:inherit}}</style><h1>{title}</h1><p>{message}</p>{action}</html>");
    let encoded: String = html.bytes().map(|b| format!("%{b:02X}")).collect();
    format!("data:text/html;charset=utf-8,{encoded}")
        .parse()
        .unwrap()
}

fn is_service_url(url: &tauri::Url, port: u16) -> bool {
    port != 0
        && url.scheme() == "http"
        && url.host_str() == Some("127.0.0.1")
        && url.port() == Some(port)
        && url.username().is_empty()
        && url.password().is_none()
}

pub fn allow_navigation(app: &AppHandle, url: &tauri::Url) -> bool {
    let state = app.state::<Lifecycle>();
    if url == &status_url(false) || url == &status_url(true) {
        return true;
    }
    if state.failed.load(Ordering::SeqCst) && url.as_str() == "https://openpaper.invalid/restart" {
        state.approved_exit.store(true, Ordering::SeqCst);
        app.request_restart();
        return false;
    }
    let port = state.port.load(Ordering::SeqCst);
    if !is_service_url(url, port) {
        return false;
    }
    match url.path() {
        "/desktop/ui-ready" => {
            state.ui_ready.store(true, Ordering::SeqCst);
            false
        }
        "/desktop/close-approved" => {
            state.approved_exit.store(true, Ordering::SeqCst);
            app.exit(0);
            false
        }
        "/desktop/restart-approved" => {
            state.approved_exit.store(true, Ordering::SeqCst);
            app.request_restart();
            false
        }
        _ => {
            state.ui_ready.store(false, Ordering::SeqCst);
            true
        }
    }
}

pub fn request_close(app: &AppHandle) -> bool {
    let state = app.state::<Lifecycle>();
    if state.approved_exit.load(Ordering::SeqCst) || !state.ui_ready.load(Ordering::SeqCst) {
        return false;
    }
    if let Some(window) = app.get_webview_window("main") {
        // Vue handles confirmation without giving the remote page general Tauri IPC.
        if window
            .eval("window.dispatchEvent(new Event('openpaper-close-request'))")
            .is_ok()
        {
            return true;
        }
    }
    false
}

pub fn backend_failed(app: &AppHandle) {
    let state = app.state::<Lifecycle>();
    state.failed.store(true, Ordering::SeqCst);
    if let Some(window) = app.get_webview_window("main") {
        if state.ui_ready.load(Ordering::SeqCst) {
            // Preserve drafts in the current page. Restart is an explicit action.
            let _ = window.eval("window.dispatchEvent(new Event('openpaper-backend-stopped'))");
        } else {
            let _ = window.navigate(status_url(true));
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn lifecycle_actions_are_restricted_to_current_service_origin() {
        assert!(is_service_url(
            &"http://127.0.0.1:54321/desktop/close-approved"
                .parse()
                .unwrap(),
            54321
        ));
        for candidate in [
            "http://127.0.0.1:54322/desktop/close-approved",
            "https://127.0.0.1:54321/",
            "http://localhost:54321/",
            "http://example.com:54321/",
            "http://user@127.0.0.1:54321/",
            "data:text/html,hello",
        ] {
            assert!(!is_service_url(&candidate.parse().unwrap(), 54321));
        }
        assert!(!is_service_url(
            &"http://127.0.0.1:54321/".parse().unwrap(),
            0
        ));
    }
}
