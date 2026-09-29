import type { ActionDefinition, Mapping } from "../api/types";
import { t } from "../i18n";

export function mappingAction(
  mapping: Pick<Mapping, "keys" | "action">,
): ActionDefinition {
  return (
    mapping.action ?? { steps: [{ type: "press", keys: mapping.keys ?? [] }] }
  );
}

export function actionError(action: ActionDefinition): string {
  if (action.steps.length < 1 || action.steps.length > 20)
    return "Sekwencja musi mieć od 1 do 20 kroków.";
  let total = 0;
  for (const step of action.steps) {
    if (step.type !== "wait" && !step.keys.length)
      return "Wybierz klawisze dla każdego naciśnięcia i przytrzymania.";
    if (step.type !== "press") {
      const min = step.type === "hold" ? 50 : 10;
      if (
        !Number.isInteger(step.duration_ms) ||
        step.duration_ms < min ||
        step.duration_ms > 3000
      )
        return step.type === "hold"
          ? "Przytrzymanie: 50–3000 ms (liczba całkowita)."
          : "Pauza: 10–3000 ms (liczba całkowita).";
      total += step.duration_ms;
    }
  }
  return total > 10000
    ? "Łączny czas przytrzymań i pauz nie może przekraczać 10000 ms"
    : "";
}

export function actionSummary(action: ActionDefinition): string {
  return action.steps
    .map((step) =>
      step.type === "wait"
        ? `${t("Pauza")} ${step.duration_ms} ms`
        : `${step.keys.join(" + ")}${step.type === "hold" ? ` (${step.duration_ms} ms)` : ""}`,
    )
    .join(" → ");
}
