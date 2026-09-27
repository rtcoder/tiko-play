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
          <span className="eyebrow">KOMENTARZ → AKCJA</span>
          <h2>Mapowania klawiszy</h2>
          <p>Widz pisze komentarz. TikoPlay wykonuje Twoją kombinację.</p>
        </div>
        <span className="count">{mappings.length} mapowań</span>
      </div>
      <div className="mapping-tools">
        <select
          aria-label="Preset"
          value={preset}
          onChange={(e) => setPreset(e.target.value)}
        >
          <option value="">Wybierz preset…</option>
          {Object.keys(presets).map((p) => (
            <option key={p}>{p}</option>
          ))}
        </select>
        <button
          disabled={!preset}
          onClick={() => {
            if (
              !mappings.length ||
              confirm("Zastąpić obecne mapowania wybranym presetem?")
            )
              onChange(
                presets[preset].map((m) => ({ ...m, id: crypto.randomUUID() })),
              );
          }}
        >
          Zastosuj preset
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
          + Dodaj mapowanie
        </button>
      </div>
      <div className="table-labels">
        <span>Komentarz widza</span>
        <span>Klawisz lub kombinacja</span>
        <span />
      </div>
      {!mappings.length && (
        <div className="empty">
          <span className="empty-symbol">⌨</span>
          <h3>Twoja gra, zasady widzów</h3>
          <p>Dodaj pierwszy komentarz lub zacznij od gotowego presetu.</p>
        </div>
      )}
      {mappings.map((m, index) => (
        <div className="mapping-row" key={m.id}>
          <div className="trigger-input">
            <span>{String(index + 1).padStart(2, "0")}</span>
            <input
              aria-label={`Komentarz ${index + 1}`}
              placeholder="np. lewo"
              value={m.trigger}
              onChange={(e) => update(m.id, { trigger: e.target.value })}
            />
          </div>
          <div className="key-picker">
            {m.keys.map((key, i) => (
              <button
                className="key-chip"
                key={i}
                title="Usuń klawisz"
                onClick={() =>
                  update(m.id, { keys: m.keys.filter((_, n) => n !== i) })
                }
              >
                {key}
                <span>×</span>
              </button>
            ))}
            <select
              aria-label={`Dodaj klawisz ${index + 1}`}
              value=""
              onChange={(e) => {
                if (e.target.value)
                  update(m.id, { keys: [...m.keys, e.target.value] });
              }}
            >
              <option value="">+ klawisz</option>
              {keys.map((k) => (
                <option key={k} value={k}>
                  {k === " " ? "spacja" : k}
                </option>
              ))}
            </select>
          </div>
          <button
            className="icon-button danger"
            aria-label="Usuń mapowanie"
            onClick={() =>
              onChange(mappings.filter((item) => item.id !== m.id))
            }
          >
            ×
          </button>
        </div>
      ))}
      <div className="card-foot">
        Dopasowanie obejmuje cały komentarz. Kilka klawiszy tworzy jednoczesną
        kombinację.
      </div>
    </section>
  );
}
