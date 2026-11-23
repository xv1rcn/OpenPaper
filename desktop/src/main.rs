#![cfg_attr(all(windows, not(debug_assertions)), windows_subsystem = "windows")]

use std::{
    io::{BufRead, BufReader},
    path::PathBuf,
    process::{Child, Command, Stdio},
    sync::{mpsc, Mutex},
    time::{Duration, Instant},
};
use tauri::{Manager, WebviewUrl, WebviewWindowBuilder};
mod lifecycle;
use lifecycle::Lifecycle;
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

fn launch_backend(
    app: &tauri::AppHandle,
) -> Result<(Backend, u16, String), Box<dyn std::error::Error>> {
    let resources = app.path().resource_dir()?;
    let executable = resources.join("backend").join(if cfg!(windows) {
        "openpaper-backend.exe"
    } else {
        "openpaper-backend"
    });
    let mut command;
    if executable.is_file() {
        command = Command::new(executable);
    } else if cfg!(debug_assertions) {
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
        command = Command::new(python);
        command
            .args(["-m", "backend", "--resource-root"])
            .arg(&root)
            .current_dir(root);
    } else {
        return Err(format!("Bundled backend missing: {}", executable.display()).into());
    }
    let data = std::env::var_os("OPENPAPER_DATA_DIR")
        .map(PathBuf::from)
        .unwrap_or(app.path().app_data_dir()?);
    std::fs::create_dir_all(&data)?;
    let token = uuid::Uuid::new_v4().simple().to_string();
    // Keep the Python helper from opening a console window on Windows.
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000); // CREATE_NO_WINDOW
    }
    let mut child = command
        .args(["--port", "0", "--ready-json", "--desktop", "--library-root"])
        .arg(data.join("library"))
        .arg("--config-root")
        .arg(data.join("config"))
        .env("OPENPAPER_DESKTOP_TOKEN", &token)
        .env("PYTHONUTF8", "1")
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
    Ok((guard, port as u16, token))
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _, _| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.set_focus();
            }
        }))
        .manage(Lifecycle::default())
        .manage(Backend(Mutex::new(None)))
        .setup(|app| {
            let handle = app.handle().clone();
            let navigation_handle = handle.clone();
            WebviewWindowBuilder::new(
                app,
                "main",
                WebviewUrl::External(lifecycle::status_url(false)),
            )
            .title("OpenPaper")
            .inner_size(1024.0, 768.0)
            .center()
            .initialization_script("window.__OPENPAPER_DESKTOP__ = true;")
            .on_navigation(move |url| lifecycle::allow_navigation(&navigation_handle, url))
            .build()?;
            std::thread::spawn(move || match launch_backend(&handle) {
                Ok((guard, port, token)) => {
                    let Some(window) = handle.get_webview_window("main") else {
                        return;
                    };
                    handle
                        .state::<Lifecycle>()
                        .port
                        .store(port, std::sync::atomic::Ordering::SeqCst);
                    *handle.state::<Backend>().0.lock().unwrap() = guard.0.lock().unwrap().take();
                    let url = format!("http://127.0.0.1:{port}/desktop/session?token={token}")
                        .parse()
                        .unwrap();
                    if window.navigate(url).is_err() {
                        lifecycle::backend_failed(&handle);
                        return;
                    }
                    loop {
                        std::thread::sleep(Duration::from_secs(1));
                        let stopped = {
                            let backend = handle.state::<Backend>();
                            let mut slot = backend.0.lock().unwrap();
                            match slot.as_mut() {
                                Some(child) => !matches!(child.try_wait(), Ok(None)),
                                None => return,
                            }
                        };
                        if stopped {
                            lifecycle::backend_failed(&handle);
                            break;
                        }
                    }
                }
                Err(error) => {
                    eprintln!("OpenPaper backend startup failed: {error}");
                    lifecycle::backend_failed(&handle);
                }
            });
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                if lifecycle::request_close(window.app_handle()) {
                    api.prevent_close();
                }
            }
        })
        .build(tauri::generate_context!())
        .expect("Cannot start OpenPaper")
        .run(|app, event| {
            if let tauri::RunEvent::ExitRequested { api, .. } = &event {
                if lifecycle::request_close(app) {
                    api.prevent_exit();
                }
            }
            if matches!(event, tauri::RunEvent::Exit) {
                if let Some(backend) = app.try_state::<Backend>() {
                    let child = backend.0.lock().ok().and_then(|mut slot| slot.take());
                    // Finish graceful shutdown before restart can claim the config lock.
                    drop(Backend(Mutex::new(child)));
                }
            }
        });
}
