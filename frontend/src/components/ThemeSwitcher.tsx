import { t } from "../i18n";
import { useEffect, useState } from "react";

type Theme = "classic" | "glass";
const storageKey = "tikoplay-theme";

export function ThemeSwitcher() {
  const [theme, setTheme] = useState<Theme>(() => {
    try {
      return localStorage.getItem(storageKey) === "glass" ? "glass" : "classic";
    } catch {
      return "classic";
    }
  });
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem(storageKey, theme);
    } catch {
      // The switch also works when browser storage is unavailable.
    }
    return () => {
      delete document.documentElement.dataset.theme;
    };
  }, [theme]);
  return (
    <div
      className="theme-switcher"
      role="group"
      aria-label={t("Wygląd panelu")}
    >
      {(["classic", "glass"] as const).map((value) => (
        <button
          key={value}
          type="button"
          aria-pressed={theme === value}
          onClick={() => setTheme(value)}
        >
          {value === "classic" ? t("Klasyczny") : "Glass"}
        </button>
      ))}
    </div>
  );
}
