import { defineConfig } from "wxt";

export default defineConfig({
  manifest: {
    name: "Application Tracker",
    description: "Capture job-application intent without scraping page content.",
    permissions: ["alarms", "storage", "tabs", "webNavigation"],
    host_permissions: ["<all_urls>"],
    action: {
      default_title: "Application Tracker",
      default_popup: "popup.html",
    },
  },
});
