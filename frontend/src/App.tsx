import {
  t,
  useLanguage,
  setLanguage,
  statusLabel,
  type Language,
} from "./i18n";
import { sourceLabel } from "./api/platforms";
import { ThemeSwitcher } from "./components/ThemeSwitcher";
import { useEffect, useState, useSyncExternalStore, useRef } from "react";
import {
  bootstrapSession,
  configApi,
  fetchState,
  request,
  twitchAuthApi,
} from "./api/client";
import { subscribeEvents } from "./api/events";
import type {
  AppConfig,
  AppEvent,
  AppState,
  TwitchAuthState,
} from "./api/types";
import { ConfigController } from "./state/configController";
import { MappingEditor } from "./components/MappingEditor";
import { EventLog } from "./components/EventLog";
import { ConfigRecovery } from "./components/ConfigRecovery";
import { ChatSourceSettings } from "./components/ChatSourceSettings";
const saves: Record<string, string> = {
  saved: "Zapisano",
  dirty: "Niezapisane zmiany",
  saving: "Zapisywanie…",
  invalid: "Niepełny szkic",
  error: "Błąd zapisu",
};
export default function App() {
  const language = useLanguage();
  const [controller] = useState(() => new ConfigController(configApi));
  const editor = useSyncExternalStore(
    controller.subscribe,
    controller.snapshot,
  );
  const [auth, setAuth] = useState<TwitchAuthState | null>(null);
  const authRevision = useRef(0);
  const refreshAuth = async () => {
    const revision = ++authRevision.current;
    const result = await twitchAuthApi.state();
    if (revision === authRevision.current) setAuth(result);
  };
  const [state, setState] = useState<AppState | null>(null);
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState<AppEvent[]>([]);
  const [section, setSection] = useState("Pulpit");
  const [error, setError] = useState("");
  const [keys, setKeys] = useState<string[]>([]);
  const [presets, setPresets] = useState<
    Record<string, { trigger: string; keys: string[] }[]>
  >({});
  const [busy, setBusy] = useState(false);
  const [serverConfig, setServerConfig] = useState<AppConfig | null>(null);
  useEffect(() => {
    let stop: undefined | (() => void);
    let mounted = true;
    void (async () => {
      try {
        await bootstrapSession();
        const s = await fetchState();
        if (!mounted) return;
        setLanguage(s.language);
        setState(s);
        await refreshAuth();
        const [k, p] = await Promise.all([
          request<string[]>("/api/keys"),
          request<typeof presets>("/api/presets"),
        ]);
        if (!mounted) return;
        setKeys(k);
        setPresets(p);
        if (!s.config_error) await controller.reload();
        if (!mounted) return;
        stop = subscribeEvents(
          (snap) => {
            setLanguage(snap.state.language);
            setState(snap.state);
            void refreshAuth().catch(showError);
            setEvents(snap.events);
            if (snap.state.config_revision)
              void controller
                .remoteChanged(snap.state.config_revision)
                .catch(showError);
          },
          (event) => {
            if (event.type === "preferences_changed") {
              setLanguage(event.payload.language as Language);
            }
            setEvents((list) => [...list, event].slice(-1000));
            if (event.type === "twitch_auth") {
              ++authRevision.current;
              setAuth(event.payload as unknown as TwitchAuthState);
            }
            if (event.type === "status")
              setState((s) => (s ? { ...s, ...event.payload } : s));
            if (event.type === "config_changed") {
              const revision = event.payload.config_revision as number;
              setState((s) => (s ? { ...s, config_revision: revision } : s));
              void controller.remoteChanged(revision).catch(showError);
            }
          },
          setConnected,
        );
      } catch (e) {
        if (mounted) showError(e);
      }
    })();
    return () => {
      mounted = false;
      ++authRevision.current;
      stop?.();
      controller.dispose();
    };
  }, [controller]);
  const showError = (e: unknown) =>
    setError(
      e instanceof Error ? e.message : "Nie udało się wykonać operacji.",
    );
  const edit = (patch: Partial<AppConfig>) => {
    if (editor.draft) controller.edit({ ...editor.draft, ...patch });
  };
  const action = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (e) {
      showError(e);
    } finally {
      setBusy(false);
    }
  };
  const running =
    state && ["connecting", "connected", "stopping"].includes(state.status);
  const pending = running && state.active_config_revision !== editor.revision;
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#" onClick={(e) => e.preventDefault()}>
          <span className="brand-icon">t</span>
          <span>
            Tiko<span className="brand-light">Play</span>
          </span>
        </a>
        <div className="sidebar-caption">{t("TWÓJ PANEL STEROWANIA")}</div>
        <nav>
          {[
            ["Pulpit", "◫"],
            ["Mapowania", "⌨"],
            ["Ustawienia", "⚙"],
          ].map(([name, icon]) => (
            <button
              key={name}
              className={section === name ? "active" : ""}
              onClick={() => setSection(name)}
            >
              <span>{icon}</span>
              {t(name)}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <span className={"dot " + (connected ? "on" : "")} />
          <div>
            {t("Lokalna aplikacja")}
            <small>
              {connected
                ? t("Działa na tym komputerze")
                : t("Łączenie z TikoPlay…")}
            </small>
          </div>
        </div>
        <span className="version">{t("TikoPlay 2.0 · Web panel")}</span>
      </aside>
      <main>
        <header>
          <div>
            <span className="eyebrow">{t("CZAT → TWOJA GRA")}</span>
            <h1>{t(section)}</h1>
            <p>{t("Oddaj stery swojej społeczności.")}</p>
          </div>
          <div className="header-actions">
            <ThemeSwitcher />
            <div className="save-indicator">
              <span
                className={"dot " + (editor.saveStatus === "saved" ? "on" : "")}
              />
              {t(saves[editor.saveStatus])}
            </div>
          </div>
        </header>
        {error && (
          <div className="notice error" role="alert">
            {t(error)}
          </div>
        )}
        {!connected && state && (
          <div className="notice">
            {t(
              "Utracono połączenie z TikoPlay. Nasłuch może nadal działać. Jeśli program został zamknięty, otwórz go ponownie z ikony.",
            )}
          </div>
        )}
        {state?.error && (
          <div className="notice error" role="alert">
            {t(state.error.message)}
          </div>
        )}
        {editor.error && (
          <div className="notice error" role="alert">
            {t(editor.error)}
            {editor.conflict && (
              <div className="conflict-actions">
                <button
                  onClick={() =>
                    void configApi
                      .load()
                      .then((s) => setServerConfig(s.config))
                      .catch(showError)
                  }
                >
                  {t("Porównaj z serwerem")}
                </button>
                <button
                  onClick={() => {
                    if (
                      confirm(
                        t(
                          "Odrzucić lokalny szkic i wczytać zapisane ustawienia?",
                        ),
                      )
                    )
                      void controller.reload().catch(showError);
                  }}
                >
                  {t("Wczytaj zapisane ustawienia")}
                </button>
              </div>
            )}
            {serverConfig && <pre>{JSON.stringify(serverConfig, null, 2)}</pre>}
          </div>
        )}
        {state?.config_error ? (
          <ConfigRecovery state={state} onRecovered={() => location.reload()} />
        ) : editor.draft ? (
          <>
            <section className="connection-card">
              <div className="connection-title">
                <span
                  className={
                    "status-orb " +
                    (connected && state?.status === "connected" ? "live" : "")
                  }
                >
                  ◉
                </span>
                <div>
                  <h2>
                    {!connected
                      ? t("Stan nasłuchu nieznany")
                      : state
                        ? statusLabel(state.status)
                        : t("Łączenie z aplikacją…")}
                  </h2>
                  {running && connected && state?.active_platform && (
                    <p className="active-source">
                      {t("Aktywne źródło:")}{" "}
                      {sourceLabel(
                        state.active_platform,
                        state.active_channel ?? "",
                      )}
                    </p>
                  )}
                  <p>
                    {!connected
                      ? t(
                          "Brak aktualnego stanu. Otwórz TikoPlay z ikony lub poczekaj na ponowne połączenie.",
                        )
                      : state?.output === "countdown"
                        ? t(
                            "Przełącz się do gry. Klawisze zostaną włączone po 3 sekundach.",
                          )
                        : state?.output === "enabled"
                          ? t("Wysyłanie klawiszy jest aktywne.")
                          : t("Nasłuch gotowy do uruchomienia.")}
                  </p>
                </div>
              </div>
              <button
                className={running ? "stop-button" : "primary start-button"}
                disabled={
                  !connected ||
                  busy ||
                  state?.status === "stopping" ||
                  (!running &&
                    (!editor.draft[editor.draft.platform].channel.trim() ||
                      (editor.draft.platform === "twitch" &&
                        auth?.status !== "connected") ||
                      editor.saveStatus === "error" ||
                      editor.conflict ||
                      editor.saveStatus === "invalid"))
                }
                onClick={() =>
                  void action(() =>
                    running
                      ? request("/api/listener/stop", "POST")
                      : controller.start(),
                  )
                }
              >
                {running ? t("■ Zatrzymaj nasłuch") : t("▶ Rozpocznij nasłuch")}
              </button>
            </section>
            {pending && (
              <div className="notice">
                {t(
                  "Zapisano nowe ustawienia. Zatrzymaj i ponownie uruchom nasłuch, aby je zastosować.",
                )}
              </div>
            )}
            {section === "Pulpit" && (
              <>
                <div className="two-columns">
                  <ChatSourceSettings
                    config={editor.draft}
                    onChange={edit}
                    auth={auth}
                    onAuthChanged={refreshAuth}
                  />
                  <section className="card how-it-works">
                    <span className="eyebrow">{t("JAK TO DZIAŁA")}</span>
                    <h2>{t("Od komentarza do ruchu")}</h2>
                    <div className="flow-example">
                      <span>{t("„lewo”")}</span>
                      <b>→</b>
                      <kbd>←</kbd>
                    </div>
                    <p>
                      {t(
                        "Ustaw mapowania, rozpocznij nasłuch i przełącz się do gry. Resztą zajmą się Twoi widzowie.",
                      )}
                    </p>
                    <label className="check">
                      <input
                        type="checkbox"
                        checked={editor.draft.countdown_enabled}
                        onChange={(e) =>
                          edit({ countdown_enabled: e.target.checked })
                        }
                      />
                      <span>{t("3 sekundy na przełączenie do gry")}</span>
                    </label>
                    <div className="info-box">
                      {t(
                        "Klawisze trafiają do aktywnego okna. Zamknięcie tej karty nie zatrzymuje programu.",
                      )}
                    </div>
                  </section>
                </div>
                <div className="summary-line">
                  <span>
                    <strong>{editor.draft.mappings.length}</strong>{" "}
                    {t("mapowań gotowych do gry")}
                  </span>
                  <button onClick={() => setSection("Mapowania")}>
                    {t("Edytuj mapowania →")}
                  </button>
                </div>
              </>
            )}
            {section === "Mapowania" && (
              <MappingEditor
                mappings={editor.draft.mappings}
                onChange={(mappings) => edit({ mappings })}
                presets={presets}
                keys={keys}
              />
            )}
            {section === "Ustawienia" && (
              <section className="card">
                <span className="eyebrow">{t("PREFERENCJE")}</span>
                <h2>{t("Ustawienia aplikacji")}</h2>
                <label className="language-setting">
                  {t("Język")}
                  <select
                    value={language}
                    disabled={busy || !connected}
                    onChange={(e) => {
                      const next = e.target.value as Language;
                      void action(async () => {
                        const result = await request<{ language: Language }>(
                          "/api/preferences",
                          "PUT",
                          { language: next },
                        );
                        setLanguage(result.language);
                      });
                    }}
                  >
                    <option value="pl">Polski</option>
                    <option value="en">English</option>
                  </select>
                </label>
                <label className="check">
                  <input
                    type="checkbox"
                    checked={editor.draft.show_logs}
                    onChange={(e) => edit({ show_logs: e.target.checked })}
                  />
                  {t("Pokazuj panel aktywności")}
                </label>
                <label className="check">
                  <input
                    type="checkbox"
                    checked={editor.draft.countdown_enabled}
                    onChange={(e) =>
                      edit({ countdown_enabled: e.target.checked })
                    }
                  />
                  {t("Odliczanie przed wysyłaniem klawiszy")}
                </label>
                <div className="info-box">
                  {t(
                    "TikoPlay działa lokalnie w tle. Aby zakończyć program, wybierz „Zakończ TikoPlay” z ikony w zasobniku systemowym. Ustawienia są zapisywane automatycznie.",
                  )}
                </div>
                <p className="hint">
                  {t("Wersja 2.0.0 · Cooldown: 0,3 s na komentarz")}
                </p>
              </section>
            )}
            {editor.draft.show_logs && (
              <EventLog events={events} onClear={() => setEvents([])} />
            )}
            <footer>
              <span>{t("Ustawienia zapisują się automatycznie.")}</span>
              <button
                disabled={busy || !connected || editor.conflict}
                onClick={() => void action(() => controller.flush())}
              >
                {t("Zapisz teraz")}
              </button>
            </footer>
          </>
        ) : (
          <section className="card">
            <h2>{t("Uruchamianie panelu…")}</h2>
            <p>
              {t(
                "Jeśli panel się nie połączy, otwórz go ponownie z ikony TikoPlay.",
              )}
            </p>
          </section>
        )}
      </main>
    </div>
  );
}
