import { it, expect, vi, afterEach } from "vitest";
import { subscribeEvents } from "./events";
class Socket {
  static all: Socket[] = [];
  onmessage: any;
  onclose: any;
  onerror: any;
  constructor(public url: string) {
    Socket.all.push(this);
  }
  close() {
    this.onclose?.();
  }
}
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  Socket.all = [];
});
it("reconnects without starting listener and resets dedupe from snapshot", () => {
  vi.useFakeTimers();
  vi.stubGlobal("WebSocket", Socket);
  const snapshot = vi.fn(),
    event = vi.fn(),
    connection = vi.fn();
  const close = subscribeEvents(snapshot, event, connection);
  let ws = Socket.all[0];
  ws.onmessage({
    data: JSON.stringify({
      type: "snapshot",
      instance_id: "a",
      watermark: 5,
      events: [],
    }),
  });
  ws.onmessage({
    data: JSON.stringify({ type: "comment", instance_id: "a", id: 5 }),
  });
  expect(event).not.toHaveBeenCalled();
  ws.onmessage({
    data: JSON.stringify({ type: "comment", instance_id: "a", id: 6 }),
  });
  expect(event).toHaveBeenCalledTimes(1);
  ws.close();
  vi.advanceTimersByTime(999);
  expect(Socket.all).toHaveLength(1);
  vi.advanceTimersByTime(1);
  expect(Socket.all).toHaveLength(2);
  ws = Socket.all[1];
  ws.onmessage({
    data: JSON.stringify({
      type: "snapshot",
      instance_id: "b",
      watermark: 0,
      events: [],
    }),
  });
  ws.onmessage({
    data: JSON.stringify({ type: "comment", instance_id: "b", id: 1 }),
  });
  expect(event).toHaveBeenCalledTimes(2);
  close();
  vi.runAllTimers();
  expect(Socket.all).toHaveLength(2);
});
