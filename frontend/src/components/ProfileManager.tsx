import { useEffect, useRef, useState } from "react";
import type { AppConfig, GameProfile, ProfileTemplate } from "../api/types";
import { request } from "../api/client";
import { activeProfile, createProfile } from "../state/profiles";
import { t } from "../i18n";

type Props = {
  config: AppConfig;
  templates: ProfileTemplate[];
  disabled: boolean;
  dirty: boolean;
  onMutate: (transform: (config: AppConfig) => AppConfig) => Promise<void>;
  onReload: () => Promise<void>;
};

export function ProfileManager({
  config,
  templates,
  disabled,
  dirty,
  onMutate,
  onReload,
}: Props) {
  const profile = activeProfile(config);
  const [mode, setMode] = useState<"new" | "rename" | "delete" | null>(null);
  const [name, setName] = useState("");
  const [templateId, setTemplateId] = useState("");
  const [replacement, setReplacement] = useState("");
  const [preview, setPreview] = useState<GameProfile | null>(null);
  const [error, setError] = useState("");
  const [working, setWorking] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const importAttempt = useRef(0);
  const template = templates.find((p) => p.id === templateId);
  const locked = disabled || working;
  useEffect(() => {
    setMode(null);
    setPreview(null);
    setError("");
    setWorking(false);
    importAttempt.current++;
  }, [profile.id]);
  useEffect(
    () => () => {
      importAttempt.current++;
    },
    [],
  );
  async function act(fn: () => Promise<void>) {
    setWorking(true);
    setError("");
    try {
      await fn();
      setMode(null);
      setPreview(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Błąd zapisu");
    } finally {
      setWorking(false);
    }
  }
  const add = (p: GameProfile) =>
    onMutate((c) => ({
      ...c,
      profiles: [...c.profiles, p],
      active_profile_id: p.id,
    }));
  async function readFile(file: File) {
    const attempt = ++importAttempt.current;
    setWorking(true);
    setError("");
    setPreview(null);
    setMode(null);
    try {
      if (file.size > 1024 * 1024)
        throw new Error("Plik profilu przekracza 1 MiB.");
      const payload = JSON.parse(await file.text());
      const result = await request<GameProfile>(
        "/api/profiles/import-preview",
        "POST",
        payload,
      );
      if (attempt === importAttempt.current) setPreview(result);
    } catch (e) {
      if (attempt === importAttempt.current)
        setError(
          e instanceof Error ? e.message : "Niepoprawny plik JSON profilu.",
        );
    } finally {
      if (attempt === importAttempt.current) setWorking(false);
    }
  }
  return (
    <section className="card profile-card">
      <div className="section-heading">
        <div>
          <span className="eyebrow">{t("PROFILE GIER")}</span>
          <h2>{t("Twoje gry")}</h2>
          <p>{t("Każdy profil ma własne mapowania i dozwolonych widzów.")}</p>
        </div>
      </div>
      <label>
        {t("Aktywny profil")}
        <select
          value={profile.id}
          disabled={locked}
          onChange={(e) => {
            const id = e.target.value;
            void act(() => onMutate((c) => ({ ...c, active_profile_id: id })));
          }}
        >
          {config.profiles.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name} · {p.id.slice(0, 8)}
            </option>
          ))}
        </select>
      </label>
      {disabled && (
        <p className="hint">
          {t(
            "Zatrzymaj nasłuch i poczekaj na połączenie z panelem, aby zarządzać profilami.",
          )}
        </p>
      )}
      <div className="profile-actions">
        <button
          disabled={locked || config.profiles.length >= 100}
          onClick={() => {
            setMode("new");
            setName("");
            setTemplateId("");
            setPreview(null);
          }}
        >
          {t("Nowy profil")}
        </button>
        <button
          disabled={locked}
          onClick={() => {
            setMode("rename");
            setName(profile.name);
            setPreview(null);
          }}
        >
          {t("Zmień nazwę")}
        </button>
        <button
          disabled={locked || config.profiles.length >= 100}
          onClick={() =>
            void act(() =>
              onMutate((c) => {
                const original = activeProfile(c);
                const copy = {
                  ...structuredClone(original),
                  id: crypto.randomUUID(),
                  name: `${original.name.slice(0, 65)} (${t("kopia")})`,
                  mappings: original.mappings.map((m) => ({
                    ...m,
                    keys: [...m.keys],
                    id: crypto.randomUUID(),
                  })),
                };
                return {
                  ...c,
                  profiles: [...c.profiles, copy],
                  active_profile_id: copy.id,
                };
              }),
            )
          }
        >
          {t("Duplikuj")}
        </button>
        <button
          disabled={locked}
          onClick={() =>
            void act(async () => {
              if (dirty)
                throw new Error("Zapisz lub odrzuć szkic przed eksportem.");
              const payload = await request(
                `/api/profiles/${encodeURIComponent(profile.id)}/export`,
              );
              const url = URL.createObjectURL(
                new Blob([JSON.stringify(payload, null, 2)], {
                  type: "application/json",
                }),
              );
              const a = document.createElement("a");
              a.href = url;
              a.download = "tikoplay-profile.json";
              a.click();
              setTimeout(() => URL.revokeObjectURL(url), 1000);
            })
          }
        >
          {t("Eksportuj profil")}
        </button>
        <button
          disabled={locked || config.profiles.length >= 100}
          onClick={() => fileInput.current?.click()}
        >
          {t("Importuj plik")}
        </button>
        <input
          ref={fileInput}
          type="file"
          accept=".json,application/json"
          className="profile-file-input"
          aria-label={t("Importuj profil")}
          disabled={locked}
          onChange={(e) => {
            const file = e.target.files?.[0];
            e.target.value = "";
            if (file) void readFile(file);
          }}
        />
        <button
          className="danger"
          disabled={locked || config.profiles.length === 1}
          onClick={() => {
            setMode("delete");
            setReplacement(
              config.profiles.find((p) => p.id !== profile.id)?.id ?? "",
            );
            setPreview(null);
          }}
        >
          {t("Usuń profil")}
        </button>
        {dirty && (
          <button
            disabled={locked}
            onClick={() => {
              if (
                confirm(
                  t("Odrzucić lokalny szkic i wczytać zapisane ustawienia?"),
                )
              )
                void act(onReload);
            }}
          >
            {t("Odrzuć szkic")}
          </button>
        )}
      </div>
      {mode && (
        <form
          className="profile-form"
          onSubmit={(e) => {
            e.preventDefault();
            if (locked) return;
            if (mode === "new")
              void act(() => add(createProfile(name, template)));
            if (mode === "rename")
              void act(() =>
                onMutate((c) => ({
                  ...c,
                  profiles: c.profiles.map((p) =>
                    p.id === profile.id ? { ...p, name: name.trim() } : p,
                  ),
                })),
              );
            if (mode === "delete")
              void act(() =>
                onMutate((c) => ({
                  ...c,
                  profiles: c.profiles.filter((p) => p.id !== profile.id),
                  active_profile_id: replacement,
                })),
              );
          }}
        >
          {mode === "new" && (
            <>
              <label>
                {t("Szablon profilu")}
                <select
                  value={templateId}
                  disabled={locked}
                  onChange={(e) => {
                    setTemplateId(e.target.value);
                    setName(
                      templates.find((p) => p.id === e.target.value)?.name ??
                        "",
                    );
                  }}
                >
                  <option value="">{t("Pusty profil")}</option>
                  {["Ogólne", "Retro", "Nowsze"].map((group) => (
                    <optgroup key={group} label={t(group)}>
                      {templates
                        .filter((p) => p.category === group)
                        .map((p) => (
                          <option key={p.id} value={p.id}>
                            {t(p.name)}
                          </option>
                        ))}
                    </optgroup>
                  ))}
                </select>
              </label>
              {template && <p className="hint">{t(template.description)}</p>}
              {template && (
                <p className="profile-preview">
                  {template.mappings
                    .map((m) => `${m.trigger} → ${m.keys.join(" + ")}`)
                    .join(" · ")}
                </p>
              )}
            </>
          )}
          {mode !== "delete" ? (
            <label>
              {t("Nazwa profilu")}
              <input
                value={name}
                maxLength={80}
                required
                disabled={locked}
                onChange={(e) => setName(e.target.value)}
              />
            </label>
          ) : (
            <>
              <p>
                {t(
                  "Usunięcie profilu jest nieodwracalne. Wybierz profil, który go zastąpi.",
                )}
              </p>
              <label>
                {t("Profil zastępczy")}
                <select
                  value={replacement}
                  disabled={locked}
                  onChange={(e) => setReplacement(e.target.value)}
                >
                  {config.profiles
                    .filter((p) => p.id !== profile.id)
                    .map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                      </option>
                    ))}
                </select>
              </label>
            </>
          )}
          <div className="profile-actions">
            <button
              type="submit"
              className="primary"
              disabled={
                locked || (mode === "delete" ? !replacement : !name.trim())
              }
            >
              {t(
                mode === "new"
                  ? "Utwórz profil"
                  : mode === "rename"
                    ? "Zapisz nazwę"
                    : "Potwierdź usunięcie",
              )}
            </button>
            <button
              type="button"
              disabled={working}
              onClick={() => setMode(null)}
            >
              {t("Anuluj")}
            </button>
          </div>
        </form>
      )}
      {preview && (
        <div className="profile-form">
          <h3>{t("Podgląd importu")}</h3>
          <strong>{preview.name}</strong>
          <p>
            {preview.mappings.length} {t("mapowań")}
          </p>
          <div className="profile-import-list">
            {preview.mappings.map((m) => (
              <div key={m.id}>
                {m.trigger} → {m.keys.join(" + ")}
              </div>
            ))}
          </div>
          <p className="hint">
            {t(
              "Import tworzy nowy profil. Kanały, konta i filtry widzów nie są przenoszone.",
            )}
          </p>
          <div className="profile-actions">
            <button
              disabled={locked || config.profiles.length >= 100}
              className="primary"
              onClick={() => void act(() => add(preview))}
            >
              {t("Dodaj importowany profil")}
            </button>
            <button disabled={working} onClick={() => setPreview(null)}>
              {t("Anuluj")}
            </button>
          </div>
        </div>
      )}
      <p className="hint">
        {t(
          "Eksport zawiera nazwę i mapowania. Pomija kanały, konta, klucze i filtry widzów.",
        )}
      </p>
      {error && <p role="alert">{t(error)}</p>}
    </section>
  );
}
