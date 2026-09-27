import { render, screen } from "@testing-library/react";
import { it, expect } from "vitest";
import { EventLog } from "./EventLog";
it("treats comments as text instead of HTML", () => {
  const { container } = render(
    <EventLog
      events={[
        {
          id: 1,
          instance_id: "a",
          timestamp: "2026-09-27T10:00:00Z",
          type: "comment",
          payload: { user: "u", comment: "<img onerror=alert(1)>" },
        },
      ]}
      onClear={() => {}}
    />,
  );
  expect(screen.getByText("u: <img onerror=alert(1)>")).toBeInTheDocument();
  expect(container.querySelector("img")).toBeNull();
});
