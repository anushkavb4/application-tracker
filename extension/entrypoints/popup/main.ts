import { CONFIG_KEY, DEFAULT_API_BASE_URL } from "../../lib/config";
import type { QueueState, TrackerConfig } from "../../lib/types";

const apiUrl = document.querySelector<HTMLInputElement>("#api-url")!;
const apiKey = document.querySelector<HTMLInputElement>("#api-key")!;
const status = document.querySelector<HTMLDivElement>("#status")!;

function show(message: string): void {
  status.textContent = message;
}

async function load(): Promise<void> {
  const response = await chrome.runtime.sendMessage({ type: "get_status" }) as {
    queue: QueueState;
    config: { apiBaseUrl: string; hasApiKey: boolean };
  };
  apiUrl.value = response.config.apiBaseUrl || DEFAULT_API_BASE_URL;
  show(`Queued: ${response.queue.events.length}\nSent: ${response.queue.totalSent}\nDropped: ${response.queue.totalDropped}`);
}

document.querySelector<HTMLButtonElement>("#save")!.addEventListener("click", async () => {
  const stored = await chrome.storage.local.get(CONFIG_KEY);
  const current = (stored[CONFIG_KEY] ?? {}) as Partial<TrackerConfig>;
  const config: TrackerConfig = {
    apiBaseUrl: apiUrl.value.trim(),
    apiKey: apiKey.value || current.apiKey || "",
  };
  await chrome.storage.local.set({ [CONFIG_KEY]: config });
  apiKey.value = "";
  show("Settings saved.");
});

document.querySelector<HTMLButtonElement>("#test")!.addEventListener("click", async () => {
  const response = await fetch(`${apiUrl.value.replace(/\/$/, "")}/health`);
  show(response.ok ? "API is reachable." : `API returned HTTP ${response.status}.`);
});

document.querySelector<HTMLButtonElement>("#flush")!.addEventListener("click", async () => {
  const response = await chrome.runtime.sendMessage({ type: "flush" }) as { queue: QueueState };
  show(`Queued: ${response.queue.events.length}\nSent: ${response.queue.totalSent}\nDropped: ${response.queue.totalDropped}`);
});

void load();
