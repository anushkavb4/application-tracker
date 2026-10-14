import { isAtsHost } from "../lib/config";

const APPLY_LABEL_RE = /\b(apply|easy apply|submit application|apply now|i'?m interested)\b/i;

function actionableText(path: EventTarget[]): string {
  return path
    .filter((node): node is Element => node instanceof Element)
    .slice(0, 6)
    .map((element) => element.textContent ?? element.getAttribute("aria-label") ?? "")
    .join(" ")
    .trim();
}

export default defineContentScript({
  matches: ["<all_urls>"],
  allFrames: true,
  runAt: "document_start",
  main() {
    document.addEventListener(
      "click",
      (event) => {
        const text = actionableText(event.composedPath());
        if (!APPLY_LABEL_RE.test(text)) {
          return;
        }
        void chrome.runtime.sendMessage({
          type: "capture_intent",
          url: location.href,
          pageTitle: document.title,
        });
      },
      true,
    );

    document.addEventListener(
      "submit",
      () => {
        if (!isAtsHost(location.href)) {
          return;
        }
        void chrome.runtime.sendMessage({
          type: "capture_submit",
          url: location.href,
          pageTitle: document.title,
        });
      },
      true,
    );
  },
});
