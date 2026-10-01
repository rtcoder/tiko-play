import { useState } from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { it, expect } from "vitest";
import { ControlLimits } from "./ControlLimits";
import { defaultLimits } from "../state/limits";
it("edits profile limits and keeps an invalid draft visible", () => {
  function Panel() {
    const [limits, setLimits] = useState(defaultLimits);
    return (
      <ControlLimits
        value={limits}
        onChange={setLimits}
        profileName="Gra"
        connected
      />
    );
  }
  render(<Panel />);
  const viewer = screen.getByLabelText("Odstęp dla jednego widza (ms)");
  fireEvent.change(viewer, { target: { value: "1000" } });
  expect(viewer).toHaveValue(1000);
  fireEvent.change(viewer, { target: { value: "" } });
  expect(viewer).toHaveAttribute("aria-invalid", "true");
  expect(screen.getByRole("alert")).toHaveTextContent("od 0 do 60000");
  fireEvent.click(screen.getByText("Co robić z nadmiarem? Kolejka"));
  expect(screen.getByLabelText("Miejsca w kolejce")).toHaveValue(100);
});
it("separates admission and actual execution and explains skips", () => {
  render(
    <ControlLimits
      profileName="Gra"
      connected={false}
      onChange={() => {}}
      stats={{
        counts: { accepted: 3, executed: 1, expired: 1, queue_full: 8 },
        recent: [
          {
            id: 1,
            reason: "expired",
            actor_id: "bob",
            comment: "go",
            mapping_id: "a",
          },
        ],
      }}
    />,
  );
  expect(screen.getByText("3")).toBeInTheDocument();
  expect(screen.getByText("9")).toBeInTheDocument();
  expect(screen.getByText("Brak miejsca w kolejce")).toBeInTheDocument();
  expect(screen.getByText(/mogą być nieaktualne/)).toBeInTheDocument();
  fireEvent.click(screen.getByText("Ostatnie decyzje i ich powody"));
  expect(screen.getByText("go")).toBeInTheDocument();
});
