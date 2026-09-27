import { useEffect, useState, useSyncExternalStore } from "react";
import { bootstrapSession, configApi, fetchState, request } from "./api/client";
import { subscribeEvents } from "./api/events";
import type { AppConfig, AppEvent, AppState } from "./api/types";
import { ConfigController } from "./state/configController";
import { MappingEditor } from "./components/MappingEditor";
import { EventLog } from "./components/EventLog";
import { ConfigRecovery } from "./components/ConfigRecovery";
const labels: Record<string, string> = {
  stopped: "Zatrzymany",
  connecting: "Łączenie…",
  connected: "Połączony",
  stopping: "Zatrzymywanie…",
  error: "Błąd połączenia",
};
const saves: Record<string, string> = {
  saved: "Zapisano",
  dirty: "Niezapisane zmiany",
  saving: "Zapisywanie…",
  invalid: "Niepełny szkic",
  error: "Błąd zapisu",
};
export default function App() {
  const [controller] = useState(() => new ConfigController(configApi));
  const editor = useSyncExternalStore(
    controller.subscribe,
    controller.snapshot,
  );
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
        setState(s);
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
            setState(snap.state);
            setEvents(snap.events);
            if (snap.state.config_revision)
              void controller
                .remoteChanged(snap.state.config_revision)
                .catch(showError);
          },
          (event) => {
            setEvents((list) => [...list, event].slice(-1000));
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
        <div className="sidebar-caption">TWÓJ PANEL STEROWANIA</div>
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
              {name}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <span className={"dot " + (connected ? "on" : "")} />
          <div>
            Lokalna aplikacja
            <small>
              {connected ? "Działa na tym komputerze" : "Łączenie z TikoPlay…"}
            </small>
          </div>
        </div>
        <span className="version">TikoPlay 2.0 · Web panel</span>
      </aside>
      <main>
        <header>
          <div>
            <span className="eyebrow">TIKTOK LIVE → TWOJA GRA</span>
            <h1>{section}</h1>
            <p>Oddaj stery swojej społeczności.</p>
          </div>
          <div className="save-indicator">
            <span
              className={"dot " + (editor.saveStatus === "saved" ? "on" : "")}
            />
            {saves[editor.saveStatus]}
          </div>
        </header>
        {error && (
          <div className="notice error" role="alert">
            {error}
          </div>
        )}
        {!connected && state && (
          <div className="notice">
            Utracono połączenie z TikoPlay. Nasłuch może nadal działać. Jeśli
            program został zamknięty, otwórz go ponownie z ikony.
          </div>
        )}
        {state?.error && (
          <div className="notice error" role="alert">
            {state.error.message}
          </div>
        )}
        {editor.error && (
          <div className="notice error" role="alert">
            {editor.error}
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
                  Porównaj z serwerem
                </button>
                <button
                  onClick={() => {
                    if (
                      confirm(
                        "Odrzucić lokalny szkic i wczytać zapisane ustawienia?",
                      )
                    )
                      void controller.reload().catch(showError);
                  }}
                >
                  Wczytaj zapisane ustawienia
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
                      ? "Stan nasłuchu nieznany"
                      : state
                        ? labels[state.status]
                        : "Łączenie z aplikacją…"}
                  </h2>
                  <p>
                    {!connected
                      ? "Brak aktualnego stanu. Otwórz TikoPlay z ikony lub poczekaj na ponowne połączenie."
                      : state?.output === "countdown"
                        ? "Przełącz się do gry. Klawisze zostaną włączone po 3 sekundach."
                        : state?.output === "enabled"
                          ? "Wysyłanie klawiszy jest aktywne."
                          : "Nasłuch gotowy do uruchomienia."}
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
                    (!editor.draft.streamer_id.trim() ||
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
                {running ? "■ Zatrzymaj nasłuch" : "▶ Rozpocznij nasłuch"}
              </button>
            </section>
            {pending && (
              <div className="notice">
                Zapisano nowe ustawienia. Zatrzymaj i ponownie uruchom nasłuch,
                aby je zastosować.
              </div>
            )}
            {section === "Pulpit" && (
              <>
                <div className="two-columns">
                  <section className="card">
                    <span className="eyebrow">POŁĄCZENIE</span>
                    <h2>Twoja transmisja</h2>
                    <label>
                      Nick streamera
                      <div className="with-prefix">
                        <span>@</span>
                        <input
                          placeholder="nazwa_streamera"
                          value={editor.draft.streamer_id}
                          onChange={(e) =>
                            edit({ streamer_id: e.target.value })
                          }
                        />
                      </div>
                    </label>
                    <p className="hint">
                      Wpisz nick konta prowadzącego TikTok LIVE.
                    </p>
                    <label>
                      Dozwolony użytkownik{" "}
                      <span className="optional">opcjonalnie</span>
                      <input
                        placeholder="Wszyscy widzowie"
                        value={editor.draft.target_user}
                        onChange={(e) => edit({ target_user: e.target.value })}
                      />
                    </label>
                    <p className="hint">
                      Dokładny identyfikator użytkownika bez @. Puste pole
                      dopuszcza wszystkich.
                    </p>
                  </section>
                  <section className="card how-it-works">
                    <span className="eyebrow">JAK TO DZIAŁA</span>
                    <h2>Od komentarza do ruchu</h2>
                    <div className="flow-example">
                      <span>„lewo”</span>
                      <b>→</b>
                      <kbd>←</kbd>
                    </div>
                    <p>
                      Ustaw mapowania, rozpocznij nasłuch i przełącz się do gry.
                      Resztą zajmą się Twoi widzowie.
                    </p>
                    <label className="check">
                      <input
                        type="checkbox"
                        checked={editor.draft.countdown_enabled}
                        onChange={(e) =>
                          edit({ countdown_enabled: e.target.checked })
                        }
                      />
                      <span>3 sekundy na przełączenie do gry</span>
                    </label>
                    <div className="info-box">
                      Klawisze trafiają do aktywnego okna. Zamknięcie tej karty
                      nie zatrzymuje programu.
                    </div>
                  </section>
                </div>
                <div className="summary-line">
                  <span>
                    <strong>{editor.draft.mappings.length}</strong> mapowań
                    gotowych do gry
                  </span>
                  <button onClick={() => setSection("Mapowania")}>
                    Edytuj mapowania →
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
                <span className="eyebrow">PREFERENCJE</span>
                <h2>Ustawienia aplikacji</h2>
                <label className="check">
                  <input
                    type="checkbox"
                    checked={editor.draft.show_logs}
                    onChange={(e) => edit({ show_logs: e.target.checked })}
                  />
                  Pokazuj panel aktywności
                </label>
                <label className="check">
                  <input
                    type="checkbox"
                    checked={editor.draft.countdown_enabled}
                    onChange={(e) =>
                      edit({ countdown_enabled: e.target.checked })
                    }
                  />
                  Odliczanie przed wysyłaniem klawiszy
                </label>
                <div className="info-box">
                  TikoPlay działa lokalnie w tle. Aby zakończyć program, wybierz
                  „Zakończ TikoPlay” z ikony w zasobniku systemowym. Ustawienia
                  są zapisywane automatycznie.
                </div>
                <p className="hint">
                  Wersja 2.0.0 · Cooldown: 0,3 s na komentarz
                </p>
              </section>
            )}
            {editor.draft.show_logs && (
              <EventLog events={events} onClear={() => setEvents([])} />
            )}
            <footer>
              <span>Ustawienia zapisują się automatycznie.</span>
              <button
                disabled={busy || !connected || editor.conflict}
                onClick={() => void action(() => controller.flush())}
              >
                Zapisz teraz
              </button>
            </footer>
          </>
        ) : (
          <section className="card">
            <h2>Uruchamianie panelu…</h2>
            <p>
              Jeśli panel się nie połączy, otwórz go ponownie z ikony TikoPlay.
            </p>
          </section>
        )}
      </main>
    </div>
  );
}
