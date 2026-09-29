export type ActionStep =
  | { type: "press"; keys: string[] }
  | { type: "hold"; keys: string[]; duration_ms: number }
  | { type: "wait"; duration_ms: number };
export interface ActionDefinition {
  steps: ActionStep[];
}
export interface Mapping {
  id: string;
  trigger: string;
  keys?: string[]; // Accepted for legacy presets and drafts. Saved responses use action.
  action?: ActionDefinition;
  [key: string]: unknown;
}
export type Platform = "tiktok" | "twitch" | "youtube" | "kick";
export interface ChannelConfig {
  channel: string;
  [key: string]: unknown;
}
export interface AppConfig {
  version: 6;
  platform: Platform;
  tiktok: ChannelConfig;
  twitch: ChannelConfig;
  youtube: ChannelConfig;
  kick: ChannelConfig & { chatroom_id: number | null };
  active_profile_id: string;
  profiles: GameProfile[];
  show_logs: boolean;
  countdown_enabled: boolean;
  [key: string]: unknown;
}
export interface GameProfile {
  id: string;
  name: string;
  mappings: Mapping[];
  filters: Record<Platform, string>;
  [key: string]: unknown;
}
export interface ProfileTemplate {
  id: string;
  name: string;
  category: string;
  description: string;
  mappings: { trigger: string; keys: string[] }[];
}
export interface ConfigSnapshot {
  config: AppConfig;
  config_revision: number;
}
export interface ApiError {
  code: string;
  message: string;
  field_errors?: Record<string, string>;
}
export interface AppState {
  active_profile_id?: string | null;
  active_profile_name?: string | null;
  language: "pl" | "en";
  active_platform: Platform | null;
  active_channel: string | null;
  status: string;
  output: string;
  generation: number;
  active_config_revision: number | null;
  config_revision: number | null;
  instance_id: string;
  error: ApiError | null;
  config_error: ApiError | null;
  recovery_data: unknown;
}
export interface AppEvent {
  id: number;
  instance_id: string;
  timestamp: string;
  type: string;
  payload: Record<string, unknown>;
}
export interface Snapshot {
  type: "snapshot";
  state: AppState;
  events: AppEvent[];
  watermark: number;
  instance_id: string;
}

export interface TwitchAuthState {
  configured: boolean;
  status: "disconnected" | "pending" | "connected" | "error";
  login: string | null;
  error: ApiError | null;
  attempt_id: number;
}
export interface TwitchActivation extends TwitchAuthState {
  user_code: string;
  verification_uri: string;
  expires_at: number;
}
