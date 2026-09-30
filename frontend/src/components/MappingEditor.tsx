import { KeyOptions } from "./KeyOptions";
import { ActionEditor } from "./ActionEditor";
import { actionError, mappingAction, readableAction } from "../state/actions";
import { t } from "../i18n";
import { useEffect, useId, useState } from "react";
import type { Mapping } from "../api/types";
type Props = {
  mappings: Mapping[];
  onChange: (m: Mapping[]) => void;
  presets: Record<string, { trigger: string; keys: string[] }[]>;
  keys: string[];
};
export function MappingEditor({ mappings, onChange, presets, keys }: Props) {
  const [preset, setPreset] = useState("");
  return (
    <section className="card mapping-card">
      <div className="section-heading">
        <div>
          <span className="eyebrow">{t("KOMENTARZ → AKCJA")}</span>
          <h2>{t("Mapowania klawiszy")}</h2>
          <p>
            {t("Wpisz komentarz i wybierz klawisz. Przykład: „lewo” → ← Lewo.")}
          </p>
        </div>
        <span className="count">
          {mappings.length} {t("mapowań")}
        </span>
      </div>
      <div className="mapping-tools">
        <select
          aria-label={t("Preset")}
          value={preset}
          onChange={(e) => setPreset(e.target.value)}
        >
          <option value="">{t("Wybierz preset…")}</option>
          {Object.keys(presets).map((p) => (
            <option key={p} value={p}>
              {t(p)}
            </option>
          ))}
        </select>
        <button
          disabled={!preset}
          onClick={() => {
            if (
              !mappings.length ||
              confirm(t("Zastąpić obecne mapowania wybranym presetem?"))
            )
              onChange(
                presets[preset].map((m) => ({ ...m, id: crypto.randomUUID() })),
              );
          }}
        >
          {t("Zastosuj preset")}
        </button>
        <button
          className="primary push-right"
          onClick={() =>
            onChange([
              ...mappings,
              { id: crypto.randomUUID(), trigger: "", keys: [] },
            ])
          }
        >
          {t("+ Dodaj mapowanie")}
        </button>
      </div>
      {!mappings.length && (
        <div className="empty">
          <span className="empty-symbol">⌨</span>
          <h3>{t("Twoja gra, zasady widzów")}</h3>
          <p>
            {t("Dodaj pierwszy komentarz lub zacznij od gotowego presetu.")}
          </p>
        </div>
      )}
      <div className="mapping-list">
        {mappings.map((m, index) => (
          <MappingRow
            key={m.id}
            mapping={m}
            number={index + 1}
            keys={keys}
            onChange={(next) =>
              onChange(mappings.map((item) => (item.id === m.id ? next : item)))
            }
            onRemove={() =>
              onChange(mappings.filter((item) => item.id !== m.id))
            }
          />
        ))}
      </div>
      <div className="card-foot">
        {t(
          "Chcesz przytrzymać klawisz lub wykonać kilka ruchów? Otwórz „Więcej opcji” przy mapowaniu.",
        )}
      </div>
    </section>
  );
}

function MappingRow({
  mapping,
  number,
  keys,
  onChange,
  onRemove,
}: {
  mapping: Mapping;
  number: number;
  keys: string[];
  onChange: (mapping: Mapping) => void;
  onRemove: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const panelId = useId();
  const action = mappingAction(mapping);
  const first = action.steps[0];
  const simple =
    action.steps.length === 1 &&
    first.type === "press" &&
    first.keys.length <= 1;
  const error = actionError(action);
  useEffect(() => {
    if (!simple && error) setExpanded(true);
  }, [simple, error]);
  // Never hide an invalid advanced draft behind a collapsed summary.
  const open = expanded || (!simple && !!error);
  const updateAction = (value: typeof action) => {
    const { keys: _legacyKeys, ...rest } = mapping;
    onChange({ ...rest, action: value });
  };
  return (
    <article className={`mapping-item${open ? " is-open" : ""}`}>
      <div className="mapping-overview">
        <label className="mapping-trigger">
          <span>{t("Widz pisze")}</span>
          <input
            aria-label={t("Komentarz {number}", { number })}
            placeholder={t("np. lewo")}
            value={mapping.trigger}
            onChange={(e) => onChange({ ...mapping, trigger: e.target.value })}
          />
        </label>
        <span className="mapping-arrow" aria-hidden="true">
          →
        </span>
        <div className="mapping-result">
          <span className="mapping-label">
            {t(simple ? "Naciśnij klawisz" : "Gra wykonuje")}
          </span>
          {simple ? (
            <select
              aria-label={t("Klawisz mapowania {number}", { number })}
              value={first.type === "press" ? (first.keys[0] ?? "") : ""}
              onChange={(e) =>
                updateAction({
                  steps: [
                    {
                      type: "press",
                      keys: e.target.value ? [e.target.value] : [],
                    },
                  ],
                })
              }
            >
              <option value="">{t("Wybierz klawisz…")}</option>
              <KeyOptions keys={keys} />
            </select>
          ) : (
            <p className="mapping-summary">{readableAction(action)}</p>
          )}
        </div>
        <div className="mapping-row-actions">
          <button
            className="mapping-options"
            aria-expanded={open}
            aria-controls={panelId}
            disabled={!simple && !!error}
            onClick={() => setExpanded(!open)}
          >
            {t(
              open
                ? "Zwiń opcje"
                : simple
                  ? "Więcej opcji"
                  : action.steps.length === 1
                    ? "Edytuj akcję"
                    : "Edytuj sekwencję",
            )}
          </button>
          <button
            className="mapping-remove"
            aria-label={t("Usuń mapowanie")}
            onClick={onRemove}
          >
            {t("Usuń")}
          </button>
        </div>
      </div>
      {open && (
        <div id={panelId} className="mapping-details">
          <div className="mapping-details-heading">
            <strong>{t("Co ma zrobić gra?")}</strong>
            <p>
              {t(
                "Kroki wykonują się od góry do dołu. Klawisze w jednym kroku są wciskane razem.",
              )}
            </p>
          </div>
          <ActionEditor
            action={action}
            keys={keys}
            mappingNumber={number}
            onChange={updateAction}
          />
        </div>
      )}
      {!open && error && (
        <p className="action-error" role="alert">
          {t(error)}
        </p>
      )}
    </article>
  );
}
