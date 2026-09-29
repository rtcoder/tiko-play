import { ActionEditor } from "./ActionEditor";
import { mappingAction } from "../state/actions";
import { t } from "../i18n";
import { useState } from "react";
import type { Mapping } from "../api/types";
type Props = {
  mappings: Mapping[];
  onChange: (m: Mapping[]) => void;
  presets: Record<string, { trigger: string; keys: string[] }[]>;
  keys: string[];
};
export function MappingEditor({ mappings, onChange, presets, keys }: Props) {
  const [preset, setPreset] = useState("");
  const update = (id: string, patch: Partial<Mapping>) =>
    onChange(mappings.map((m) => (m.id === id ? { ...m, ...patch } : m)));
  return (
    <section className="card mapping-card">
      <div className="section-heading">
        <div>
          <span className="eyebrow">{t("KOMENTARZ → AKCJA")}</span>
          <h2>{t("Mapowania klawiszy")}</h2>
          <p>{t("Widz pisze komentarz. TikoPlay wykonuje Twoją akcję.")}</p>
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
      <div className="table-labels">
        <span>{t("Komentarz widza")}</span>
        <span>{t("Akcja / sekwencja")}</span>
        <span />
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
      {mappings.map((m, index) => (
        <div className="mapping-row" key={m.id}>
          <div className="trigger-input">
            <span>{String(index + 1).padStart(2, "0")}</span>
            <input
              aria-label={t("Komentarz {number}", { number: index + 1 })}
              placeholder={t("np. lewo")}
              value={m.trigger}
              onChange={(e) => update(m.id, { trigger: e.target.value })}
            />
          </div>
          <ActionEditor
            action={mappingAction(m)}
            keys={keys}
            mappingNumber={index + 1}
            onChange={(action) => {
              const { keys: _legacyKeys, ...rest } = m;
              onChange(
                mappings.map((item) =>
                  item.id === m.id ? { ...rest, action } : item,
                ),
              );
            }}
          />
          <button
            className="icon-button danger"
            aria-label={t("Usuń mapowanie")}
            onClick={() =>
              onChange(mappings.filter((item) => item.id !== m.id))
            }
          >
            ×
          </button>
        </div>
      ))}
      <div className="card-foot">
        {t(
          "Kilka klawiszy w kroku to jednoczesna kombinacja. Do 20 kroków, łącznie do 10 s przytrzymań i pauz. Stop przerywa sekwencję.",
        )}
      </div>
    </section>
  );
}
