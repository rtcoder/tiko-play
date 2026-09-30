import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { it, expect, vi } from "vitest";
import { request } from "../api/client";
import { OverlaySettings } from "./OverlaySettings";
vi.mock("../api/client", () => ({ request: vi.fn() }));
const settings = {
  enabled: false,
  port: 18765,
  show_commands: true,
  show_last_action: true,
  show_actor: false,
  show_status: true,
  font_size: 24,
  accent: "#7c83ff",
};
it("starts hidden-author overlay through protected settings and exposes copyable URL", async () => {
  vi.mocked(request).mockImplementation(async (path, method, body) =>
    method === "PUT"
      ? {
          settings: body,
          running: true,
          url: "http://127.0.0.1:18765/overlay#token=test-token",
          error: null,
        }
      : { settings, running: false, url: null, error: null },
  );
  render(<OverlaySettings connected />);
  const enabled = await screen.findByLabelText("Włącz nakładkę");
  expect(screen.getByLabelText("Pokaż nick autora")).not.toBeChecked();
  fireEvent.click(enabled);
  fireEvent.click(screen.getByRole("button", { name: "Zapisz i zastosuj" }));
  await waitFor(() =>
    expect(request).toHaveBeenCalledWith("/api/overlay", "PUT", {
      ...settings,
      enabled: true,
    }),
  );
  expect(await screen.findByLabelText("Adres do OBS")).toHaveValue(
    "http://127.0.0.1:18765/overlay#token=test-token",
  );
});
it("preserves the active URL when a new port cannot be applied", async () => {
  vi.mocked(request).mockImplementation(async (path, method) => {
    if (method === "PUT") throw Error("Port zajęty");
    return {
      settings: { ...settings, enabled: true },
      running: true,
      url: "http://127.0.0.1:18765/overlay#token=old",
      error: null,
    };
  });
  render(<OverlaySettings connected />);
  fireEvent.change(await screen.findByLabelText("Port nakładki"), {
    target: { value: "18766" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Zapisz i zastosuj" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Port zajęty");
  expect(screen.getByLabelText("Adres do OBS")).toHaveValue(
    "http://127.0.0.1:18765/overlay#token=old",
  );
});

it("does not discard unsaved appearance when rotating the URL", async () => {
  vi.mocked(request).mockResolvedValue({
    settings: { ...settings, enabled: true },
    running: true,
    url: "http://127.0.0.1:18765/overlay#token=new",
    error: null,
  });
  render(<OverlaySettings connected />);
  fireEvent.change(await screen.findByLabelText("Port nakładki"), {
    target: { value: "18766" },
  });
  fireEvent.click(screen.getByText("Zmień adres nakładki"));
  fireEvent.click(screen.getByRole("button", { name: "Wygeneruj nowy adres" }));
  await waitFor(() =>
    expect(request).toHaveBeenCalledWith(
      "/api/overlay/rotate",
      "POST",
      undefined,
    ),
  );
  expect(screen.getByLabelText("Port nakładki")).toHaveValue(18766);
});
