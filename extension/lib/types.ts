export type TriggerType = "intent_click" | "ats_nav" | "form_submit";

export interface CapturedEvent {
  client_event_id: string;
  url: string;
  page_title: string;
  referrer?: string;
  trigger_type: TriggerType;
  tab_id?: number;
  nav_chain_id?: string;
  captured_at: string;
  payload: Record<string, unknown>;
}

export interface QueueState {
  events: CapturedEvent[];
  totalSent: number;
  totalDropped: number;
  lastError?: string;
  lastSentAt?: string;
}

export interface TrackerConfig {
  apiBaseUrl: string;
  apiKey: string;
}
