import type { OverlaySnapshot, OverlayConnection } from "./types";
export function connectOverlay(
  token: string,
  onSnapshot: (s: OverlaySnapshot) => void,
  onStatus: (s: OverlayConnection) => void,
) {
  let stopped = false;
  let socket: WebSocket | null = null;
  let retry: ReturnType<typeof setTimeout> | undefined;
  let heartbeat: ReturnType<typeof setInterval> | undefined;
  const connect = () => {
    if (stopped) return;
    onStatus("connecting");
    const url = new URL("/overlay/events", location.href);
    url.protocol = location.protocol === "https:" ? "wss:" : "ws:";
    const current = new WebSocket(url.toString());
    socket = current;
    current.onopen = () => {
      if (stopped || socket !== current) return;
      current.send(JSON.stringify({ type: "auth", token }));
      heartbeat = setInterval(() => {
        if (current.readyState === 1)
          current.send(JSON.stringify({ type: "ping" }));
      }, 15000);
    };
    current.onmessage = (event) => {
      if (stopped || socket !== current) return;
      try {
        const value = JSON.parse(event.data);
        if (
          value.schema_version !== 1 ||
          !Array.isArray(value.commands) ||
          !value.presentation ||
          typeof value.paused !== "boolean"
        )
          throw Error();
        onSnapshot(value);
        onStatus("connected");
      } catch {
        current.close(1008);
      }
    };
    current.onclose = (event) => {
      if (stopped || socket !== current) return;
      clearInterval(heartbeat);
      if (event.code === 1008) {
        onStatus("invalid");
        return;
      }
      onStatus("disconnected");
      retry = setTimeout(connect, 1000);
    };
    current.onerror = () => current.close();
  };
  if (token) connect();
  else onStatus("invalid");
  return () => {
    stopped = true;
    clearInterval(heartbeat);
    clearTimeout(retry);
    socket?.close();
  };
}
