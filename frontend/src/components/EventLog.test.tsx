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

it("translates app messages and preference events but never viewer text", async () => {
  const { setLanguage } = await import("../i18n");
  setLanguage("en");
  const base = { instance_id: "a", timestamp: "2026-09-27T10:00:00Z" };
  render(
    <EventLog
      events={[
        {
          ...base,
          id: 1,
          type: "comment",
          payload: { user: "u", comment: "Zatrzymany" },
        },
        { ...base, id: 2, type: "status", payload: { status: "stopped" } },
        {
          ...base,
          id: 3,
          type: "preferences_changed",
          payload: { language: "en" },
        },
        {
          ...base,
          id: 4,
          type: "error",
          payload: { message: "Nie znaleziono streamera." },
        },
      ]}
      onClear={() => {}}
    />,
  );
  expect(screen.getByText("u: Zatrzymany")).toBeInTheDocument();
  expect(screen.getByText("Stopped")).toBeInTheDocument();
  expect(screen.getByText("Streamer not found.")).toBeInTheDocument();
  expect(screen.getByText("Language: English")).toBeInTheDocument();
  expect(screen.queryByText("preferences_changed")).not.toBeInTheDocument();
});
