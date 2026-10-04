import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { it, expect, vi } from "vitest";
import { OutputSafety } from "./OutputSafety";
import { request } from "../api/client";
vi.mock("../api/client", () => ({ request: vi.fn() }));
const target = { app: "/game", pid: 42, started: "100", name: "Game" };
it("applies the selected process identity and reports the actual shortcut", async () => {
  const state = {
    enabled: false,
    target: null,
    targets: [target],
    error: null,
    hotkey: { key: "F10", active: true, error: null },
  };
  vi.mocked(request).mockResolvedValue(state);
  render(<OutputSafety running={false} connected output="disabled" />);
  await screen.findByText("Aktywny STOP: Ctrl + Alt + Shift + F10");
  fireEvent.click(screen.getByLabelText("Chroń wybraną aplikację"));
  expect(
    screen.getByRole("button", { name: "Zastosuj ochronę i skrót" }),
  ).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Uruchomiona gra lub aplikacja"), {
    target: { value: JSON.stringify([target.app, target.pid, target.started]) },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Zastosuj ochronę i skrót" }),
  );
  await waitFor(() =>
    expect(request).toHaveBeenCalledWith("/api/output-safety", "PUT", {
      enabled: true,
      target,
      key: "F10",
    }),
  );
});
it("locks settings while running and exposes unavailable shortcut", async () => {
  vi.mocked(request).mockResolvedValue({
    enabled: true,
    target,
    targets: [target],
    error: null,
    hotkey: {
      key: "F10",
      active: false,
      error: "Skrót systemowy jest niedostępny.",
    },
  });
  render(<OutputSafety running connected output="paused_focus" />);
  await screen.findByText("Skrót STOP nie jest aktywny.");
  expect(screen.getByLabelText("Chroń wybraną aplikację")).toBeDisabled();
  expect(screen.getByText(/Kolejka została wyczyszczona/)).toBeInTheDocument();
});
