import { CHAIN_PREFIX, CHAIN_TTL_MS, FLUSH_ALARM, getConfig, isAtsHost } from "../lib/config";
import { enqueue, flushQueue, getQueueState } from "../lib/queue";
import type { CapturedEvent, TriggerType } from "../lib/types";

type ChainState = { id: string; updatedAt: number; url: string };

async function getChain(tabId: number): Promise<ChainState | undefined> {
  const key = `${CHAIN_PREFIX}${tabId}`;
  const stored = await chrome.storage.session.get(key);
  const chain = stored[key] as ChainState | undefined;
  if (!chain || Date.now() - chain.updatedAt > CHAIN_TTL_MS) {
    await chrome.storage.session.remove(key);
    return undefined;
  }
  return chain;
}

async function setChain(tabId: number, chain: ChainState): Promise<void> {
  await chrome.storage.session.set({ [`${CHAIN_PREFIX}${tabId}`]: chain });
}

async function capture(
  url: string,
  pageTitle: string,
  triggerType: TriggerType,
  tabId?: number,
  chainId?: string,
): Promise<void> {
  const event: CapturedEvent = {
    client_event_id: crypto.randomUUID(),
    url,
    page_title: pageTitle || "Untitled page",
    trigger_type: triggerType,
    tab_id: tabId,
    nav_chain_id: chainId,
    captured_at: new Date().toISOString(),
    payload: {},
  };
  await enqueue(event);
  await flushQueue();
}

export default defineBackground(() => {
  void chrome.alarms.create(FLUSH_ALARM, { periodInMinutes: 1 });
  chrome.runtime.onInstalled.addListener(async () => {
    await chrome.alarms.create(FLUSH_ALARM, { periodInMinutes: 1 });
  });

  chrome.alarms.onAlarm.addListener(async (alarm) => {
    if (alarm.name === FLUSH_ALARM) {
      await flushQueue();
    }
  });

  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    void (async () => {
      if (message.type === "capture_intent") {
        const tabId = sender.tab?.id;
        const chainId = crypto.randomUUID();
        if (tabId !== undefined) {
          await setChain(tabId, { id: chainId, updatedAt: Date.now(), url: message.url });
        }
        await capture(message.url, message.pageTitle, "intent_click", tabId, chainId);
        sendResponse({ ok: true });
        return;
      }

      if (message.type === "capture_submit") {
        const tabId = sender.tab?.id;
        const chain = tabId === undefined ? undefined : await getChain(tabId);
        await capture(message.url, message.pageTitle, "form_submit", tabId, chain?.id);
        sendResponse({ ok: true });
        return;
      }

      if (message.type === "get_status") {
        const queue = await getQueueState();
        const config = await getConfig();
        sendResponse({ ok: true, queue, config: { apiBaseUrl: config.apiBaseUrl, hasApiKey: Boolean(config.apiKey) } });
        return;
      }

      if (message.type === "flush") {
        sendResponse({ ok: true, queue: await flushQueue() });
        return;
      }

      sendResponse({ ok: false, error: "Unknown message type" });
    })();
    return true;
  });

  chrome.webNavigation.onCommitted.addListener(async (details) => {
    if (details.frameId !== 0 || !isAtsHost(details.url)) {
      return;
    }
    const chain = await getChain(details.tabId);
    if (!chain) {
      return;
    }
    await setChain(details.tabId, { ...chain, updatedAt: Date.now(), url: details.url });
    await capture(details.url, details.url, "ats_nav", details.tabId, chain.id);
  });
});
