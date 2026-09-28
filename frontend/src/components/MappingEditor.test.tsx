import { render, screen, fireEvent } from "@testing-library/react";
import { it, expect, vi } from "vitest";
import { MappingEditor } from "./MappingEditor";
it("changes trigger without losing combo and removes the selected row", () => {
  const change = vi.fn();
  const mappings = [
    { id: "a", trigger: "left", keys: ["ctrl", "a"] },
    { id: "b", trigger: "right", keys: ["right"] },
  ];
  render(
    <MappingEditor
      mappings={mappings}
      onChange={change}
      presets={{}}
      keys={["ctrl", "a", "right"]}
    />,
  );
  fireEvent.change(screen.getByDisplayValue("left"), {
    target: { value: "lewo" },
  });
  expect(change.mock.calls[0][0][0]).toEqual({
    id: "a",
    trigger: "lewo",
    keys: ["ctrl", "a"],
  });
  fireEvent.click(screen.getAllByRole("button", { name: "Usuń mapowanie" })[0]);
  expect(change.mock.calls[1][0]).toEqual([mappings[1]]);
});

it("applies translated presets using the original key and unchanged triggers", async () => {
  const { setLanguage } = await import("../i18n");
  setLanguage("en");
  const change = vi.fn();
  render(
    <MappingEditor
      mappings={[]}
      onChange={change}
      keys={["left"]}
      presets={{ Strzałki: [{ trigger: "left", keys: ["left"] }] }}
    />,
  );
  fireEvent.change(screen.getByRole("combobox", { name: "Preset" }), {
    target: { value: "Strzałki" },
  });
  expect(
    screen.getByRole("option", { name: "Arrow keys" }),
  ).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Apply preset" }));
  expect(change.mock.calls[0][0][0]).toMatchObject({
    trigger: "left",
    keys: ["left"],
  });
});
