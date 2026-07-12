export type PrintMode = "natural" | "fit-page" | "fit-width" | "split-generation";

export type PrintOrientation = "portrait" | "landscape";

export type PrintSettings = {
  mode: PrintMode;
  orientation: PrintOrientation;
  generationsPerPage: number;
};

export type PrintPage = {
  id: string;
  title: string;
  memberIds: string[];
  scale?: number;
};

export const DEFAULT_PRINT_SETTINGS: PrintSettings = {
  mode: "natural",
  orientation: "portrait",
  generationsPerPage: 3,
};

export const PRINT_SETTINGS_STORAGE_KEY = "ft.print.v1";

export function loadPrintSettings(): PrintSettings {
  try {
    const raw = localStorage.getItem(PRINT_SETTINGS_STORAGE_KEY);
    if (!raw) return DEFAULT_PRINT_SETTINGS;
    const parsed = JSON.parse(raw) as Partial<PrintSettings>;
    return {
      mode: parsed.mode ?? DEFAULT_PRINT_SETTINGS.mode,
      orientation: parsed.orientation ?? DEFAULT_PRINT_SETTINGS.orientation,
      generationsPerPage: parsed.generationsPerPage ?? DEFAULT_PRINT_SETTINGS.generationsPerPage,
    };
  } catch {
    return DEFAULT_PRINT_SETTINGS;
  }
}

export function savePrintSettings(settings: PrintSettings): void {
  localStorage.setItem(PRINT_SETTINGS_STORAGE_KEY, JSON.stringify(settings));
}
