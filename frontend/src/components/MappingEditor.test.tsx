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

it("keeps simple mappings compact and changes the key without opening a sequence", () => {
  const change = vi.fn();
  render(
    <MappingEditor
      mappings={[{ id: "m", trigger: "8", keys: ["up"] }]}
      onChange={change}
      presets={{}}
      keys={["up", "down"]}
    />,
  );
  expect(
    screen.queryByRole("combobox", { name: "Typ kroku 1" }),
  ).not.toBeInTheDocument();
  expect(screen.queryByText(/10000/)).not.toBeInTheDocument();
  fireEvent.change(
    screen.getByRole("combobox", { name: "Klawisz mapowania 1" }),
    { target: { value: "down" } },
  );
  expect(change.mock.calls[0][0][0]).toEqual({
    id: "m",
    trigger: "8",
    action: { steps: [{ type: "press", keys: ["down"] }] },
  });
});

it("opens and closes sequence options without flattening or losing existing steps", () => {
  const change = vi.fn();
  const mapping = {
    id: "m",
    trigger: "go",
    action: {
      steps: [
        { type: "hold" as const, keys: ["up"], duration_ms: 500 },
        { type: "wait" as const, duration_ms: 100 },
      ],
    },
  };
  render(
    <MappingEditor
      mappings={[mapping]}
      onChange={change}
      presets={{}}
      keys={["up"]}
    />,
  );
  expect(screen.getByText(/Przytrzymaj.*500 ms/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Edytuj sekwencję" }));
  expect(
    screen.getByRole("spinbutton", { name: "Czas kroku 1 (ms)" }),
  ).toHaveValue(500);
  fireEvent.click(screen.getByRole("button", { name: "Zwiń opcje" }));
  expect(screen.queryByRole("spinbutton")).not.toBeInTheDocument();
  expect(change).not.toHaveBeenCalled();
});

it("shows invalid sequence fields immediately so a blocked save can be corrected", () => {
  render(
    <MappingEditor
      mappings={[
        {
          id: "m",
          trigger: "go",
          action: { steps: [{ type: "hold", keys: ["up"], duration_ms: 25 }] },
        },
      ]}
      onChange={() => {}}
      presets={{}}
      keys={["up"]}
    />,
  );
  expect(
    screen.getByRole("spinbutton", { name: "Czas kroku 1 (ms)" }),
  ).toHaveValue(25);
  expect(screen.getByRole("alert")).toHaveTextContent("50–3000");
});

it("keeps an automatically opened invalid action open while the user corrects it", () => {
  const change = vi.fn();
  const props = { onChange: change, presets: {}, keys: ["up"] };
  const mapping = {
    id: "m",
    trigger: "go",
    action: {
      steps: [{ type: "hold" as const, keys: ["up"], duration_ms: 25 }],
    },
  };
  const { rerender } = render(
    <MappingEditor {...props} mappings={[mapping]} />,
  );
  fireEvent.change(
    screen.getByRole("spinbutton", { name: "Czas kroku 1 (ms)" }),
    { target: { value: "50" } },
  );
  rerender(<MappingEditor {...props} mappings={change.mock.calls[0][0]} />);
  expect(
    screen.getByRole("spinbutton", { name: "Czas kroku 1 (ms)" }),
  ).toHaveValue(50);
  expect(screen.getByRole("button", { name: "Zwiń opcje" })).toBeEnabled();
});
