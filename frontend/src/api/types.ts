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
  version: 7;
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
  limits?: ControlLimits;
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
  control_stats?: ControlStats;
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

export interface SimulationMessage {
  offset_ms: number;
  user_id: string;
  comment: string;
}
export interface SimulationReport {
  config_revision: number;
  profile_id: string;
  profile_name: string;
  platform: Platform;
  planned_count: number;
  rejected_count: number;
  duration_ms: number;
  decisions: (SimulationMessage & {
    message_index: number;
    reason:
      | "planned"
      | "user_filtered"
      | "no_mapping"
      | "action_cooldown"
      | "user_cooldown"
      | "queue_full"
      | "expired";
    started_at_ms: number | null;
    finished_at_ms: number | null;
    steps: {
      type: "press" | "hold" | "wait";
      keys: string[];
      start_ms: number;
      end_ms: number;
      duration_ms: number;
    }[];
  })[];
}

export interface ControlLimits {
  action_cooldown_ms: number;
  viewer_cooldown_ms: number;
  queue_capacity: number;
  action_ttl_ms: number;
}
export interface ControlStats {
  counts: Record<string, number>;
  recent: { id: number; reason: string; actor_id: string; comment: string; mapping_id: string }[];
}
