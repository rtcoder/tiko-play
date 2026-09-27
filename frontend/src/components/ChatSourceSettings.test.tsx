import { useState } from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { ChatSourceSettings } from "./ChatSourceSettings";
import { twitchAuthApi } from "../api/client";
import type { AppConfig, TwitchAuthState } from "../api/types";
vi.mock("../api/client", () => ({
  twitchAuthApi: { start: vi.fn(), cancel: vi.fn(), disconnect: vi.fn() },
}));
const config: AppConfig = {
  version: 3,
  platform: "tiktok",
  tiktok: { channel: "alice", target_user: "Bob" },
  twitch: { channel: "other", target_user: "carol" },
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
  fireEvent.change(screen.getByRole("combobox", { name: "Źródło czatu" }), {
    target: { value: "twitch" },
  });
  expect(screen.getByRole("textbox", { name: "Kanał" })).toHaveValue("other");
  fireEvent.change(screen.getByRole("textbox", { name: "Kanał" }), {
    target: { value: "new" },
  });
  fireEvent.change(screen.getByRole("combobox", { name: "Źródło czatu" }), {
    target: { value: "tiktok" },
  });
  expect(screen.getByRole("textbox", { name: "Kanał" })).toHaveValue("alice");
  expect(screen.getByRole("textbox", { name: /Dozwoleni/ })).toHaveValue("Bob");
  fireEvent.change(screen.getByRole("combobox", { name: "Źródło czatu" }), {
    target: { value: "twitch" },
  });
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
