import type { TrackerConfig } from "./types";

export const CONFIG_KEY = "tracker_config";
export const QUEUE_KEY = "tracker_queue";
export const CHAIN_PREFIX = "tracker_chain_";
export const FLUSH_ALARM = "tracker_flush";
export const DEFAULT_API_BASE_URL = "http://localhost:8000";
export const CHAIN_TTL_MS = 30 * 60 * 1000;

const ATS_HOST_RE = [
  /(^|\.)greenhouse\.io$/i,
  /(^|\.)lever\.co$/i,
  /(^|\.)myworkdayjobs\.com$/i,
  /(^|\.)ashbyhq\.com$/i,
  /(^|\.)smartrecruiters\.com$/i,
  /(^|\.)icims\.com$/i,
  /(^|\.)taleo\.net$/i,
  /(^|\.)jobvite\.com$/i,
];

export const DEFAULT_CONFIG: TrackerConfig = {
  apiBaseUrl: DEFAULT_API_BASE_URL,
  apiKey: "",
};

export function isAtsHost(url: string): boolean {
  try {
    const hostname = new URL(url).hostname;
    return ATS_HOST_RE.some((pattern) => pattern.test(hostname));
  } catch {
    return false;
  }
}

export async function getConfig(): Promise<TrackerConfig> {
  const stored = await chrome.storage.local.get(CONFIG_KEY);
  return { ...DEFAULT_CONFIG, ...(stored[CONFIG_KEY] ?? {}) };
}
