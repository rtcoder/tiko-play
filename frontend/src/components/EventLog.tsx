import { actionSummary } from "../state/actions";
import type { ActionDefinition } from "../api/types";
import { t, getLanguage, statusLabel } from "../i18n";
import { sourceLabel } from "../api/platforms";
import type { AppEvent } from "../api/types";
export function EventLog({
  events,
  onClear,
}: {
  events: AppEvent[];
  onClear: () => void;
}) {
  return (
    <section className="card">
      <div className="section-heading">
        <div>
          <span className="eyebrow">{t("NA ŻYWO")}</span>
          <h2>{t("Aktywność")}</h2>
        </div>
        <button onClick={onClear}>{t("Wyczyść podgląd")}</button>
      </div>
      <div className="event-list" aria-live="polite">
        {!events.length ? (
          <div className="empty small">
            {t("Tutaj zobaczysz komentarze i wykonane akcje.")}
          </div>
        ) : (
          events
            .slice(-150)
            .reverse()
            .map((e) => (
              <div className="event" key={`${e.instance_id}:${e.id}`}>
                <time>
                  {new Date(e.timestamp).toLocaleTimeString(
                    getLanguage() === "pl" ? "pl-PL" : "en-GB",
                  )}
                </time>
                <span className={"event-type " + e.type}>
                  {t(
                    (
                      {
                        comment: "Komentarz",
                        action: "Klawisze",
                        status: "Status",
                        error: "Błąd",
                        dropped: "Pominięto",
                        config_changed: "Ustawienia",
                        preferences_changed: "Ustawienia",
                        twitch_auth: "Konto Twitch",
                      } as Record<string, string>
                    )[e.type] ?? e.type,
                  )}
                </span>
                <span>
                  {e.type === "comment"
                    ? `${e.payload.platform ? `[${sourceLabel(String(e.payload.platform), String(e.payload.channel))}] ` : ""}${e.payload.user}: ${e.payload.comment}`
                    : e.type === "preferences_changed"
                      ? t("Język: {language}", {
                          language:
                            e.payload.language === "pl" ? "Polski" : "English",
                        })
                      : e.type === "config_changed"
                        ? t("Zapisano")
                        : e.type === "action"
                          ? e.payload.action
                            ? actionSummary(
                                e.payload.action as ActionDefinition,
                              )
                            : (e.payload.keys as string[]).join(" + ")
                          : e.payload.message
                            ? t(String(e.payload.message))
                            : statusLabel(String(e.payload.status ?? ""))}
                </span>
              </div>
            ))
        )}
      </div>
    </section>
  );
}
