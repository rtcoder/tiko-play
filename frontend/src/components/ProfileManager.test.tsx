import { useState } from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { ProfileManager } from "./ProfileManager";
import type { AppConfig } from "../api/types";
import { setLanguage } from "../i18n";
import { request } from "../api/client";
import { act } from "@testing-library/react";

const initial = {
  version: 6,
  platform: "tiktok",
  tiktok: { channel: "host" },
  twitch: { channel: "" },
  youtube: { channel: "" },
  kick: { channel: "", chatroom_id: null },
  active_profile_id: "a",
  profiles: [
    {
      id: "a",
      name: "Moja gra",
      filters: { tiktok: "alice", twitch: "", youtube: "", kick: "" },
      mappings: [{ id: "m", trigger: "go", keys: ["left"] }],
    },
  ],
  show_logs: false,
  countdown_enabled: true,
} as AppConfig;
const templates = [
  {
    id: "numpad",
    name: "NumPad 2468",
    category: "Ogólne",
    description: "2 → dół",
    mappings: [
      { trigger: "2", keys: ["down"] },
      { trigger: "4", keys: ["left"] },
      { trigger: "6", keys: ["right"] },
      { trigger: "8", keys: ["up"] },
    ],
  },
];
vi.mock("../api/client", () => ({
  request: vi.fn(async () => ({
    id: "import",
    name: "Imported",
    mappings: [{ id: "new", trigger: "2", keys: ["down"] }],
    filters: { tiktok: "", twitch: "", youtube: "", kick: "" },
  })),
}));

function Harness({ disabled = false, fail = false } = {}) {
  const [config, setConfig] = useState(initial);
  return (
    <>
      <ProfileManager
        config={config}
        templates={templates}
        disabled={disabled}
        dirty={false}
        onReload={async () => {}}
        onMutate={async (transform) => {
          if (fail) throw new Error("Disk full");
          setConfig((old) => transform(old));
        }}
      />
      <output data-testid="config">{JSON.stringify(config)}</output>
    </>
  );
}
const config = () => JSON.parse(screen.getByTestId("config").textContent!);

it("unlocks when another panel switches profile during import", async () => {
  setLanguage("pl");
  let resolve!: (value: unknown) => void;
  vi.mocked(request).mockImplementationOnce(
    () =>
      new Promise((done) => {
        resolve = done;
      }),
  );
  const props = {
    templates,
    disabled: false,
    dirty: false,
    onReload: async () => {},
    onMutate: async () => {},
  };
  const view = render(<ProfileManager {...props} config={initial} />);
  const file = new File(["{}"], "game.json");
  Object.defineProperty(file, "text", { value: async () => "{}" });
  fireEvent.change(screen.getByLabelText("Importuj profil"), {
    target: { files: [file] },
  });
  await waitFor(() => expect(resolve).toBeDefined());
  const next = {
    ...initial,
    profiles: [{ ...initial.profiles[0], id: "remote" }],
    active_profile_id: "remote",
  };
  view.rerender(<ProfileManager {...props} config={next} />);
  await act(async () =>
    resolve({ id: "stale", name: "Stale", mappings: [], filters: {} }),
  );
  expect(screen.getByRole("button", { name: "Nowy profil" })).toBeEnabled();
  expect(screen.queryByText("Stale")).not.toBeInTheDocument();
});

it("creates NumPad profile without overwriting the original and switches profiles", async () => {
  setLanguage("pl");
  render(<Harness />);
  fireEvent.click(screen.getByRole("button", { name: "Nowy profil" }));
  fireEvent.change(screen.getByLabelText("Szablon profilu"), {
    target: { value: "numpad" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Utwórz profil" }));
  await waitFor(() => expect(config().profiles).toHaveLength(2));
  expect(config().profiles[0].mappings[0].keys).toEqual(["left"]);
  expect(config().profiles[1].mappings.map((m: any) => m.trigger)).toEqual([
    "2",
    "4",
    "6",
    "8",
  ]);
  fireEvent.change(screen.getByLabelText("Aktywny profil"), {
    target: { value: "a" },
  });
  await waitFor(() => expect(config().active_profile_id).toBe("a"));
});

it("duplicates with fresh IDs and keeps private filters locally", async () => {
  setLanguage("pl");
  render(<Harness />);
  fireEvent.click(screen.getByRole("button", { name: "Duplikuj" }));
  await waitFor(() => expect(config().profiles).toHaveLength(2));
  expect(config().profiles[1].id).not.toBe("a");
  expect(config().profiles[1].mappings[0].id).not.toBe("m");
  expect(config().profiles[1].filters.tiktok).toBe("alice");
});

it("blocks mutation during LIVE and deletion of last profile", () => {
  setLanguage("pl");
  render(<Harness disabled />);
  expect(screen.getByLabelText("Aktywny profil")).toBeDisabled();
  expect(screen.getByRole("button", { name: "Nowy profil" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Usuń profil" })).toBeDisabled();
});

it("retains the creation form after a save error", async () => {
  setLanguage("pl");
  render(<Harness fail />);
  fireEvent.click(screen.getByRole("button", { name: "Nowy profil" }));
  fireEvent.change(screen.getByLabelText("Nazwa profilu"), {
    target: { value: "Draft" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Utwórz profil" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Disk full");
  expect(screen.getByLabelText("Nazwa profilu")).toHaveValue("Draft");
  expect(config().profiles).toHaveLength(1);
});

it("imports only after reviewing and confirming the preview", async () => {
  setLanguage("pl");
  render(<Harness />);
  const file = new File(["{}"], "game.json", { type: "application/json" });
  Object.defineProperty(file, "text", { value: async () => "{}" });
  fireEvent.change(screen.getByLabelText("Importuj profil"), {
    target: { files: [file] },
  });
  expect(await screen.findByText("Imported")).toBeInTheDocument();
  expect(config().profiles).toHaveLength(1);
  fireEvent.click(
    screen.getByRole("button", { name: "Dodaj importowany profil" }),
  );
  await waitFor(() => expect(config().profiles).toHaveLength(2));
});

it("renames and deletes only the selected profile with an explicit replacement", async () => {
  setLanguage("pl");
  render(<Harness />);
  expect(screen.getByRole("button", { name: "Usuń profil" })).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "Zmień nazwę" }));
  fireEvent.change(screen.getByLabelText("Nazwa profilu"), {
    target: { value: "Renamed" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Zapisz nazwę" }));
  await waitFor(() => expect(config().profiles[0].name).toBe("Renamed"));
  fireEvent.click(screen.getByRole("button", { name: "Duplikuj" }));
  await waitFor(() => expect(config().profiles).toHaveLength(2));
  fireEvent.click(screen.getByRole("button", { name: "Usuń profil" }));
  expect(config().profiles).toHaveLength(2);
  fireEvent.click(screen.getByRole("button", { name: "Potwierdź usunięcie" }));
  await waitFor(() => expect(config().profiles).toHaveLength(1));
  expect(config().active_profile_id).toBe("a");
  expect(config().profiles[0].name).toBe("Renamed");
});
