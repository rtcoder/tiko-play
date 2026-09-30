import { render, screen } from "@testing-library/react";
import { it, expect } from "vitest";
import { OverlayView } from "./Overlay";
import type { OverlaySnapshot } from "./types";
const snapshot: OverlaySnapshot = {
  schema_version: 1,
  sequence: 1,
  mode: "direct",
  paused: false,
  language: "pl",
  commands: [
    { comment: "8", action: { steps: [{ type: "press", keys: ["up"] }] } },
  ],
  last_action: {
    id: 1,
    comment: "<script>alert(1)</script>",
    actor: "alice",
    action: { steps: [{ type: "hold", keys: ["up"], duration_ms: 500 }] },
  },
  presentation: {
    show_commands: true,
    show_last_action: true,
    show_actor: false,
    show_status: true,
    font_size: 24,
    accent: "#7788ff",
  },
};
it("shows executed action as text, hides actor by default and has no voting UI", () => {
  const { container } = render(
    <OverlayView snapshot={snapshot} status="connected" />,
  );
  expect(screen.getByText("<script>alert(1)</script>")).toBeInTheDocument();
  expect(container.querySelector("script")).toBeNull();
  expect(screen.queryByText("alice")).toBeNull();
  expect(
    screen.getByText("Przytrzymaj ↑ Góra przez 500 ms"),
  ).toBeInTheDocument();
  expect(screen.queryByText(/głos/i)).toBeNull();
});
it("shows pause and explicitly enabled actor, then clears stale actions on disconnect", () => {
  const { rerender } = render(
    <OverlayView
      snapshot={{
        ...snapshot,
        paused: true,
        presentation: { ...snapshot.presentation, show_actor: true },
      }}
      status="connected"
    />,
  );
  expect(screen.getByText("Pauza")).toBeInTheDocument();
  expect(screen.getByText("alice")).toBeInTheDocument();
  rerender(<OverlayView snapshot={snapshot} status="disconnected" />);
  expect(screen.getByText("Brak połączenia z TikoPlay")).toBeInTheDocument();
  expect(screen.queryByText("<script>alert(1)</script>")).toBeNull();
});
