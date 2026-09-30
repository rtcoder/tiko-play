import { t } from "../i18n";
import { keyLabel } from "../state/actions";

const common = [
  "up",
  "down",
  "left",
  "right",
  "w",
  "a",
  "s",
  "d",
  "space",
  "enter",
  "esc",
  "shift",
  "ctrl",
  "alt",
];
export function KeyOptions({ keys }: { keys: string[] }) {
  const popular = common.filter((key) => keys.includes(key));
  const other = keys.filter((key) => !popular.includes(key));
  const options = (items: string[]) =>
    items.map((key) => (
      <option key={key} value={key}>
        {keyLabel(key)}
      </option>
    ));
  return (
    <>
      {popular.length > 0 && (
        <optgroup label={t("Najczęściej używane")}>{options(popular)}</optgroup>
      )}
      {other.length > 0 && (
        <optgroup label={t("Pozostałe klawisze")}>{options(other)}</optgroup>
      )}
    </>
  );
}
