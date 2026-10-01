import type { ControlLimits } from "../api/types";
export const defaultLimits: ControlLimits = {
  action_cooldown_ms: 300,
  viewer_cooldown_ms: 0,
  queue_capacity: 100,
  action_ttl_ms: 1000,
};
export const limitRanges: Record<keyof ControlLimits, [number, number]> = {
  action_cooldown_ms: [0, 60000],
  viewer_cooldown_ms: [0, 60000],
  queue_capacity: [1, 100],
  action_ttl_ms: [100, 5000],
};
export function validLimits(limits = defaultLimits) {
  return Object.entries(limitRanges).every(([key, [min, max]]) => {
    const value = limits[key as keyof ControlLimits];
    return Number.isInteger(value) && value >= min && value <= max;
  });
}
export const controlReasons: Record<string, string> = {
  execution_error: "Błąd wykonania akcji",
  accepted: "Przyjęto do wykonania",
  executed: "Wykonano",
  user_filtered: "Widz spoza listy dozwolonych",
  no_mapping: "Brak pasującej komendy",
  user_cooldown: "Ten widz steruje zbyt często",
  action_cooldown: "Ta komenda pojawia się zbyt często",
  queue_full: "Brak miejsca w kolejce",
  expired: "Minął czas oczekiwania",
  output_disabled: "Sterowanie wyłączone",
  stale_epoch: "Anulowano po zatrzymaniu sterowania",
};
