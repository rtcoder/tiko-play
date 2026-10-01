import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { it, expect, vi } from "vitest";
import { ConfigRecovery } from "./ConfigRecovery";
import { request } from "../api/client";
import type { AppState } from "../api/types";
vi.mock("../api/client", () => ({ request: vi.fn() }));
it.each([6, 7])(
  "repairs schema %s without losing profile limits",
  async (version) => {
    const data = {
      version,
      active_profile_id: "p",
      profiles: [
        {
          id: "p",
          name: "Game",
          mappings: [],
          limits: { viewer_cooldown_ms: 1000 },
        },
      ],
    };
    const done = vi.fn();
    vi.mocked(request).mockReset().mockResolvedValue({});
    render(
      <ConfigRecovery
        state={
          {
            recovery_data: data,
            config_error: { code: "configuration_error", message: "invalid" },
          } as AppState
        }
        onRecovered={done}
      />,
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Zachowaj kopię i napraw" }),
    );
    await waitFor(() =>
      expect(request).toHaveBeenCalledWith(
        "/api/config/repair",
        "POST",
        expect.objectContaining({
          version: 7,
          profiles: data.profiles,
          active_profile_id: "p",
        }),
      ),
    );
    expect(done).toHaveBeenCalledOnce();
  },
);
