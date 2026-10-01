import type { ControlLimits as Limits, ControlStats } from "../api/types";
import { t } from "../i18n";
import { controlReasons, defaultLimits, limitRanges } from "../state/limits";

export function ControlLimits({
  value = defaultLimits,
  onChange,
  stats,
  profileName,
  sessionProfile,
  connected,
}: {
  value?: Limits;
  onChange: (value: Limits) => void;
  stats?: ControlStats;
  profileName: string;
  sessionProfile?: string | null;
  connected: boolean;
}) {
  const counts = stats?.counts ?? {};
  const skipped = Object.entries(counts).filter(
    ([key]) => !["accepted", "executed"].includes(key),
  );
  const field = (key: keyof Limits, label: string, help: string) => {
    const [min, max] = limitRanges[key];
    const invalid =
      !Number.isInteger(value[key]) || value[key] < min || value[key] > max;
    return (
      <label className="control-limit-field">
        <span>{t(label)}</span>
        <input
          aria-label={t(label)}
          type="number"
          min={min}
          max={max}
          step={1}
          required
          value={Number.isNaN(value[key]) ? "" : value[key]}
          aria-invalid={invalid}
          onChange={(e) =>
            onChange({ ...value, [key]: e.target.valueAsNumber })
          }
        />
        <small>{t(help)}</small>
        {invalid && (
          <small role="alert">
            {t("Wpisz liczbę całkowitą od {min} do {max}.", { min, max })}
          </small>
        )}
      </label>
    );
  };
  return (
    <>
      <section className="card control-limits">
        <h2>{t("Jak często czat może sterować?")}</h2>
        <p>
          {t("Ustawienia profilu:")} <strong>{profileName}</strong>
        </p>
        <div className="control-limit-grid">
          {field(
            "viewer_cooldown_ms",
            "Odstęp dla jednego widza (ms)",
            "1000 ms = raz na sekundę, niezależnie od komendy. 0 = bez limitu widza.",
          )}
          {field(
            "action_cooldown_ms",
            "Odstęp dla tej samej komendy (ms)",
            "Wspólny dla wszystkich widzów. 0 = bez limitu komendy.",
          )}
        </div>
        <details className="simulator-advanced">
          <summary>{t("Co robić z nadmiarem? Kolejka")}</summary>
          <p>
            {t(
              "Nowe polecenie trafia na koniec kolejki. Gdy zabraknie miejsca, zostaje pominięte. Trwająca akcja kończy się normalnie.",
            )}
          </p>
          <div className="control-limit-grid">
            {field(
              "queue_capacity",
              "Miejsca w kolejce",
              "Od 1 do 100 oczekujących akcji. Trwająca akcja nie zajmuje miejsca.",
            )}
            {field(
              "action_ttl_ms",
              "Maksymalny czas oczekiwania (ms)",
              "Od 100 do 5000 ms. Starsze polecenia są pomijane przed rozpoczęciem.",
            )}
          </div>
        </details>
        <p className="hint">
          {t(
            "Zmiany obowiązują od następnego uruchomienia nasłuchu. Odrzucona komenda nie zużywa limitu widza ani komendy.",
          )}
        </p>
      </section>
      <section className="card control-activity">
        <h2>{t("Co dzieje się z poleceniami?")}</h2>
        <p>
          {sessionProfile
            ? `${t("Profil sesji:")} ${sessionProfile}`
            : t("Rozpocznij nasłuch, aby zobaczyć wyniki.")}
        </p>
        {!connected && (
          <p className="notice">
            {t("Brak połączenia — wyświetlane wyniki mogą być nieaktualne.")}
          </p>
        )}
        <div className="control-counters">
          <div>
            <strong>{counts.accepted ?? 0}</strong>
            <span>{t("Przyjęte")}</span>
          </div>
          <div>
            <strong>{counts.executed ?? 0}</strong>
            <span>{t("Wykonane")}</span>
          </div>
          <div>
            <strong>
              {skipped.reduce((sum, [, count]) => sum + count, 0)}
            </strong>
            <span>{t("Pominięte / anulowane")}</span>
          </div>
        </div>
        <p className="hint">
          {t(
            "Wykonane są częścią przyjętych. Przyjęta akcja może później wygasnąć lub zostać anulowana. Liczniki zerują się przy nowym Start.",
          )}
        </p>
        {skipped.length > 0 && (
          <dl className="control-reasons">
            {skipped.map(([reason, count]) => (
              <div key={reason}>
                <dt>{t(controlReasons[reason] ?? reason)}</dt>
                <dd>{count}</dd>
              </div>
            ))}
          </dl>
        )}
        <details className="simulator-advanced">
          <summary>{t("Ostatnie decyzje i ich powody")}</summary>
          <p className="hint">
            {t(
              "Ostatnie 30 decyzji, od najnowszej. Liczniki obejmują wszystkie komentarze; podgląd odświeża się raz na sekundę.",
            )}
          </p>
          <ol className="control-decisions">
            {[...(stats?.recent ?? [])].reverse().map((row) => (
              <li key={row.id}>
                <span>
                  {row.actor_id || "—"} · <q>{row.comment}</q>
                </span>
                <strong>{t(controlReasons[row.reason] ?? row.reason)}</strong>
              </li>
            ))}
          </ol>
        </details>
      </section>
    </>
  );
}
