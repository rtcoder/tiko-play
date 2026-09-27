import { render, screen } from "@testing-library/react";
import { it, expect, vi } from "vitest";
import App from "./App";
const fixture = vi.hoisted(() => ({
  config: {
    version: 2,
    streamer_id: "a",
    target_user: "",
    mappings: [],
    show_logs: false,
    countdown_enabled: true,
  },
  state: {
    status: "connected",
    output: "enabled",
    generation: 1,
    active_config_revision: 1,
    config_revision: 1,
    instance_id: "x",
    error: null,
    config_error: null,
    recovery_data: null,
  },
}));
vi.mock("./api/client", () => ({
  bootstrapSession: async () => {},
  fetchState: async () => fixture.state,
  request: async (path: string) => (path === "/api/keys" ? [] : {}),
  configApi: {
    load: async () => ({ config: fixture.config, config_revision: 1 }),
    save: vi.fn(),
    start: vi.fn(),
  },
}));
vi.mock("./api/events", () => ({
  subscribeEvents: (snapshot: any, event: any, connection: any) => {
    snapshot({
      state: fixture.state,
      events: [],
      watermark: 0,
      instance_id: "x",
    });
    connection(false);
    return () => {};
  },
}));
it("does not present a stale connected state as currently active", async () => {
  render(<App />);
  expect(
    await screen.findByRole("heading", { name: "Stan nasłuchu nieznany" }),
  ).toBeInTheDocument();
  expect(
    screen.queryByText("Wysyłanie klawiszy jest aktywne."),
  ).not.toBeInTheDocument();
});
