import { useState } from "react";
import { request } from "../api/client";
import type {
  AppConfig,
  Platform,
  SimulationMessage,
  SimulationReport,
} from "../api/types";
import { t } from "../i18n";
import { keyLabel } from "../state/actions";

const reasons: Record<SimulationReport["decisions"][number]["reason"], string> =
  {
    planned: "Akcja zaplanowana",
    user_filtered: "Ten widz nie jest na liście dozwolonych osób.",
    no_mapping: "Brak mapowania dla tego komentarza.",
    action_cooldown:
      "Za szybko: od poprzedniej takiej komendy nie minęło 0,3 s.",
    queue_full: "Kolejka jest pełna (100 oczekujących akcji).",
    expired: "Polecenie czekało w kolejce ponad 1 sekundę.",
  };
const platforms = {
  tiktok: "TikTok",
  twitch: "Twitch",
  youtube: "YouTube",
  kick: "Kick",
};
export function ChatSimulator({
  config,
  revision,
  dirty,
  connected,
  live,
}: {
  config: AppConfig;
  revision: number;
  dirty: boolean;
  connected: boolean;
  live: boolean;
}) {
  const [selected, setSelected] = useState(config.active_profile_id);
  const profile =
    config.profiles.find((p) => p.id === selected) ??
    config.profiles.find((p) => p.id === config.active_profile_id)!;
  const [platform, setPlatform] = useState<Platform>(config.platform);
  const [user, setUser] = useState("widz");
  const [comment, setComment] = useState("");
  const [messages, setMessages] = useState<SimulationMessage[]>([
    { offset_ms: 0, user_id: "widz", comment: "" },
  ]);
  const [report, setReport] = useState<SimulationReport | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const clear = () => {
    setReport(null);
    setError("");
  };
  const run = async (messages: SimulationMessage[]) => {
    setBusy(true);
    setError("");
    setReport(null);
    try {
      setReport(
        await request<SimulationReport>("/api/simulation", "POST", {
          expected_revision: revision,
          profile_id: profile.id,
          platform,
          messages,
        }),
      );
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Nie udało się wykonać operacji.",
      );
    } finally {
      setBusy(false);
    }
  };
  const update = (index: number, patch: Partial<SimulationMessage>) => {
    clear();
    setMessages((rows) =>
      rows.map((row, i) => (i === index ? { ...row, ...patch } : row)),
    );
  };
  return (
    <section className="card simulator">
      <span className="simulator-badge">{t("Symulacja — bez klawiszy")}</span>
      <h2>{t("Sprawdź, co zrobi komentarz")}</h2>
      <p>
        {t(
          "Wpisz wiadomość widza. Zobaczysz akcję albo powód jej pominięcia. Nie potrzebujesz połączenia z czatem.",
        )}
      </p>
      {live && (
        <p className="hint">
          {t(
            "Nasłuch LIVE działa niezależnie. Ten test nie wysyła klawiszy i nie zmienia jego kolejki.",
          )}
        </p>
      )}
      {dirty && (
        <div className="notice">
          {t(
            "Niezapisany szkic jest pomijany. Testujesz ostatnio zapisane ustawienia.",
          )}
        </div>
      )}
      <fieldset className="editor-fields" disabled={busy || !connected}>
        <div className="simulator-context">
          <label>
            {t("Profil do testu")}
            <select
              value={profile.id}
              onChange={(e) => {
                setSelected(e.target.value);
                clear();
              }}
            >
              {config.profiles.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            {t("Platforma")}
            <select
              value={platform}
              onChange={(e) => {
                setPlatform(e.target.value as Platform);
                clear();
              }}
            >
              {Object.entries(platforms).map(([id, name]) => (
                <option key={id} value={id}>
                  {name}
                </option>
              ))}
            </select>
          </label>
        </div>
        <p className="hint">
          {t(
            "Wybór dotyczy tylko testu. Nie przełącza profilu ani źródła LIVE.",
          )}
        </p>
        {profile.filters[platform] && (
          <p className="hint">
            {t("Dozwoleni widzowie:")} {profile.filters[platform]}
          </p>
        )}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void run([{ offset_ms: 0, user_id: user, comment }]);
          }}
        >
          <div className="simulator-inputs">
            <label>
              {t(
                platform === "youtube"
                  ? "ID kanału widza"
                  : "Login widza (bez @)",
              )}
              <input
                required
                maxLength={128}
                value={user}
                onChange={(e) => {
                  setUser(e.target.value);
                  clear();
                }}
              />
            </label>
            <label>
              {t("Komentarz widza")}
              <input
                maxLength={2000}
                value={comment}
                placeholder={
                  profile.mappings[0]?.trigger ?? t("Wpisz komentarz…")
                }
                onChange={(e) => {
                  setComment(e.target.value);
                  clear();
                }}
              />
            </label>
            <button className="primary" type="submit">
              {t("Sprawdź komentarz")}
            </button>
          </div>
        </form>
        <details className="simulator-advanced">
          <summary>{t("Więcej wiadomości / test spamu")}</summary>
          <p className="hint">
            {t(
              "Czas liczony od początku testu, w milisekundach. Każdy test zaczyna z pustą kolejką. Limit: 1000 wiadomości w 60 sekundach.",
            )}
          </p>
          <button
            type="button"
            disabled={!profile.mappings.length}
            onClick={() => {
              clear();
              setMessages(
                [0, 100, 200, 300, 600].map((offset_ms) => ({
                  offset_ms,
                  user_id: user,
                  comment: profile.mappings[0].trigger,
                })),
              );
            }}
          >
            {t("Wstaw przykład spamu")}
          </button>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void run(messages);
            }}
          >
            <div className="simulator-messages">
              {messages.map((row, i) => (
                <div className="simulator-message" key={i}>
                  <label>
                    {t("Czas (ms)")}
                    <input
                      aria-label={t("Czas wiadomości {n} (ms)", { n: i + 1 })}
                      type="number"
                      required
                      min={0}
                      max={60000}
                      step={1}
                      value={Number.isNaN(row.offset_ms) ? "" : row.offset_ms}
                      onChange={(e) =>
                        update(i, { offset_ms: e.target.valueAsNumber })
                      }
                    />
                  </label>
                  <label>
                    {t("Widz")}
                    <input
                      aria-label={t("Widz wiadomości {n}", { n: i + 1 })}
                      required
                      maxLength={128}
                      value={row.user_id}
                      onChange={(e) => update(i, { user_id: e.target.value })}
                    />
                  </label>
                  <label>
                    {t("Komentarz")}
                    <input
                      aria-label={t("Treść wiadomości {n}", { n: i + 1 })}
                      maxLength={2000}
                      value={row.comment}
                      onChange={(e) => update(i, { comment: e.target.value })}
                    />
                  </label>
                  <button
                    type="button"
                    disabled={messages.length === 1}
                    aria-label={t("Usuń wiadomość {n}", { n: i + 1 })}
                    onClick={() => {
                      clear();
                      setMessages((rows) =>
                        rows.filter((_, index) => index !== i),
                      );
                    }}
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
            <div className="simulator-buttons">
              <button
                type="button"
                disabled={messages.length >= 1000}
                onClick={() => {
                  clear();
                  setMessages((rows) => [
                    ...rows,
                    {
                      offset_ms: Math.min(
                        60000,
                        (rows.at(-1)?.offset_ms || 0) + 300,
                      ),
                      user_id: user,
                      comment,
                    },
                  ]);
                }}
              >
                {t("+ Dodaj wiadomość")}
              </button>
              <button className="primary" type="submit">
                {t("Uruchom scenariusz")}
              </button>
            </div>
          </form>
        </details>
      </fieldset>
      {busy && <p role="status">{t("Sprawdzanie…")}</p>}
      {error && (
        <div className="notice error" role="alert">
          {t(error)}
        </div>
      )}
      {report && (
        <section
          className="simulator-results"
          aria-label={t("Wynik symulacji")}
        >
          <h3>{t("Wynik symulacji")}</h3>
          <p>
            {t("Zaplanowane: {planned} · Pominięte: {rejected}", {
              planned: report.planned_count,
              rejected: report.rejected_count,
            })}
          </p>
          <p className="hint">
            {report.profile_name} · {platforms[report.platform]} ·{" "}
            {t("Zapis ustawień nr {revision}", {
              revision: report.config_revision,
            })}
          </p>
          {report.config_revision !== revision && (
            <div className="notice">
              {t("Ustawienia zmieniły się od tego testu. Uruchom go ponownie.")}
            </div>
          )}
          <ol className="simulator-decisions">
            {report.decisions.map((d) => (
              <li
                key={d.message_index}
                className={d.reason === "planned" ? "planned" : "skipped"}
              >
                <div className="simulator-decision-context">
                  <span>
                    {d.offset_ms} ms · {d.user_id}
                  </span>
                  <q>{d.comment || "∅"}</q>
                </div>
                <strong>{t(reasons[d.reason])}</strong>
                {d.steps.length > 0 && (
                  <details>
                    <summary>{t("Zobacz kroki")}</summary>
                    <ol>
                      {d.steps.map((step, i) => (
                        <li key={i}>
                          <span>
                            {step.start_ms}–{step.end_ms} ms:{" "}
                          </span>
                          {step.type === "wait"
                            ? t("Poczekaj {duration} ms", {
                                duration: step.duration_ms,
                              })
                            : step.type === "hold"
                              ? t("Przytrzymaj {keys} przez {duration} ms", {
                                  keys: step.keys.map(keyLabel).join(" + "),
                                  duration: step.duration_ms,
                                })
                              : t("Naciśnij {keys}", {
                                  keys: step.keys.map(keyLabel).join(" + "),
                                })}
                        </li>
                      ))}
                    </ol>
                  </details>
                )}
              </li>
            ))}
          </ol>
          <p className="hint">
            {t(
              "To plan działania. Czasy pomijają opóźnienia systemu i gry; samo naciśnięcie ma umownie 0 ms. Symulacja nie sprawdza, czy gra odbierze klawisze.",
            )}
          </p>
        </section>
      )}
    </section>
  );
}
