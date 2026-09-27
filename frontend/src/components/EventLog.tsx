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
          <span className="eyebrow">NA ŻYWO</span>
          <h2>Aktywność</h2>
        </div>
        <button onClick={onClear}>Wyczyść podgląd</button>
      </div>
      <div className="event-list" aria-live="polite">
        {!events.length ? (
          <div className="empty small">
            Tutaj zobaczysz komentarze i wykonane akcje.
          </div>
        ) : (
          events
            .slice(-150)
            .reverse()
            .map((e) => (
              <div className="event" key={`${e.instance_id}:${e.id}`}>
                <time>{new Date(e.timestamp).toLocaleTimeString("pl-PL")}</time>
                <span className={"event-type " + e.type}>
                  {e.type === "comment"
                    ? "Komentarz"
                    : e.type === "action"
                      ? "Klawisze"
                      : e.type === "status"
                        ? "Status"
                        : e.type}
                </span>
                <span>
                  {e.type === "comment"
                    ? `${e.payload.platform ? `[${e.payload.platform === "twitch" ? "Twitch" : "TikTok"} · @${e.payload.channel}] ` : ""}${e.payload.user}: ${e.payload.comment}`
                    : e.type === "action"
                      ? (e.payload.keys as string[]).join(" + ")
                      : String(e.payload.message ?? e.payload.status ?? "")}
                </span>
              </div>
            ))
        )}
      </div>
    </section>
  );
}
