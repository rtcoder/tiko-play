export interface Mapping {
  id: string;
  trigger: string;
  keys: string[];
  [key: string]: unknown;
}
export interface AppConfig {
  version: 2;
  streamer_id: string;
  /** Allowed nicknames separated by commas, semicolons or newlines; empty = everyone. */
  target_user: string;
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
