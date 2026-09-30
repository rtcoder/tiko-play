import type { ActionDefinition } from "../api/types";
export interface OverlayPresentation {
  show_commands: boolean;
  show_last_action: boolean;
  show_actor: boolean;
  show_status: boolean;
  font_size: number;
  accent: string;
}
export interface OverlaySettings extends OverlayPresentation {
  enabled: boolean;
  port: number;
}
export interface OverlayState {
  settings: OverlaySettings;
  running: boolean;
  url: string | null;
  error: string | null;
}
export interface OverlaySnapshot {
  schema_version: 1;
  sequence: number;
  mode: "direct";
  paused: boolean;
  language: "pl" | "en";
  commands: { comment: string; action: ActionDefinition }[];
  last_action: {
    id: number;
    comment: string;
    actor?: string;
    action: ActionDefinition;
  } | null;
  presentation: OverlayPresentation;
}
export type OverlayConnection =
  "connecting" | "connected" | "disconnected" | "invalid";
