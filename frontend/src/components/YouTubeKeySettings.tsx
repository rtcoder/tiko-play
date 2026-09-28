import { t } from "../i18n";
import { useEffect, useState } from "react";
import { youtubeKeyApi } from "../api/client";

export function YouTubeKeySettings() {
  const [configured, setConfigured] = useState<boolean | null>(null);
  const [key, setKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    let mounted = true;
    void youtubeKeyApi.state().then(
      (state) => {
        if (mounted) setConfigured(state.configured);
      },
      (e: unknown) => {
        if (mounted)
          setError(
            e instanceof Error ? e.message : "Nie można odczytać klucza.",
          );
      },
    );
    return () => {
      mounted = false;
    };
  }, []);
  const update = async (remove: boolean) => {
    setBusy(true);
    setError("");
    try {
      const state = remove
        ? await youtubeKeyApi.remove()
        : await youtubeKeyApi.save(key.trim());
      setConfigured(state.configured);
      setKey("");
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Nie udało się zapisać klucza.",
      );
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="twitch-account">
      <h3>{t("Dostęp do YouTube")}</h3>
      <p className="hint">
        {configured === null
          ? t("Sprawdzanie klucza…")
          : configured
            ? t("Klucz zapisany w systemowym magazynie poświadczeń.")
            : t("Brak zapisanego klucza.")}
      </p>
      <label>
        {t("Klucz YouTube Data API")}
        <input
          type="password"
          autoComplete="off"
          spellCheck={false}
          value={key}
          onChange={(e) => setKey(e.target.value)}
        />
      </label>
      <button disabled={busy || !key.trim()} onClick={() => void update(false)}>
        {t("Zapisz klucz")}
      </button>
      {configured && (
        <button disabled={busy} onClick={() => void update(true)}>
          {t("Usuń klucz")}
        </button>
      )}
      <p className="hint">
        {t(
          "W projekcie Google Cloud włącz YouTube Data API v3 i utwórz klucz API. Zmianę klucza wykonuj przy zatrzymanym nasłuchu.",
        )}
      </p>
      <a
        href="https://console.cloud.google.com/apis/library/youtube.googleapis.com"
        target="_blank"
        rel="noopener noreferrer"
      >
        {t("Otwórz YouTube Data API w Google Cloud")}
      </a>
      {error && <p role="alert">{t(error)}</p>}
    </div>
  );
}
