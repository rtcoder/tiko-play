import { useState } from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { ChatSourceSettings } from "./ChatSourceSettings";
import { twitchAuthApi } from "../api/client";
import type { AppConfig, TwitchAuthState } from "../api/types";
vi.mock("../api/client", () => ({
  twitchAuthApi: { start: vi.fn(), cancel: vi.fn(), disconnect: vi.fn() },
  youtubeKeyApi: { state: vi.fn(async () => ({ configured: false })) },
}));
const config: AppConfig = {
  version: 4,
  platform: "tiktok",
  tiktok: { channel: "alice", target_user: "Bob" },
  twitch: { channel: "other", target_user: "carol" },
  youtube: { channel: "", target_user: "" },
  kick: { channel: "", target_user: "", chatroom_id: null },
  mappings: [],
  show_logs: false,
  countdown_enabled: true,
};
const auth: TwitchAuthState = {
  configured: true,
  status: "disconnected",
  login: null,
  error: null,
  attempt_id: 0,
};
function Harness() {
  const [cfg, setCfg] = useState(config);
  return (
    <ChatSourceSettings
      config={cfg}
      onChange={(p) => setCfg({ ...cfg, ...p })}
      auth={auth}
      onAuthChanged={async () => {}}
    />
  );
}
it("keeps separate channel and user settings while switching sources", () => {
  render(<Harness />);
  expect(screen.getByRole("textbox", { name: "Kanał" })).toHaveValue("alice");
  fireEvent.click(screen.getByRole("tab", { name: "Twitch" }));
  expect(screen.getByRole("textbox", { name: "Kanał" })).toHaveValue("other");
  fireEvent.change(screen.getByRole("textbox", { name: "Kanał" }), {
    target: { value: "new" },
  });
  fireEvent.click(screen.getByRole("tab", { name: "TikTok" }));
  expect(screen.getByRole("textbox", { name: "Kanał" })).toHaveValue("alice");
  expect(screen.getByRole("textbox", { name: /Dozwoleni/ })).toHaveValue("Bob");
  fireEvent.click(screen.getByRole("tab", { name: "Twitch" }));
  expect(screen.getByRole("textbox", { name: "Kanał" })).toHaveValue("new");
});
it("shows a safe activation link then removes the code when auth completes", async () => {
  vi.mocked(twitchAuthApi.start).mockResolvedValue({
    ...auth,
    status: "pending",
    attempt_id: 1,
    user_code: "ABCD",
    verification_uri: "https://www.twitch.tv/activate",
    expires_at: Date.now() / 1000 + 300,
  });
  const props = {
    config: { ...config, platform: "twitch" as const },
    onChange: vi.fn(),
    onAuthChanged: vi.fn(async () => {}),
  };
  const view = render(<ChatSourceSettings {...props} auth={auth} />);
  fireEvent.click(screen.getByRole("button", { name: "Połącz konto Twitch" }));
  expect(await screen.findByText("ABCD")).toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: "Otwórz aktywację Twitcha" }),
  ).toHaveAttribute("href", "https://www.twitch.tv/activate");
  view.rerender(
    <ChatSourceSettings
      {...props}
      auth={{ ...auth, status: "connected", login: "alice", attempt_id: 1 }}
    />,
  );
  await waitFor(() =>
    expect(screen.queryByText("ABCD")).not.toBeInTheDocument(),
  );
});
it("does not render foreign activation URLs", async () => {
  vi.mocked(twitchAuthApi.start).mockResolvedValue({
    ...auth,
    status: "pending",
    attempt_id: 1,
    user_code: "ABCD",
    verification_uri: "https://evil.test",
    expires_at: Date.now() / 1000 + 300,
  });
  render(
    <ChatSourceSettings
      config={{ ...config, platform: "twitch" }}
      onChange={vi.fn()}
      auth={auth}
      onAuthChanged={async () => {}}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Połącz konto Twitch" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(/adres/);
  expect(screen.queryByRole("link")).not.toBeInTheDocument();
});
it("keeps YouTube and Kick settings separate and clears stale room ID when changing Kick channel", () => {
  render(<Harness />);
  expect(
    screen.queryByRole("combobox", { name: "Źródło czatu" }),
  ).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("tab", { name: "Kick" }));
  fireEvent.change(screen.getByRole("textbox", { name: "Kanał" }), {
    target: { value: "alice" },
  });
  fireEvent.change(screen.getByRole("spinbutton", { name: /ID pokoju/ }), {
    target: { value: "42" },
  });
  fireEvent.click(screen.getByRole("tab", { name: "YouTube" }));
  fireEvent.change(
    screen.getByRole("textbox", { name: /Transmisja YouTube/ }),
    { target: { value: "https://youtu.be/abcdefghijk" } },
  );
  expect(screen.getByText(/ID kanałów użytkowników/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("tab", { name: "Kick" }));
  expect(screen.getByRole("textbox", { name: "Kanał" })).toHaveValue("alice");
  expect(screen.getByRole("spinbutton", { name: /ID pokoju/ })).toHaveValue(42);
  fireEvent.change(screen.getByRole("textbox", { name: "Kanał" }), {
    target: { value: "bob" },
  });
  expect(screen.getByRole("spinbutton", { name: /ID pokoju/ })).toHaveValue(
    null,
  );
  fireEvent.click(screen.getByRole("tab", { name: "YouTube" }));
  expect(
    screen.getByRole("textbox", { name: /Transmisja YouTube/ }),
  ).toHaveValue("https://youtu.be/abcdefghijk");
});

it("supports arrow, Home and End navigation between platform tabs", () => {
  render(<Harness />);
  const first = screen.getByRole("tab", { name: "TikTok" });
  expect(first).toHaveAttribute("aria-selected", "true");
  fireEvent.keyDown(first, { key: "ArrowRight" });
  const twitch = screen.getByRole("tab", { name: "Twitch" });
  expect(twitch).toHaveFocus();
  expect(twitch).toHaveAttribute("aria-selected", "true");
  expect(screen.getByRole("tabpanel")).toHaveAccessibleName("Twitch");
  fireEvent.keyDown(twitch, { key: "End" });
  const kick = screen.getByRole("tab", { name: "Kick" });
  expect(kick).toHaveFocus();
  fireEvent.keyDown(kick, { key: "ArrowRight" });
  expect(first).toHaveFocus();
  fireEvent.keyDown(first, { key: "ArrowLeft" });
  expect(kick).toHaveFocus();
  fireEvent.keyDown(kick, { key: "Home" });
  expect(first).toHaveAttribute("aria-selected", "true");
});
