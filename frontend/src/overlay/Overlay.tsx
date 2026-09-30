import { useEffect, useState, type CSSProperties } from "react";
import { setLanguage, t, useLanguage } from "../i18n";
import { readableAction } from "../state/actions";
import { connectOverlay } from "./client";
import type { OverlaySnapshot, OverlayConnection } from "./types";
export function OverlayView({
  snapshot,
  status,
}: {
  snapshot: OverlaySnapshot | null;
  status: OverlayConnection;
}) {
  useLanguage();
  if (status !== "connected" || !snapshot)
    return (
      <div className="broadcast-overlay">
        <div className="overlay-status offline">
          {t(
            status === "invalid"
              ? "Adres nakładki wygasł. Skopiuj nowy z panelu."
              : status === "connecting"
                ? "Łączenie z TikoPlay…"
                : "Brak połączenia z TikoPlay",
          )}
        </div>
      </div>
    );
  const p = snapshot.presentation;
  return (
    <div
      className="broadcast-overlay"
      style={
        { "--overlay-accent": p.accent, fontSize: p.font_size } as CSSProperties
      }
    >
      {p.show_status && (
        <div
          className={"overlay-status " + (snapshot.paused ? "paused" : "live")}
        >
          <span className="overlay-dot" />
          {snapshot.paused ? t("Pauza") : t("Czat steruje grą")}
        </div>
      )}
      {p.show_last_action && snapshot.last_action && (
        <section className="overlay-action" key={snapshot.last_action.id}>
          <span className="overlay-caption">{t("Ostatni wykonany ruch")}</span>
          {p.show_actor && snapshot.last_action.actor && (
            <strong className="overlay-actor">
              {snapshot.last_action.actor}
            </strong>
          )}
          <q>{snapshot.last_action.comment}</q>
          <p>{readableAction(snapshot.last_action.action)}</p>
        </section>
      )}
      {p.show_commands && snapshot.commands.length > 0 && (
        <section className="overlay-commands">
          <span className="overlay-caption">{t("Napisz na czacie")}</span>
          <div>
            {snapshot.commands.map((command, i) => (
              <span className="overlay-command" key={i}>
                <strong>{command.comment}</strong>
                <span>{readableAction(command.action)}</span>
              </span>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
export default function Overlay() {
  const [snapshot, setSnapshot] = useState<OverlaySnapshot | null>(null);
  const [status, setStatus] = useState<OverlayConnection>("connecting");
  useEffect(
    () =>
      connectOverlay(
        new URLSearchParams(location.hash.slice(1)).get("token") ?? "",
        (s) => {
          setLanguage(s.language);
          setSnapshot(s);
        },
        (s) => {
          setStatus(s);
          if (s !== "connected") setSnapshot(null);
        },
      ),
    [],
  );
  return <OverlayView snapshot={snapshot} status={status} />;
}
