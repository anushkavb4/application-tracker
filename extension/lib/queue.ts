import { getConfig, QUEUE_KEY } from "./config";
import type { CapturedEvent, QueueState } from "./types";

const EMPTY_QUEUE: QueueState = { events: [], totalSent: 0, totalDropped: 0 };

async function readQueue(): Promise<QueueState> {
  const stored = await chrome.storage.local.get(QUEUE_KEY);
  return { ...EMPTY_QUEUE, ...(stored[QUEUE_KEY] ?? {}) };
}

async function writeQueue(queue: QueueState): Promise<void> {
  await chrome.storage.local.set({ [QUEUE_KEY]: queue });
}

export async function enqueue(event: CapturedEvent): Promise<void> {
  const queue = await readQueue();
  if (!queue.events.some((item) => item.client_event_id === event.client_event_id)) {
    queue.events.push(event);
    await writeQueue(queue);
  }
}

export async function getQueueState(): Promise<QueueState> {
  return readQueue();
}

export async function flushQueue(): Promise<QueueState> {
  const config = await getConfig();
  const queue = await readQueue();

  if (!queue.events.length || !config.apiKey) {
    return queue;
  }

  try {
    const response = await fetch(`${config.apiBaseUrl.replace(/\/$/, "")}/api/events/batch`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": config.apiKey,
      },
      body: JSON.stringify({ events: queue.events }),
    });

    if (response.ok) {
      const result = await response.json() as { accepted?: number; duplicates?: number };
      queue.totalSent += (result.accepted ?? 0) + (result.duplicates ?? 0);
      queue.events = [];
      queue.lastSentAt = new Date().toISOString();
      delete queue.lastError;
      await writeQueue(queue);
      return queue;
    }

    if (response.status === 422) {
      queue.totalDropped += queue.events.length;
      queue.events = [];
      queue.lastError = "Dropped invalid event batch (HTTP 422)";
      await writeQueue(queue);
      return queue;
    }

    throw new Error(`Backend returned HTTP ${response.status}`);
  } catch (error) {
    queue.lastError = error instanceof Error ? error.message : "Unknown backend error";
    await writeQueue(queue);
    return queue;
  }
}
