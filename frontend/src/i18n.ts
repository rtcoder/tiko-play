import { useSyncExternalStore } from "react";
import english from "../../src/locales/en.json";

export type Language = "pl" | "en";
const catalog: Record<string, string> = english;
let language: Language = document.documentElement.lang === "en" ? "en" : "pl";
const listeners = new Set<() => void>();
export function setLanguage(value: Language) {
  if (value !== "pl" && value !== "en") return;
  document.documentElement.lang = value;
  if (value === language) return;
  language = value;
  listeners.forEach((listener) => listener());
}
export function getLanguage() {
  return language;
}
export function t(
  source: string,
  values: Record<string, string | number> = {},
) {
  const text = language === "en" ? (catalog[source] ?? source) : source;
  return text.replace(/\{(\w+)\}/g, (match, key: string) =>
    String(values[key] ?? match),
  );
}
export function useLanguage() {
  return useSyncExternalStore((listener) => {
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  }, getLanguage);
}
export function statusLabel(status: string) {
  const labels: Record<string, string> = {
    disconnected: "Rozłączony",
    pending: "Oczekiwanie na logowanie",
    stopped: "Zatrzymany",
    connecting: "Łączenie…",
    connected: "Połączony",
    stopping: "Zatrzymywanie…",
    error: "Błąd połączenia",
  };
  return t(labels[status] ?? status);
}
