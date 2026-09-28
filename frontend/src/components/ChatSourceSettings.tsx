import { t, getLanguage } from "../i18n";
import { useEffect, useState, useId } from "react";
import { PlatformTabs } from "./PlatformTabs";
import { YouTubeKeySettings } from "./YouTubeKeySettings";
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
  const tabsId = useId();
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
    <div className="chat-source-group">
      <PlatformTabs
        id={tabsId}
        value={config.platform}
        onChange={(platform) => onChange({ platform })}
      />
      <section
        className="card chat-source-card"
        role="tabpanel"
        id={`${tabsId}-panel`}
        aria-labelledby={`${tabsId}-${config.platform}`}
      >
        <span className="eyebrow">{t("POŁĄCZENIE")}</span>
        <h2>{t("Twoja transmisja")}</h2>
        <label>
          {config.platform === "youtube" ? t("Transmisja YouTube") : t("Kanał")}
          <div className="with-prefix">
            {config.platform !== "youtube" && <span aria-hidden="true">@</span>}
            <input
              value={source.channel}
              placeholder={
                config.platform === "youtube"
                  ? "https://www.youtube.com/watch?v=…"
                  : t("nazwa_kanału")
              }
              onChange={(e) =>
                onChange({
                  [config.platform]: {
                    ...source,
                    channel: e.target.value,
                    ...(config.platform === "kick"
                      ? { chatroom_id: null }
                      : {}),
                  },
                })
              }
            />
          </div>
        </label>
        <p className="hint">
          {config.platform === "tiktok"
            ? t("Wpisz nick konta prowadzącego TikTok LIVE.")
            : config.platform === "twitch"
              ? t(
                  "Wpisz login kanału Twitch, bez adresu URL. Kanał może być inny niż połączone konto.",
                )
              : config.platform === "youtube"
                ? t(
                    "Wklej link do trwającej transmisji lub jej ID. Wymagany jest włączony czat.",
                  )
                : t(
                    "Wpisz login kanału Kick. Połączenie lokalne, bez logowania. Integracja nieoficjalna może wymagać aktualizacji po zmianach Kicka.",
                  )}
        </p>
        <label>
          {t("Dozwoleni użytkownicy")}{" "}
          <span className="optional">{t("opcjonalnie")}</span>
          <textarea
            rows={3}
            aria-describedby="allowed-users-hint"
            placeholder={
              config.platform === "youtube"
                ? t("np. UC…")
                : t("np. gracz1, gracz2")
            }
            value={source.target_user}
            onChange={(e) =>
              onChange({
                [config.platform]: { ...source, target_user: e.target.value },
              })
            }
          />
        </label>
        <p className="hint" id="allowed-users-hint">
          {config.platform === "youtube"
            ? t(
                "Wpisz ID kanałów użytkowników (UC…), nie nazwy wyświetlane. ID zobaczysz przy komentarzach w panelu aktywności. Oddziel je przecinkami lub wierszami. Wielkość liter ma znaczenie.",
              )
            : `${t("Nicki oddziel przecinkami lub wpisz po jednym w wierszu. Możesz dodać @.")} ${config.platform === "tiktok" ? t("Wielkość liter ma znaczenie.") : t("Wielkość liter nie ma znaczenia.")}`}{" "}
          {t("Puste pole dopuszcza wszystkich widzów.")}
        </p>
        {config.platform === "youtube" && <YouTubeKeySettings />}
        {config.platform === "kick" && (
          <details>
            <summary>{t("Zaawansowane: ID pokoju czatu")}</summary>
            <label>
              {t("ID pokoju czatu Kick (opcjonalnie)")}
              <input
                type="number"
                min="1"
                step="1"
                max="9007199254740991"
                value={config.kick.chatroom_id ?? ""}
                onChange={(e) =>
                  onChange({
                    kick: {
                      ...config.kick,
                      chatroom_id: e.target.value
                        ? Number(e.target.value)
                        : null,
                    },
                  })
                }
              />
            </label>
            <p className="hint">
              {t(
                "Użyj, jeśli Kick blokuje rozpoznawanie kanału. ID określa faktyczny czat — upewnij się, że należy do wpisanego kanału. Zmiana kanału czyści ID.",
              )}
            </p>
            <p className="hint">
              {t(
                "W przeglądarce otwórz kick.com/api/v2/channels/LOGIN i odczytaj chatroom.id. To ID pokoju, nie ID użytkownika.",
              )}
            </p>
          </details>
        )}
        {config.platform === "twitch" && (
          <div className="twitch-account">
            <h3>{t("Konto Twitch")}</h3>
            {!auth ? (
              <p>{t("Sprawdzanie konta…")}</p>
            ) : !auth.configured ? (
              <p className="hint">
                {t(
                  "Integracja Twitch nie jest skonfigurowana. Ustaw identyfikator aplikacji TIKOPLAY_TWITCH_CLIENT_ID i uruchom TikoPlay ponownie.",
                )}
              </p>
            ) : (
              <>
                {auth.login && (
                  <p>
                    {t("Połączone konto:")} <strong>@{auth.login}</strong>
                  </p>
                )}
                {auth.status === "pending" || activation ? (
                  <>
                    {activation ? (
                      <div className="info-box">
                        <p>
                          {t("Kod aktywacji:")}{" "}
                          <strong className="activation-code">
                            {activation.user_code}
                          </strong>
                        </p>
                        <a
                          href={activation.verification_uri}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          {t("Otwórz aktywację Twitcha")}
                        </a>
                        <p>
                          {t(
                            "Zaloguj się w Twitchu i zatwierdź odczyt czatu. Kod jest ważny do",
                          )}{" "}
                          {new Date(
                            activation.expires_at * 1000,
                          ).toLocaleTimeString(
                            getLanguage() === "pl" ? "pl-PL" : "en-GB",
                          )}
                          .
                        </p>
                      </div>
                    ) : (
                      <p>
                        {t(
                          "Logowanie rozpoczęto w innym panelu. Dokończ je tam lub anuluj.",
                        )}
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
                      {t("Anuluj logowanie")}
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
                          throw new Error(
                            "Niepoprawny adres aktywacji Twitcha.",
                          );
                        setActivation(result);
                      })
                    }
                  >
                    {t("Połącz konto Twitch")}
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
                    {t("Odłącz konto")}
                  </button>
                )}
                {auth.error && <p role="alert">{t(auth.error.message)}</p>}
              </>
            )}
            {error && <p role="alert">{t(error)}</p>}
          </div>
        )}
      </section>
    </div>
  );
}
