import { t } from "../i18n";
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
        version: 7,
        active_profile_id: "default",
        profiles: [
          {
            id: "default",
            name: "Domyślny",
            mappings: [],
            filters: { tiktok: "", twitch: "", youtube: "", kick: "" },
          },
        ],
        platform: "tiktok",
        tiktok: { channel: "", target_user: "" },
        twitch: { channel: "", target_user: "" },
        youtube: { channel: "", target_user: "" },
        kick: { channel: "", target_user: "", chatroom_id: null },
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
      <h2>{t("Konfiguracja wymaga uwagi")}</h2>
      <p>{state.config_error && t(state.config_error.message)}</p>
      {state.config_error?.code === "future_version" ? (
        <p>
          {t(
            "Zainstaluj wersję TikoPlay obsługującą ten plik. Oryginalne dane pozostały nienaruszone.",
          )}
        </p>
      ) : (
        <>
          <p>
            {t(
              "Popraw ustawienia poniżej. Przed naprawą TikoPlay zachowa kopię oryginalnego pliku.",
            )}
          </p>
          <textarea
            aria-label={t("Konfiguracja do naprawy")}
            rows={14}
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <button
            className="primary"
            onClick={async () => {
              try {
                const value = JSON.parse(text);
                if (![undefined, 1, 2, 3, 4, 5, 6, 7].includes(value.version))
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
                if (![5, 6, 7].includes(value.version)) {
                  const id = crypto.randomUUID();
                  value.profiles = [
                    {
                      id,
                      name: "Domyślny",
                      mappings: value.mappings ?? [],
                      filters: {
                        tiktok: value.tiktok?.target_user ?? "",
                        twitch: value.twitch?.target_user ?? "",
                        youtube: value.youtube?.target_user ?? "",
                        kick: value.kick?.target_user ?? "",
                      },
                    },
                  ];
                  value.active_profile_id = id;
                  delete value.mappings;
                }
                value.version = 7;
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
            {t("Zachowaj kopię i napraw")}
          </button>
        </>
      )}
      {error && <p role="alert">{t(error)}</p>}
    </section>
  );
}
