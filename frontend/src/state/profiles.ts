import { defaultLimits } from "./limits";
import type { AppConfig, GameProfile, ProfileTemplate } from "../api/types";

export function activeProfile(config: AppConfig): GameProfile {
  const profile = config.profiles.find(
    (p) => p.id === config.active_profile_id,
  );
  if (!profile) throw new Error("Nie znaleziono profilu.");
  return profile;
}

export function updateProfile(
  config: AppConfig,
  patch: Partial<GameProfile>,
): AppConfig {
  return {
    ...config,
    profiles: config.profiles.map((p) =>
      p.id === config.active_profile_id ? { ...p, ...patch } : p,
    ),
  };
}

export function createProfile(
  name: string,
  template?: ProfileTemplate,
): GameProfile {
  return {
    id: crypto.randomUUID(),
    name: name.trim(),
    limits: { ...defaultLimits },
    filters: { tiktok: "", twitch: "", youtube: "", kick: "" },
    mappings: (template?.mappings ?? []).map((m) => ({
      ...m,
      keys: [...m.keys],
      id: crypto.randomUUID(),
    })),
  };
}
