import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { ThemeSwitcher } from "./ThemeSwitcher";

it("switches both ways and restores the browser preference after remount", () => {
  localStorage.clear();
  const first = render(<ThemeSwitcher />);
  expect(screen.getByRole("button", { name: "Klasyczny" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  fireEvent.click(screen.getByRole("button", { name: "Glass" }));
  expect(document.documentElement.dataset.theme).toBe("glass");
  first.unmount();
  render(<ThemeSwitcher />);
  expect(screen.getByRole("button", { name: "Glass" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  fireEvent.click(screen.getByRole("button", { name: "Klasyczny" }));
  expect(document.documentElement.dataset.theme).toBe("classic");
});
it("works when browser storage is blocked", () => {
  const read = vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
    throw new Error("blocked");
  });
  const write = vi
    .spyOn(Storage.prototype, "setItem")
    .mockImplementation(() => {
      throw new Error("blocked");
    });
  try {
    render(<ThemeSwitcher />);
    fireEvent.click(screen.getByRole("button", { name: "Glass" }));
    expect(document.documentElement.dataset.theme).toBe("glass");
  } finally {
    read.mockRestore();
    write.mockRestore();
  }
});
