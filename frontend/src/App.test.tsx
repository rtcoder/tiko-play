import { configApi } from "./api/client";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { it, expect, vi } from "vitest";
import App from "./App";
const fixture = vi.hoisted(() => ({
  config: {
    version: 4,
    platform: "tiktok",
    tiktok: { channel: "a", target_user: "" },
    twitch: { channel: "b", target_user: "" },
    youtube: { channel: "", target_user: "" },
    kick: { channel: "", target_user: "", chatroom_id: null },
    mappings: [],
    show_logs: false,
    countdown_enabled: true,
  },
  connected: false,
  auth: {
    configured: true,
    status: "disconnected",
    login: null,
    error: null,
    attempt_id: 0,
  },
  state: {
    status: "connected",
    output: "enabled",
    generation: 1,
    active_config_revision: 1,
    active_platform: "tiktok",
    active_channel: "a",
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
  twitchAuthApi: { state: async () => fixture.auth },
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
    connection(fixture.connected);
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

it("saves multiple allowed users from the multiline field", async () => {
  vi.mocked(configApi.save).mockImplementation(async (config, revision) => ({
    config,
    config_revision: revision + 1,
  }));
  render(<App />);
  const field = await screen.findByRole("textbox", {
    name: /Dozwoleni użytkownicy/,
  });
  const users = "@alice, bob\ncarol";
  fireEvent.change(field, { target: { value: users } });
  await waitFor(() =>
    expect(configApi.save).toHaveBeenCalledWith(
      expect.objectContaining({ tiktok: { channel: "a", target_user: users } }),
      1,
    ),
  );
  expect(field).toHaveValue(users);
});

it("blocks Twitch start without authentication", async () => {
  fixture.connected = true;
  fixture.config.platform = "twitch";
  fixture.state.status = "stopped";
  render(<App />);
  expect(
    await screen.findByRole("button", { name: /Rozpocznij nasłuch/ }),
  ).toBeDisabled();
  fixture.connected = false;
  fixture.config.platform = "tiktok";
  fixture.state.status = "connected";
});
it("shows active Twitch source while settings select TikTok", async () => {
  fixture.connected = true;
  fixture.state.active_platform = "twitch";
  fixture.state.active_channel = "live_channel";
  render(<App />);
  expect(
    await screen.findByText("Aktywne źródło: Twitch · @live_channel"),
  ).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "TikTok" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  fixture.connected = false;
  fixture.state.active_platform = "tiktok";
  fixture.state.active_channel = "a";
});
