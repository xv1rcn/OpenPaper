use std::{
    io::{BufRead, BufReader},
    path::PathBuf,
    process::{Child, Command, Stdio},
    sync::{mpsc, Mutex},
    time::{Duration, Instant},
};
use tauri::{Manager, WebviewUrl, WebviewWindowBuilder};
struct Backend(Mutex<Option<Child>>);
impl Drop for Backend {
    fn drop(&mut self) {
        if let Ok(slot) = self.0.get_mut() {
            if let Some(mut child) = slot.take() {
                drop(child.stdin.take());
                let deadline = Instant::now() + Duration::from_secs(5);
                loop {
                    if child.try_wait().ok().flatten().is_some() {
                        break;
                    }
                    if Instant::now() > deadline {
                        let _ = child.kill();
                        let _ = child.wait();
                        break;
                    }
                    std::thread::sleep(Duration::from_millis(50));
                }
            }
        }
    }
}
fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _, _| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.set_focus();
            }
        }))
        .setup(|app| {
            let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
                .parent()
                .unwrap()
                .to_path_buf();
            let python = std::env::var_os("OPENPAPER_PYTHON")
                .map(PathBuf::from)
                .unwrap_or(root.join(if cfg!(windows) {
                    ".venv/Scripts/python.exe"
                } else {
                    ".venv/bin/python"
                }));
            let data = std::env::var_os("OPENPAPER_DATA_DIR")
                .map(PathBuf::from)
                .unwrap_or(app.path().app_data_dir()?);
            std::fs::create_dir_all(&data)?;
            let token = uuid::Uuid::new_v4().simple().to_string();
            let mut child = Command::new(python)
                .args([
                    "-m",
                    "backend",
                    "--port",
                    "0",
                    "--ready-json",
                    "--desktop",
                    "--library-root",
                ])
                .arg(data.join("library"))
                .arg("--config-root")
                .arg(data.join("config"))
                .arg("--resource-root")
                .arg(&root)
                .env("OPENPAPER_DESKTOP_TOKEN", &token)
                .current_dir(&root)
                .stdin(Stdio::piped())
                .stdout(Stdio::piped())
                .stderr(Stdio::inherit())
                .spawn()?;
            let stdout = child.stdout.take().unwrap();
            let guard = Backend(Mutex::new(Some(child)));
            let (tx, rx) = mpsc::channel();
            std::thread::spawn(move || {
                for line in BufReader::new(stdout).lines().map_while(Result::ok) {
                    if let Ok(value) = serde_json::from_str::<serde_json::Value>(&line) {
                        if value["event"] == "ready" {
                            let _ = tx.send(value["port"].as_u64());
                        }
                    }
                }
            });
            let port = rx
                .recv_timeout(Duration::from_secs(60))?
                .ok_or("Invalid backend readiness")?;
            if !(1..=65535).contains(&port) {
                return Err("Invalid backend port".into());
            }
            let origin = format!("http://127.0.0.1:{port}");
            let url = format!("{origin}/desktop/session?token={token}").parse()?;
            WebviewWindowBuilder::new(app, "main", WebviewUrl::External(url))
                .title("OpenPaper")
                .inner_size(1024.0, 768.0)
                .center()
                .on_navigation(move |url| {
                    url.scheme() == "http"
                        && url.host_str() == Some("127.0.0.1")
                        && url.port() == Some(port as u16)
                })
                .build()?;
            println!("OpenPaper desktop ready on port {port}");
            app.manage(guard);
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("Cannot start OpenPaper")
        .run(|app, event| {
            if matches!(event, tauri::RunEvent::Exit) {
                if let Some(backend) = app.try_state::<Backend>() {
                    if let Ok(mut child) = backend.0.lock() {
                        if let Some(child) = child.as_mut() {
                            drop(child.stdin.take());
                        }
                    }
                }
            }
        });
}
