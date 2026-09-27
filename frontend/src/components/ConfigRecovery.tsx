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
        version: 2,
        streamer_id: "",
        target_user: "",
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
                if (value.version !== 2) {
                  value.version = 2;
                  value.mappings = (value.mappings ?? []).map((m: object) => ({
                    ...m,
                    id: crypto.randomUUID(),
                  }));
                }
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
