import { useEffect, useState } from "react";
import { twitchAuthApi } from "../api/client";
import type {
  AppConfig,
  TwitchAuthState,
  TwitchActivation,
} from "../api/types";

export function ChatSourceSettings({
  config,
  onChange,
  auth,
  onAuthChanged,
}: {
  config: AppConfig;
  onChange: (patch: Partial<AppConfig>) => void;
  auth: TwitchAuthState | null;
  onAuthChanged: () => Promise<void>;
}) {
  const [activation, setActivation] = useState<TwitchActivation | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const source = config[config.platform];
  useEffect(() => {
    setActivation((current) =>
      current &&
      auth?.status === "pending" &&
      auth.attempt_id === current.attempt_id
        ? current
        : null,
    );
  }, [auth]);
  useEffect(() => {
    if (!activation) return;
    const timer = setTimeout(
      () => setActivation(null),
      Math.max(0, activation.expires_at * 1000 - Date.now()),
    );
    return () => clearTimeout(timer);
  }, [activation]);
  const act = async (fn: () => Promise<void>) => {
    setBusy(true);
    setError("");
    try {
      await fn();
      await onAuthChanged();
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Nie udało się połączyć konta.",
      );
    } finally {
      setBusy(false);
    }
  };
  return (
    <section className="card chat-source-card">
      <span className="eyebrow">POŁĄCZENIE</span>
      <h2>Twoja transmisja</h2>
      <label>
        Źródło czatu
        <select
          value={config.platform}
          onChange={(e) =>
            onChange({ platform: e.target.value as AppConfig["platform"] })
          }
        >
          <option value="tiktok">TikTok LIVE</option>
          <option value="twitch">Twitch</option>
        </select>
      </label>
      <label>
        Kanał
        <div className="with-prefix">
          <span aria-hidden="true">@</span>
          <input
            value={source.channel}
            placeholder="nazwa_kanału"
            onChange={(e) =>
              onChange({
                [config.platform]: { ...source, channel: e.target.value },
              })
            }
          />
        </div>
      </label>
      <p className="hint">
        {config.platform === "tiktok"
          ? "Wpisz nick konta prowadzącego TikTok LIVE."
          : "Wpisz login kanału Twitch, bez adresu URL. Kanał może być inny niż połączone konto."}
      </p>
      <label>
        Dozwoleni użytkownicy <span className="optional">opcjonalnie</span>
        <textarea
          rows={3}
          aria-describedby="allowed-users-hint"
          placeholder="np. gracz1, gracz2"
          value={source.target_user}
          onChange={(e) =>
            onChange({
              [config.platform]: { ...source, target_user: e.target.value },
            })
          }
        />
      </label>
      <p className="hint" id="allowed-users-hint">
        Nicki oddziel przecinkami lub wpisz po jednym w wierszu. Możesz dodać @.{" "}
        {config.platform === "twitch"
          ? "Wielkość liter nie ma znaczenia."
          : "Wielkość liter ma znaczenie."}{" "}
        Puste pole dopuszcza wszystkich widzów.
      </p>
      {config.platform === "twitch" && (
        <div className="twitch-account">
          <h3>Konto Twitch</h3>
          {!auth ? (
            <p>Sprawdzanie konta…</p>
          ) : !auth.configured ? (
            <p className="hint">
              Integracja Twitch nie jest skonfigurowana. Ustaw identyfikator
              aplikacji TIKOPLAY_TWITCH_CLIENT_ID i uruchom TikoPlay ponownie.
            </p>
          ) : (
            <>
              {auth.login && (
                <p>
                  Połączone konto: <strong>@{auth.login}</strong>
                </p>
              )}
              {auth.status === "pending" || activation ? (
                <>
                  {activation ? (
                    <div className="info-box">
                      <p>
                        Kod aktywacji:{" "}
                        <strong className="activation-code">
                          {activation.user_code}
                        </strong>
                      </p>
                      <a
                        href={activation.verification_uri}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        Otwórz aktywację Twitcha
                      </a>
                      <p>
                        Zaloguj się w Twitchu i zatwierdź odczyt czatu. Kod jest
                        ważny do{" "}
                        {new Date(
                          activation.expires_at * 1000,
                        ).toLocaleTimeString("pl-PL")}
                        .
                      </p>
                    </div>
                  ) : (
                    <p>
                      Logowanie rozpoczęto w innym panelu. Dokończ je tam lub
                      anuluj.
                    </p>
                  )}
                  <button
                    disabled={busy}
                    onClick={() =>
                      void act(async () => {
                        await twitchAuthApi.cancel();
                        setActivation(null);
                      })
                    }
                  >
                    Anuluj logowanie
                  </button>
                </>
              ) : (
                <button
                  disabled={busy}
                  onClick={() =>
                    void act(async () => {
                      const result = await twitchAuthApi.start();
                      const url = new URL(result.verification_uri);
                      if (
                        url.protocol !== "https:" ||
                        !["www.twitch.tv", "twitch.tv"].includes(
                          url.hostname,
                        ) ||
                        url.username ||
                        url.password ||
                        (url.port && url.port !== "443")
                      )
                        throw new Error("Niepoprawny adres aktywacji Twitcha.");
                      setActivation(result);
                    })
                  }
                >
                  Połącz konto Twitch
                </button>
              )}
              {auth.login && (
                <button
                  disabled={busy}
                  onClick={() =>
                    void act(async () => {
                      await twitchAuthApi.disconnect();
                      setActivation(null);
                    })
                  }
                >
                  Odłącz konto
                </button>
              )}
              {auth.error && <p role="alert">{auth.error.message}</p>}
            </>
          )}
          {error && <p role="alert">{error}</p>}
        </div>
      )}
    </section>
  );
}
