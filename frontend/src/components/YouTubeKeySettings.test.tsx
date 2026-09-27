import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { YouTubeKeySettings } from "./YouTubeKeySettings";
import { youtubeKeyApi } from "../api/client";
vi.mock("../api/client", () => ({
  youtubeKeyApi: {
    state: vi.fn(async () => ({ configured: false })),
    save: vi.fn(async () => ({ configured: true })),
    remove: vi.fn(async () => ({ configured: false })),
  },
}));
it("saves a key separately, clears its input and supports removal", async () => {
  render(<YouTubeKeySettings />);
  const input = screen.getByLabelText("Klucz YouTube Data API");
  expect(input).toHaveAttribute("type", "password");
  await screen.findByText("Brak zapisanego klucza.");
  fireEvent.change(input, { target: { value: "PRIVATE_KEY" } });
  fireEvent.click(screen.getByRole("button", { name: "Zapisz klucz" }));
  await screen.findByText("Klucz zapisany w systemowym magazynie poświadczeń.");
  expect(youtubeKeyApi.save).toHaveBeenCalledWith("PRIVATE_KEY");
  expect(input).toHaveValue("");
  fireEvent.click(screen.getByRole("button", { name: "Usuń klucz" }));
  await screen.findByText("Brak zapisanego klucza.");
});
it("shows storage errors and allows retry", async () => {
  vi.mocked(youtubeKeyApi.save).mockRejectedValueOnce(
    new Error("Magazyn niedostępny"),
  );
  render(<YouTubeKeySettings />);
  await screen.findByText("Brak zapisanego klucza.");
  fireEvent.change(screen.getByLabelText("Klucz YouTube Data API"), {
    target: { value: "PRIVATE_KEY" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Zapisz klucz" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Magazyn niedostępny",
  );
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Zapisz klucz" })).toBeEnabled(),
  );
});
