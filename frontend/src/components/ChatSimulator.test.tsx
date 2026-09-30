import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { it, expect, vi } from "vitest";
import { ChatSimulator } from "./ChatSimulator";
import { request } from "../api/client";
import type { AppConfig } from "../api/types";
vi.mock("../api/client", () => ({ request: vi.fn() }));
const config: AppConfig = {
  version: 6,
  platform: "tiktok",
  tiktok: { channel: "" },
  twitch: { channel: "" },
  youtube: { channel: "" },
  kick: { channel: "", chatroom_id: null },
  active_profile_id: "a",
  profiles: [
    {
      id: "a",
      name: "Mario",
      mappings: [{ id: "go", trigger: "go", keys: ["up"] }],
      filters: { tiktok: "", twitch: "", youtube: "", kick: "" },
    },
  ],
  show_logs: false,
  countdown_enabled: true,
};
const report = {
  config_revision: 7,
  profile_id: "a",
  profile_name: "Mario",
  platform: "tiktok",
  planned_count: 0,
  rejected_count: 1,
  duration_ms: 0,
  decisions: [
    {
      message_index: 0,
      offset_ms: 0,
      comment: "abc",
      user_id: "widz",
      reason: "no_mapping",
      steps: [],
    },
  ],
};
it("tests saved settings without saving a draft and shows the rejection reason", async () => {
  vi.mocked(request).mockResolvedValue(report);
  render(<ChatSimulator config={config} revision={7} dirty connected live />);
  expect(screen.getByText("Symulacja — bez klawiszy")).toBeInTheDocument();
  expect(screen.getByText(/Niezapisany szkic/)).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Komentarz widza"), {
    target: { value: "abc" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Sprawdź komentarz" }));
  expect(
    await screen.findByText("Brak mapowania dla tego komentarza."),
  ).toBeInTheDocument();
  expect(request).toHaveBeenLastCalledWith("/api/simulation", "POST", {
    expected_revision: 7,
    profile_id: "a",
    platform: "tiktok",
    messages: [{ offset_ms: 0, user_id: "widz", comment: "abc" }],
  });
});
it("builds a spam scenario from a saved mapping", async () => {
  vi.mocked(request).mockResolvedValue(report);
  render(
    <ChatSimulator
      config={config}
      revision={7}
      dirty={false}
      connected
      live={false}
    />,
  );
  fireEvent.click(screen.getByText("Więcej wiadomości / test spamu"));
  fireEvent.click(screen.getByRole("button", { name: "Wstaw przykład spamu" }));
  fireEvent.click(screen.getByRole("button", { name: "Uruchom scenariusz" }));
  await waitFor(() =>
    expect(request).toHaveBeenLastCalledWith(
      "/api/simulation",
      "POST",
      expect.objectContaining({
        messages: [0, 100, 200, 300, 600].map((offset_ms) => ({
          offset_ms,
          user_id: "widz",
          comment: "go",
        })),
      }),
    ),
  );
});
it("marks a result outdated after a saved revision changes in flight", async () => {
  let finish!: (value: any) => void;
  vi.mocked(request).mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  const props = { config, dirty: false, connected: true, live: false };
  const { rerender } = render(<ChatSimulator {...props} revision={7} />);
  fireEvent.click(screen.getByRole("button", { name: "Sprawdź komentarz" }));
  rerender(<ChatSimulator {...props} revision={8} />);
  finish(report);
  expect(
    await screen.findByText(
      "Ustawienia zmieniły się od tego testu. Uruchom go ponownie.",
    ),
  ).toBeInTheDocument();
});
