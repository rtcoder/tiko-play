import { useEffect, useState } from "react";
import { request } from "../api/client";
import { t } from "../i18n";
import { OverlayView } from "../overlay/Overlay";
import type {
  OverlaySettings as Settings,
  OverlayState,
} from "../overlay/types";

export function OverlaySettings({ connected }: { connected: boolean }) {
  const [state, setState] = useState<OverlayState | null>(null);
  const [draft, setDraft] = useState<Settings | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  useEffect(() => {
    let alive = true;
    request<OverlayState>("/api/overlay")
      .then((s) => {
        if (alive) {
          setState(s);
          setDraft(s.settings);
        }
      })
      .catch((e) => {
        if (alive) setError(e.message);
      });
    return () => {
      alive = false;
    };
  }, []);
  const act = async (method: string, path = "/api/overlay") => {
    setBusy(true);
    setError("");
    setCopied(false);
    try {
      const s = await request<OverlayState>(
        path,
        method,
        path.endsWith("/rotate") ? undefined : draft,
      );
      setState(s);
      if (method === "PUT") setDraft(s.settings);
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Nie udało się wykonać operacji.",
      );
    } finally {
      setBusy(false);
    }
  };
  const change = (patch: Partial<Settings>) =>
    setDraft((d) => (d ? { ...d, ...patch } : d));
  return (
    <div className="overlay-settings">
      <section className="card">
        <span className="eyebrow">{t("CZAT NA TRANSMISJI")}</span>
        <h2>{t("Dodaj sterowanie do obrazu")}</h2>
        <p>
          {t(
            "Widzowie zobaczą dostępne komendy i ostatni wykonany ruch. Nakładka ma przezroczyste tło.",
          )}
        </p>
        {error && (
          <div className="notice error" role="alert">
            {t(error)}
          </div>
        )}
        {state?.error && (
          <div className="notice error" role="alert">
            {t(state.error)}
          </div>
        )}
        {draft &&
          state &&
          JSON.stringify(draft) !== JSON.stringify(state.settings) && (
            <p className="notice" role="status">
              {t("Nakładka ma niezapisane zmiany.")}
            </p>
          )}
        {!draft && <p>{t("Wczytywanie ustawień…")}</p>}
        {draft && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void act("PUT");
            }}
          >
            <fieldset className="editor-fields" disabled={busy || !connected}>
              <label className="check">
                <input
                  type="checkbox"
                  checked={draft.enabled}
                  onChange={(e) => change({ enabled: e.target.checked })}
                />
                {t("Włącz nakładkę")}
              </label>
              <div className="overlay-setup">
                <label>
                  {t("Port nakładki")}
                  <input
                    type="number"
                    required
                    min={1024}
                    max={65535}
                    step={1}
                    value={Number.isNaN(draft.port) ? "" : draft.port}
                    onChange={(e) => change({ port: e.target.valueAsNumber })}
                  />
                </label>
                <button type="submit" className="primary">
                  {busy ? t("Zapisywanie…") : t("Zapisz i zastosuj")}
                </button>
              </div>
              <p className="hint">
                {t(
                  "Domyślnie 18765. Zmień tylko, gdy port jest zajęty. Po zmianie portu wklej nowy adres do OBS.",
                )}
              </p>
              <details className="overlay-customize">
                <summary>{t("Dostosuj wygląd")}</summary>
                <div className="overlay-options">
                  <label className="check">
                    <input
                      type="checkbox"
                      checked={draft.show_commands}
                      onChange={(e) =>
                        change({ show_commands: e.target.checked })
                      }
                    />
                    {t("Pokaż dostępne komendy")}
                  </label>
                  <label className="check">
                    <input
                      type="checkbox"
                      checked={draft.show_last_action}
                      onChange={(e) =>
                        change({ show_last_action: e.target.checked })
                      }
                    />
                    {t("Pokaż ostatni ruch")}
                  </label>
                  <label className="check">
                    <input
                      type="checkbox"
                      checked={draft.show_actor}
                      onChange={(e) => change({ show_actor: e.target.checked })}
                    />
                    {t("Pokaż nick autora")}
                  </label>
                  <label className="check">
                    <input
                      type="checkbox"
                      checked={draft.show_status}
                      onChange={(e) =>
                        change({ show_status: e.target.checked })
                      }
                    />
                    {t("Pokaż stan sterowania")}
                  </label>
                  <label>
                    {t("Rozmiar tekstu (px)")}
                    <input
                      type="number"
                      required
                      min={16}
                      max={48}
                      step={1}
                      value={
                        Number.isNaN(draft.font_size) ? "" : draft.font_size
                      }
                      onChange={(e) =>
                        change({ font_size: e.target.valueAsNumber })
                      }
                    />
                  </label>
                  <label>
                    {t("Kolor akcentu")}
                    <input
                      type="color"
                      value={draft.accent}
                      onChange={(e) => change({ accent: e.target.value })}
                    />
                  </label>
                </div>
                <p className="hint">
                  {t(
                    "Nick jest domyślnie ukryty. Włącz go, jeśli chcesz pokazywać autorów ruchów na transmisji.",
                  )}
                </p>
              </details>
            </fieldset>
          </form>
        )}
        {state?.running && state.url && (
          <div className="overlay-address">
            <label>
              {t("Adres do OBS")}
              <input
                readOnly
                value={state.url}
                onFocus={(e) => e.target.select()}
              />
            </label>
            <div className="overlay-address-actions">
              <button
                className="primary"
                type="button"
                onClick={() => {
                  void navigator.clipboard
                    .writeText(state.url!)
                    .then(() => setCopied(true))
                    .catch(() =>
                      setError(
                        "Nie można skopiować adresu. Zaznacz go i skopiuj ręcznie.",
                      ),
                    );
                }}
              >
                {copied ? t("Skopiowano") : t("Kopiuj adres")}
              </button>
              <a href={state.url} target="_blank" rel="noreferrer">
                {t("Otwórz nakładkę ↗")}
              </a>
            </div>
            <ol className="overlay-instructions">
              <li>{t("W OBS dodaj źródło „Przeglądarka”.")}</li>
              <li>
                {t("Wklej adres powyżej. Ustaw szerokość 900 i wysokość 600.")}
              </li>
              <li>
                {t(
                  "Umieść źródło nad obrazem gry. TikoPlay musi działać w tle.",
                )}
              </li>
            </ol>
            <details className="overlay-customize">
              <summary>{t("Zmień adres nakładki")}</summary>
              <p className="hint">
                {t(
                  "Unieważnia poprzedni link i rozłącza korzystające z niego źródła. Nowy adres trzeba wkleić do OBS.",
                )}
              </p>
              <button
                type="button"
                disabled={busy || !connected}
                onClick={() => void act("POST", "/api/overlay/rotate")}
              >
                {t("Wygeneruj nowy adres")}
              </button>
            </details>
          </div>
        )}
        {state && !state.running && (
          <div className="info-box">
            {t(
              "Włącz nakładkę i zapisz ustawienia, aby otrzymać adres do OBS.",
            )}
          </div>
        )}
      </section>
      {draft && (
        <section className="card overlay-preview-card">
          <h2>{t("Podgląd wyglądu")}</h2>
          <p className="hint">
            {t(
              "Przykładowe dane. Zapisz ustawienia, aby zmienić nakładkę na transmisji.",
            )}
          </p>
          <div className="overlay-preview">
            <OverlayView
              status="connected"
              snapshot={{
                schema_version: 1,
                sequence: 0,
                mode: "direct",
                paused: false,
                language: "pl",
                presentation: {
                  ...draft,
                  font_size: Number.isNaN(draft.font_size)
                    ? 24
                    : draft.font_size,
                },
                commands: [
                  {
                    comment: "8",
                    action: { steps: [{ type: "press", keys: ["up"] }] },
                  },
                  {
                    comment: "2",
                    action: { steps: [{ type: "press", keys: ["down"] }] },
                  },
                ],
                last_action: {
                  id: 1,
                  comment: "8",
                  actor: "widz",
                  action: { steps: [{ type: "press", keys: ["up"] }] },
                },
              }}
            />
          </div>
        </section>
      )}
    </div>
  );
}
