import { useState } from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { expect, it } from "vitest";
import { ActionEditor } from "./ActionEditor";
import type { ActionDefinition } from "../api/types";

it("edits holds, inserts pauses, reorders and preserves invalid duration", () => {
  function Demo() {
    const [action, setAction] = useState<ActionDefinition>({
      steps: [{ type: "press", keys: ["a"] }],
    });
    return (
      <>
        <ActionEditor
          action={action}
          onChange={setAction}
          keys={["a", "b"]}
          mappingNumber={1}
        />
        <output>{JSON.stringify(action)}</output>
      </>
    );
  }
  render(<Demo />);
  fireEvent.change(screen.getByRole("combobox", { name: "Typ kroku 1" }), {
    target: { value: "hold" },
  });
  fireEvent.change(
    screen.getByRole("spinbutton", { name: "Czas kroku 1 (ms)" }),
    { target: { value: "25" } },
  );
  expect(screen.getByRole("alert")).toHaveTextContent("50–3000");
  expect(screen.getByRole("spinbutton")).toHaveValue(25);
  fireEvent.click(screen.getByRole("button", { name: "Dodaj pauzę" }));
  fireEvent.click(
    screen.getByRole("button", { name: "Przesuń krok 2 w górę" }),
  );
  expect(screen.getAllByRole("combobox")[0]).toHaveValue("wait");
  expect(screen.getByRole("status")).toHaveTextContent('"duration_ms":25');
});

it("shows total declared hold and pause time", () => {
  render(
    <ActionEditor
      action={{
        steps: [
          { type: "hold", keys: ["a"], duration_ms: 500 },
          { type: "wait", duration_ms: 100 },
        ],
      }}
      onChange={() => {}}
      keys={["a"]}
      mappingNumber={1}
    />,
  );
  expect(screen.getByText("Łącznie: 600 / 10000 ms")).toBeInTheDocument();
});
