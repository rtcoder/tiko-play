import { useState } from "react";
import { request } from "../api/client";
import type { AppState } from "../api/types";
export function ConfigRecovery({
  state,
  onRecovered,
}: {
  state: AppState;
  onRecovered: () => void;
}) {
  const [text, setText] = useState(
    JSON.stringify(
      state.recovery_data ?? {
        version: 4,
        platform: "tiktok",
        tiktok: { channel: "", target_user: "" },
        twitch: { channel: "", target_user: "" },
        youtube: { channel: "", target_user: "" },
        kick: { channel: "", target_user: "", chatroom_id: null },
        mappings: [],
        show_logs: false,
        countdown_enabled: true,
      },
      null,
      2,
    ),
  );
  const [error, setError] = useState("");
  return (
    <section className="card">
      <h2>Konfiguracja wymaga uwagi</h2>
      <p>{state.config_error?.message}</p>
      {state.config_error?.code === "future_version" ? (
        <p>
          Zainstaluj wersję TikoPlay obsługującą ten plik. Oryginalne dane
          pozostały nienaruszone.
        </p>
      ) : (
        <>
          <p>
            Popraw ustawienia poniżej. Przed naprawą TikoPlay zachowa kopię
            oryginalnego pliku.
          </p>
          <textarea
            aria-label="Konfiguracja do naprawy"
            rows={14}
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <button
            className="primary"
            onClick={async () => {
              try {
                const value = JSON.parse(text);
                if (![undefined, 1, 2, 3, 4].includes(value.version))
                  throw new Error("Nieobsługiwana wersja konfiguracji.");
                if ([undefined, 1, 2].includes(value.version)) {
                  value.version = 3;
                  value.platform = "tiktok";
                  value.tiktok = {
                    channel: value.streamer_id ?? "",
                    target_user: value.target_user ?? "",
                  };
                  value.twitch = { channel: "", target_user: "" };
                  delete value.streamer_id;
                  delete value.target_user;
                  value.mappings = (value.mappings ?? []).map(
                    (m: { id?: string }) => ({
                      ...m,
                      id: m.id ?? crypto.randomUUID(),
                    }),
                  );
                }
                value.version = 4;
                value.youtube ??= { channel: "", target_user: "" };
                value.kick ??= {
                  channel: "",
                  target_user: "",
                  chatroom_id: null,
                };
                await request("/api/config/repair", "POST", value);
                onRecovered();
              } catch (e) {
                setError(e instanceof Error ? e.message : "Błąd naprawy");
              }
            }}
          >
            Zachowaj kopię i napraw
          </button>
        </>
      )}
      {error && <p role="alert">{error}</p>}
    </section>
  );
}
