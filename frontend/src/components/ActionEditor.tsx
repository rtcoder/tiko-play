import { KeyOptions } from "./KeyOptions";
import type { ActionDefinition, ActionStep } from "../api/types";
import { actionError, keyLabel } from "../state/actions";
import { t } from "../i18n";

type Props = {
  action: ActionDefinition;
  onChange: (value: ActionDefinition) => void;
  keys: string[];
  mappingNumber: number;
};
export function ActionEditor({ action, onChange, keys, mappingNumber }: Props) {
  const update = (index: number, step: ActionStep) =>
    onChange({ steps: action.steps.map((s, i) => (i === index ? step : s)) });
  const move = (index: number, offset: number) => {
    const steps = [...action.steps];
    [steps[index], steps[index + offset]] = [
      steps[index + offset],
      steps[index],
    ];
    onChange({ steps });
  };
  const error = actionError(action);
  const total = action.steps.reduce(
    (sum, step) => sum + (step.type === "press" ? 0 : step.duration_ms),
    0,
  );
  return (
    <div
      className="action-editor"
      role="group"
      aria-label={t("Akcja mapowania {number}", { number: mappingNumber })}
    >
      {action.steps.map((step, index) => (
        <div className="action-step" key={index}>
          <div className="step-heading">
            <span className="step-number">{index + 1}.</span>
            <label className="step-type">
              <span>{t("Akcja")}</span>
              <select
                aria-label={t("Typ kroku {number}", { number: index + 1 })}
                value={step.type}
                onChange={(e) => {
                  const type = e.target.value as ActionStep["type"];
                  const selected = step.type === "wait" ? [] : step.keys;
                  update(
                    index,
                    type === "wait"
                      ? { type, duration_ms: 100 }
                      : type === "hold"
                        ? { type, keys: selected, duration_ms: 100 }
                        : { type, keys: selected },
                  );
                }}
              >
                <option value="press">{t("Naciśnięcie")}</option>
                <option value="hold">{t("Przytrzymanie")}</option>
                <option value="wait">{t("Pauza")}</option>
              </select>
            </label>
            {step.type !== "press" && (
              <label className="step-duration">
                <span>{t("Czas (ms)")}</span>
                <input
                  type="number"
                  min={step.type === "hold" ? 50 : 10}
                  max={3000}
                  step={1}
                  aria-label={t("Czas kroku {number} (ms)", {
                    number: index + 1,
                  })}
                  value={Number.isNaN(step.duration_ms) ? "" : step.duration_ms}
                  onChange={(e) =>
                    update(index, {
                      ...step,
                      duration_ms:
                        e.target.value === "" ? NaN : Number(e.target.value),
                    })
                  }
                />
              </label>
            )}
            <div className="step-order">
              <button
                disabled={index === 0}
                aria-label={t("Przesuń krok {number} w górę", {
                  number: index + 1,
                })}
                onClick={() => move(index, -1)}
              >
                ↑
              </button>
              <button
                disabled={index === action.steps.length - 1}
                aria-label={t("Przesuń krok {number} w dół", {
                  number: index + 1,
                })}
                onClick={() => move(index, 1)}
              >
                ↓
              </button>
              <button
                disabled={action.steps.length === 1}
                aria-label={t("Usuń krok {number}", { number: index + 1 })}
                onClick={() =>
                  onChange({
                    steps: action.steps.filter((_, i) => i !== index),
                  })
                }
              >
                {t("Usuń krok")}
              </button>
            </div>
          </div>
          {step.type !== "wait" && (
            <div className="key-picker">
              {step.keys.map((key, i) => (
                <button
                  className="key-chip"
                  key={i}
                  title={t("Usuń klawisz")}
                  onClick={() =>
                    update(index, {
                      ...step,
                      keys: step.keys.filter((_, n) => n !== i),
                    })
                  }
                >
                  {keyLabel(key)}
                  <span>×</span>
                </button>
              ))}
              <select
                aria-label={
                  action.steps.length === 1
                    ? t("Dodaj klawisz {number}", { number: mappingNumber })
                    : t("Dodaj klawisz do kroku {number}", {
                        number: index + 1,
                      })
                }
                value=""
                onChange={(e) => {
                  if (e.target.value)
                    update(index, {
                      ...step,
                      keys: [...step.keys, e.target.value],
                    });
                }}
              >
                <option value="">{t("Dodaj klawisz…")}</option>
                <KeyOptions keys={keys} />
              </select>
            </div>
          )}
        </div>
      ))}
      <div className="step-add">
        <button
          disabled={action.steps.length >= 20}
          onClick={() =>
            onChange({ steps: [...action.steps, { type: "press", keys: [] }] })
          }
        >
          {t("+ Dodaj krok")}
        </button>
        <button
          disabled={action.steps.length >= 20}
          onClick={() =>
            onChange({
              steps: [...action.steps, { type: "wait", duration_ms: 100 }],
            })
          }
        >
          {t("+ Dodaj pauzę")}
        </button>
        <span>{t("Kroki: {count} / 20", { count: action.steps.length })}</span>
        <span>
          {t("Łącznie: {duration} / 10000 ms", {
            duration: Number.isFinite(total) ? total : "—",
          })}
        </span>
      </div>
      {error && (
        <p className="action-error" role="alert">
          {t(error)}
        </p>
      )}
    </div>
  );
}
