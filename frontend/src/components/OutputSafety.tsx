import { useEffect, useState } from "react";
import { request } from "../api/client";
import { t } from "../i18n";
export interface Target {
  app: string;
  pid: number;
  started: string;
  name: string;
}
export interface SafetyState {
  enabled: boolean;
  target: Target | null;
  targets: Target[];
  error: string | null;
  hotkey: { key: string; active: boolean; error: string | null };
}
const identity = (target: Target) =>
  JSON.stringify([target.app, target.pid, target.started]);
export function OutputSafety({
  running,
  connected,
  output,
}: {
  running: boolean;
  connected: boolean;
  output: string;
}) {
  const [state, setState] = useState<SafetyState | null>(null);
  const [enabled, setEnabled] = useState(false);
  const [target, setTarget] = useState("");
  const [key, setKey] = useState("F10");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const apply = (data: SafetyState) => {
    setState(data);
    setEnabled(data.enabled);
    setTarget(data.target ? identity(data.target) : "");
    setKey(data.hotkey.key);
  };
  useEffect(() => {
    let active = true;
    if (connected)
      void request<SafetyState>("/api/output-safety")
        .then((data) => {
          if (active) apply(data);
        })
        .catch((e) => {
          if (active) setError(e.message);
        });
    return () => {
      active = false;
    };
  }, [connected, running]);
  const load = async () => {
    setBusy(true);
    setError("");
    try {
      apply(await request<SafetyState>("/api/output-safety"));
      setSaved(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Błąd odczytu");
    } finally {
      setBusy(false);
    }
  };
  const save = async () => {
    setBusy(true);
    setError("");
    setSaved(false);
    try {
      const data = await request<SafetyState>("/api/output-safety", "PUT", {
        enabled,
        target: state?.targets.find((row) => identity(row) === target) ?? null,
        key,
      });
      apply(data);
      setSaved(!data.hotkey.error);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Błąd zapisu");
    } finally {
      setBusy(false);
    }
  };
  return (
    <section className="card output-safety">
      <h2>{t("Klawisze tylko do wybranej gry")}</h2>
      <p>
        {t(
          "Po przełączeniu do innej aplikacji sterowanie zostaje wstrzymane. Powrót do gry nie włącza go automatycznie.",
        )}
      </p>
      {error && (
        <p className="notice error" role="alert">
          {t(error)}
        </p>
      )}
      {state?.error && <p className="notice error">{t(state.error)}</p>}
      <fieldset
        className="editor-fields"
        disabled={busy || running || !connected || !state}
      >
        <label className="check">
          <input
            type="checkbox"
            checked={enabled}
            onChange={(e) => {
              setEnabled(e.target.checked);
              setSaved(false);
            }}
          />
          {t("Chroń wybraną aplikację")}
        </label>
        <label>
          {t("Uruchomiona gra lub aplikacja")}
          <select
            value={target}
            onChange={(e) => {
              setTarget(e.target.value);
              setSaved(false);
            }}
          >
            <option value="">{t("Wybierz z listy…")}</option>
            {state?.targets.map((row) => (
              <option key={identity(row)} value={identity(row)}>
                {row.name} · PID {row.pid}
              </option>
            ))}
            {state?.target &&
              !state.targets.some(
                (row) => identity(row) === identity(state.target!),
              ) && (
                <option value={identity(state.target)}>
                  {state.target.name} — {t("proces zakończony")}
                </option>
              )}
          </select>
        </label>
        <button type="button" onClick={() => void load()}>
          {t("Odśwież listę aplikacji")}
        </button>
        <p className="hint">
          {t(
            "Uruchom grę przed wyborem. Po jej restarcie wybierz proces ponownie. Ochrona dotyczy całej aplikacji, nie rozróżnia jej okien ani dialogów.",
          )}
        </p>
        <h3>{t("Awaryjny STOP z dowolnej aplikacji")}</h3>
        <label>
          {t("Skrót STOP")}
          <select
            value={key}
            onChange={(e) => {
              setKey(e.target.value);
              setSaved(false);
            }}
          >
            {["F9", "F10", "F11"].map((k) => (
              <option key={k} value={k}>
                Ctrl + Alt + Shift + {k}
              </option>
            ))}
          </select>
        </label>
        <button
          className="primary"
          onClick={() => void save()}
          disabled={
            enabled && !state?.targets.some((row) => identity(row) === target)
          }
        >
          {t("Zastosuj ochronę i skrót")}
        </button>
      </fieldset>
      {state && (
        <p role="status">
          {state.hotkey.active
            ? t("Aktywny STOP: Ctrl + Alt + Shift + {key}", {
                key: state.hotkey.key,
              })
            : t("Skrót STOP nie jest aktywny.")}
        </p>
      )}
      {state?.hotkey.error && (
        <p className="notice error" role="alert">
          {t(state.hotkey.error)}
        </p>
      )}
      {saved && <p role="status">{t("Zastosowano ustawienia ochrony.")}</p>}
      {running && (
        <p className="hint">{t("Zatrzymaj nasłuch przed zmianą ochrony.")}</p>
      )}
      {output === "paused_focus" && (
        <p className="notice">
          {t(
            "Utracono fokus gry. Kolejka została wyczyszczona. Kliknij Wznów sterowanie, a potem przełącz się do gry.",
          )}
        </p>
      )}
      <p className="hint">
        {t(
          "Ustawienia dotyczą bieżącego uruchomienia TikoPlay. Po ponownym otwarciu wybierz grę i włącz ochronę. Skrót domyślny: Ctrl + Alt + Shift + F10.",
        )}
      </p>
      <p className="hint">
        {t(
          "Odczyt fokusu i wysłanie klawisza nie są jedną operacją systemową. Ochrona ogranicza ryzyko, ale nie gwarantuje zablokowania każdego wejścia w chwili przełączenia okna.",
        )}
      </p>
    </section>
  );
}
