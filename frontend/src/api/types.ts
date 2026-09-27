export interface Mapping {
  id: string;
  trigger: string;
  keys: string[];
  [key: string]: unknown;
}
export type Platform = "tiktok" | "twitch";
export interface ChannelConfig {
  channel: string;
  target_user: string;
  [key: string]: unknown;
}
export interface AppConfig {
  version: 3;
  platform: Platform;
  tiktok: ChannelConfig;
  twitch: ChannelConfig;
  mappings: Mapping[];
  show_logs: boolean;
  countdown_enabled: boolean;
  [key: string]: unknown;
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
