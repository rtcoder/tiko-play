import { invoke } from "@tauri-apps/api/tauri";

let listening = false;

const btn = document.getElementById("listenBtn");

btn.addEventListener("click", async () => {
    try {
        if (!listening) {
            await invoke("start_listener");
            btn.innerText = "⏹ Stop";
            listening = true;
        } else {
            await invoke("stop_listener");
            btn.innerText = "🎧 Nasłuchuj";
            listening = false;
        }
    } catch (e) {
        alert(e);
    }
});
