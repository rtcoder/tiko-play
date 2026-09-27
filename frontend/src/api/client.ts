import type { AppState, AppConfig, ConfigSnapshot } from "./types";
let csrf = "";
export class RequestError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number,
    public field_errors: Record<string, string> = {},
  ) {
    super(message);
  }
}
export async function request<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const response = await fetch(path, {
    method,
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      ...(csrf ? { "X-CSRF-Token": csrf } : {}),
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  const data = await response.json();
  if (!response.ok)
    throw new RequestError(
      data.code ?? "request_error",
      data.message ?? "Nie udało się wykonać operacji.",
      response.status,
      data.field_errors,
    );
  return data;
}
export async function bootstrapSession() {
  const token = new URLSearchParams(location.hash.slice(1)).get("token");
  if (location.hash)
    history.replaceState(null, "", location.pathname + location.search);
  const session = token
    ? await request<{ csrf_token: string }>("/api/session", "POST", { token })
    : await request<{ csrf_token: string }>("/api/session");
  csrf = session.csrf_token;
}
export const fetchState = () => request<AppState>("/api/state");
export const configApi = {
  load: () => request<ConfigSnapshot>("/api/config"),
  save: (config: AppConfig, expected_revision: number) =>
    request<ConfigSnapshot>("/api/config", "PUT", {
      config,
      expected_revision,
    }),
  start: (expected_revision: number) =>
    request<AppState>("/api/listener/start", "POST", { expected_revision }),
};
