import type { AppEvent, Snapshot } from "./types";
export function subscribeEvents(
  onSnapshot: (s: Snapshot) => void,
  onEvent: (e: AppEvent) => void,
  onConnection: (connected: boolean) => void,
) {
  let closed = false;
  let socket: WebSocket;
  let timer: ReturnType<typeof setTimeout>;
  let attempt = 0;
  let last = 0;
  let instance = "";
  function connect() {
    if (closed) return;
    socket = new WebSocket(
      `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/api/events`,
    );
    socket.onmessage = ({ data }) => {
      let event: Snapshot | AppEvent;
      try {
        event = JSON.parse(data);
      } catch {
        return;
      }
      if (event.type === "snapshot") {
        const snap = event as Snapshot;
        instance = snap.instance_id;
        last = snap.watermark;
        attempt = 0;
        onConnection(true);
        onSnapshot(snap);
      } else {
        const e = event as AppEvent;
        if (e.instance_id === instance && e.id > last) {
          last = e.id;
          onEvent(e);
        }
      }
    };
    socket.onerror = () => socket.close();
    socket.onclose = () => {
      if (closed) return;
      onConnection(false);
      timer = setTimeout(
        connect,
        [1000, 2000, 5000, 10000][Math.min(attempt++, 3)],
      );
    };
  }
  connect();
  return () => {
    closed = true;
    clearTimeout(timer);
    socket?.close();
  };
}
