import { it, expect, vi, afterEach } from "vitest";
import { connectOverlay } from "./client";
class Socket {
  static all: Socket[] = [];
  onopen: any;
  onmessage: any;
  onclose: any;
  onerror: any;
  readyState = 1;
  sent: string[] = [];
  constructor(public url: string) {
    Socket.all.push(this);
  }
  send(s: string) {
    this.sent.push(s);
  }
  close(code = 1006) {
    this.onclose?.({ code });
  }
}
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  Socket.all = [];
});
it("authenticates in a message and reconnects with a fresh snapshot, stopping on revoked credentials", () => {
  vi.useFakeTimers();
  vi.stubGlobal("WebSocket", Socket);
  const snapshot = vi.fn(),
    status = vi.fn();
  const stop = connectOverlay("test-secret", snapshot, status);
  let ws = Socket.all[0];
  ws.onopen();
  expect(ws.url).not.toContain("test-secret");
  expect(JSON.parse(ws.sent[0])).toEqual({
    type: "auth",
    token: "test-secret",
  });
  ws.onmessage({
    data: JSON.stringify({
      schema_version: 1,
      sequence: 10,
      commands: [],
      presentation: {},
      paused: false,
    }),
  });
  expect(status).toHaveBeenLastCalledWith("connected");
  ws.close();
  expect(status).toHaveBeenLastCalledWith("disconnected");
  vi.advanceTimersByTime(1000);
  ws = Socket.all[1];
  ws.onopen();
  ws.onmessage({
    data: JSON.stringify({
      schema_version: 1,
      sequence: 1,
      commands: [],
      presentation: {},
      paused: true,
    }),
  });
  expect(snapshot).toHaveBeenCalledTimes(2);
  ws.close(1008);
  expect(status).toHaveBeenLastCalledWith("invalid");
  vi.advanceTimersByTime(60000);
  expect(Socket.all).toHaveLength(2);
  stop();
});
