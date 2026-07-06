const HANNOM_CONFIG_KEY = "developer_hannom_config";
const API_LOGS_KEY = "developer_api_logs";

export interface HannomClientConfig {
  loginEmail: string;
  apiToken: string;
  ocrId: number;
  ocrLangType: number;
  fontType: number;
  transliterationLangType: number;
  rateLimitPerMinute: number;
  modelPriority: "balanced" | "accuracy" | "speed";
}

export interface DeveloperApiLogEntry {
  id: string;
  timestamp: string;
  method: string;
  path: string;
  status: number;
  message: string;
  apiCode?: string;
}

const DEFAULT_HANNOM_CONFIG: HannomClientConfig = {
  loginEmail: "",
  apiToken: "",
  ocrId: 1,
  ocrLangType: 0,
  fontType: 1,
  transliterationLangType: 1,
  rateLimitPerMinute: 40,
  modelPriority: "balanced",
};

export function loadHannomConfig(): HannomClientConfig {
  try {
    const raw = localStorage.getItem(HANNOM_CONFIG_KEY);
    if (!raw) return { ...DEFAULT_HANNOM_CONFIG };
    return { ...DEFAULT_HANNOM_CONFIG, ...JSON.parse(raw) };
  } catch {
    return { ...DEFAULT_HANNOM_CONFIG };
  }
}

export function saveHannomConfig(config: HannomClientConfig): void {
  localStorage.setItem(HANNOM_CONFIG_KEY, JSON.stringify(config));
}

export function loadDeveloperLogs(): DeveloperApiLogEntry[] {
  try {
    const raw = localStorage.getItem(API_LOGS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as DeveloperApiLogEntry[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function appendDeveloperLog(entry: Omit<DeveloperApiLogEntry, "id" | "timestamp">): void {
  const logs = loadDeveloperLogs();
  logs.unshift({
    ...entry,
    id: crypto.randomUUID(),
    timestamp: new Date().toISOString(),
  });
  localStorage.setItem(API_LOGS_KEY, JSON.stringify(logs.slice(0, 200)));
}

export function clearDeveloperLogs(): void {
  localStorage.removeItem(API_LOGS_KEY);
}
