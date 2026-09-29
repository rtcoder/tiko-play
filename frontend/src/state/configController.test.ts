import { it, expect, vi, afterEach } from "vitest";
import { ConfigController } from "./configController";
const config = {
  version: 6 as const,
  platform: "tiktok" as const,
  tiktok: { channel: "a", target_user: "" },
  twitch: { channel: "", target_user: "" },
  youtube: { channel: "", target_user: "" },
  kick: { channel: "", target_user: "", chatroom_id: null },
  show_logs: false,
  countdown_enabled: true,
  active_profile_id: "default",
  profiles: [
    {
      id: "default",
      name: "Domyślny",
      filters: { tiktok: "", twitch: "", youtube: "", kick: "" },
      mappings: [],
    },
  ],
};
afterEach(() => vi.useRealTimers());
it("keeps saved configuration on failed profile transaction", async () => {
  const api = {
    load: async () => ({ config, config_revision: 1 }),
    save: vi.fn(async () => {
      throw new Error("disk full");
    }),
    start: vi.fn(),
  };
  const ctrl = new ConfigController(api);
  await ctrl.reload();
  await expect(ctrl.mutate((c) => ({ ...c, show_logs: true }))).rejects.toThrow(
    "disk full",
  );
  expect(ctrl.state.draft).toEqual(config);
  expect(ctrl.state.revision).toBe(1);
  ctrl.dispose();
});
it("serializes saves and never overwrites newest draft with old response", async () => {
  const writes: any[] = [];
  let resolve!: (x: any) => void;
  const api = {
    load: async () => ({ config, config_revision: 1 }),
    save: vi.fn((c: any, r: number) => {
      writes.push([c, r]);
      return new Promise<any>((done) => {
        resolve = done;
      });
    }),
    start: vi.fn(async () => {}),
  };
  const ctrl = new ConfigController(api);
  await ctrl.reload();
  ctrl.edit({ ...config, tiktok: { channel: "A", target_user: "" } });
  const pending = ctrl.flush();
  ctrl.edit({ ...config, tiktok: { channel: "B", target_user: "" } });
  ctrl.edit({ ...config, tiktok: { channel: "C", target_user: "" } });
  resolve({ config: writes[0][0], config_revision: 2 });
  await Promise.resolve();
  await Promise.resolve();
  expect(ctrl.state.draft?.tiktok.channel).toBe("C");
  expect(writes[1][0].tiktok.channel).toBe("C");
  expect(writes[1][1]).toBe(2);
  resolve({ config: writes[1][0], config_revision: 3 });
  await pending;
  expect(ctrl.state.saveStatus).toBe("saved");
  ctrl.dispose();
});
it("debounces 500ms and blocks start after save error", async () => {
  vi.useFakeTimers();
  const api = {
    load: async () => ({ config, config_revision: 1 }),
    save: vi.fn(async () => {
      throw Object.assign(new Error("Konflikt"), { status: 409 });
    }),
    start: vi.fn(async () => {}),
  };
  const ctrl = new ConfigController(api);
  await ctrl.reload();
  ctrl.edit({ ...config, tiktok: { channel: "b", target_user: "" } });
  await vi.advanceTimersByTimeAsync(499);
  expect(api.save).not.toHaveBeenCalled();
  await vi.advanceTimersByTimeAsync(1);
  expect(api.save).toHaveBeenCalledTimes(1);
  expect(ctrl.state.conflict).toBe(true);
  await expect(ctrl.start()).rejects.toThrow();
  expect(api.start).not.toHaveBeenCalled();
  ctrl.dispose();
});
it("retains incomplete row locally without replacing saved mappings", async () => {
  const api = {
    load: async () => ({ config, config_revision: 1 }),
    save: vi.fn(),
    start: vi.fn(),
  };
  const ctrl = new ConfigController(api);
  await ctrl.reload();
  ctrl.edit({
    ...config,
    profiles: [
      { ...config.profiles[0], mappings: [{ id: "x", trigger: "", keys: [] }] },
    ],
  });
  await expect(ctrl.flush()).rejects.toThrow();
  expect(api.save).not.toHaveBeenCalled();
  expect(ctrl.state.draft?.profiles[0].mappings).toHaveLength(1);
  ctrl.dispose();
});

it("keeps an incomplete sequence draft and refuses autosave and Start", async () => {
  const api = {
    load: async () => ({ config, config_revision: 1 }),
    save: vi.fn(),
    start: vi.fn(),
  };
  const ctrl = new ConfigController(api);
  await ctrl.reload();
  const draft = {
    ...config,
    profiles: [
      {
        ...config.profiles[0],
        mappings: [
          {
            id: "m",
            trigger: "go",
            action: {
              steps: [{ type: "hold" as const, keys: ["a"], duration_ms: NaN }],
            },
          },
        ],
      },
    ],
  };
  ctrl.edit(draft);
  await expect(ctrl.start()).rejects.toThrow();
  expect(ctrl.state.draft).toBe(draft);
  expect(ctrl.state.saveStatus).toBe("invalid");
  expect(api.save).not.toHaveBeenCalled();
  expect(api.start).not.toHaveBeenCalled();
  ctrl.dispose();
});
