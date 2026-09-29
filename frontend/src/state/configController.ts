import { mappingAction, actionError } from "./actions";
import type { AppConfig, ConfigSnapshot } from "../api/types";
type Api = {
  load: () => Promise<ConfigSnapshot>;
  save: (c: AppConfig, r: number) => Promise<ConfigSnapshot>;
  start: (r: number) => Promise<unknown>;
};
export interface EditorState {
  draft: AppConfig | null;
  saved: AppConfig | null;
  revision: number;
  saveStatus: "saved" | "dirty" | "saving" | "invalid" | "error";
  error: string;
  conflict: boolean;
}
export class ConfigController {
  state: EditorState = {
    draft: null,
    saved: null,
    revision: 0,
    saveStatus: "saved",
    error: "",
    conflict: false,
  };
  private timer: ReturnType<typeof setTimeout> | undefined;
  private running: Promise<void> | null = null;
  private listeners = new Set<() => void>();
  private generation = 0;
  private remoteRevision = 0;
  private disposed = false;
  constructor(private api: Api) {}
  subscribe = (fn: () => void) => {
    this.listeners.add(fn);
    return () => {
      this.listeners.delete(fn);
    };
  };
  snapshot = () => this.state;
  private update(patch: Partial<EditorState>) {
    this.state = { ...this.state, ...patch };
    this.listeners.forEach((fn) => fn());
  }
  async reload() {
    const stamp = this.generation;
    const result = await this.api.load();
    if (stamp !== this.generation || this.disposed) return;
    clearTimeout(this.timer);
    this.update({
      draft: result.config,
      saved: result.config,
      revision: result.config_revision,
      saveStatus: "saved",
      conflict: false,
      error: "",
    });
  }
  edit(config: AppConfig) {
    this.generation++;
    clearTimeout(this.timer);
    this.update({ draft: config, saveStatus: "dirty", error: "" });
    if (!this.state.conflict)
      this.timer = setTimeout(() => {
        void this.flush().catch(() => {});
      }, 500);
  }
  async remoteChanged(revision: number) {
    this.remoteRevision = Math.max(this.remoteRevision, revision);
    if (this.running || revision <= this.state.revision) return;
    if (this.state.saveStatus === "saved") {
      await this.reload();
    } else
      this.update({
        conflict: true,
        error:
          "Konfiguracja zmieniła się w innym panelu. Porównaj zmiany przed zapisem.",
      });
  }
  flush(): Promise<void> {
    clearTimeout(this.timer);
    if (this.running) return this.running;
    this.running = this.saveLoop().finally(() => {
      this.running = null;
      if (this.remoteRevision > this.state.revision)
        void this.remoteChanged(this.remoteRevision).catch(() => {});
    });
    return this.running;
  }
  private async saveLoop() {
    if (this.state.conflict)
      throw new Error("Najpierw rozwiąż konflikt konfiguracji.");
    while (this.state.draft && this.state.draft !== this.state.saved) {
      const draft = this.state.draft;
      if (
        draft.profiles.some((p) => {
          const triggers = p.mappings.map((m) =>
            m.trigger.trim().toLowerCase(),
          );
          return (
            !p.name.trim() ||
            p.mappings.some((m) => !m.trigger.trim() || !!actionError(mappingAction(m))) ||
            new Set(triggers).size !== triggers.length
          );
        })
      ) {
        this.update({
          saveStatus: "invalid",
          error:
            "Uzupełnij komentarze i popraw kroki akcji. Komentarze nie mogą się powtarzać.",
        });
        throw new Error(this.state.error);
      }
      this.update({ saveStatus: "saving" });
      try {
        const result = await this.api.save(draft, this.state.revision);
        this.update({
          saved: result.config,
          revision: result.config_revision,
          ...(this.state.draft === draft ? { draft: result.config } : {}),
          saveStatus: "saved",
          error: "",
        });
      } catch (e) {
        this.update({
          saveStatus: "error",
          error: e instanceof Error ? e.message : "Błąd zapisu",
          conflict: (e as { status?: number }).status === 409,
        });
        throw e;
      }
    }
  }
  async start() {
    await this.flush();
    return this.api.start(this.state.revision);
  }
  async mutate(transform: (config: AppConfig) => AppConfig): Promise<void> {
    await this.flush();
    if (!this.state.saved) throw new Error("Konfiguracja nie jest gotowa");
    const next = transform(this.state.saved);
    this.generation++;
    const operation = async () => {
      try {
        const result = await this.api.save(next, this.state.revision);
        this.update({
          draft: result.config,
          saved: result.config,
          revision: result.config_revision,
          saveStatus: "saved",
          error: "",
          conflict: false,
        });
      } catch (e) {
        if ((e as { status?: number }).status === 409)
          this.update({
            conflict: true,
            error: e instanceof Error ? e.message : "Błąd zapisu",
          });
        throw e;
      }
    };
    this.running = operation().finally(() => {
      this.running = null;
      if (this.remoteRevision > this.state.revision)
        void this.remoteChanged(this.remoteRevision).catch(() => {});
    });
    return this.running;
  }
  dispose() {
    this.disposed = true;
    clearTimeout(this.timer);
    this.listeners.clear();
  }
}
