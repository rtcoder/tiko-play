use std::process::{Child, Command};
use std::sync::Mutex;
use tauri::State;

struct ListenerState {
    process: Mutex<Option<Child>>,
}

#[tauri::command]
fn start_listener(state: State<ListenerState>) -> Result<(), String> {
    let mut guard = state.process.lock().unwrap();
    if guard.is_some() {
        return Err("Listener already running".into());
    }

    let child = Command::new("python")
        .arg("python/listener.py")
        .arg("config.json")
        .spawn()
        .map_err(|e| e.to_string())?;

    *guard = Some(child);
    Ok(())
}

#[tauri::command]
fn stop_listener(state: State<ListenerState>) -> Result<(), String> {
    let mut guard = state.process.lock().unwrap();

    if let Some(mut child) = guard.take() {
        child.kill().map_err(|e| e.to_string())?;
    }

    Ok(())
}

fn main() {
    tauri::Builder::default()
        .manage(ListenerState {
            process: Mutex::new(None),
        })
        .invoke_handler(tauri::generate_handler![
            start_listener,
            stop_listener
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
