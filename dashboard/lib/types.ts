export type Application = {
  id: string;
  dedup_key: string;
  status_source: string;
  company_name: string | null;
  role: string | null;
  ats: string | null;
  external_id: string | null;
  url: string;
  status: string;
  confidence: number;
  manual_fields: string[];
  first_seen_at: string;
  last_seen_at: string;
  applied_at: string | null;
  notes: string | null;
};

export type ApplicationCorrection = Partial<
  Pick<Application, "company_name" | "role" | "status" | "notes">
>;

export type ApplicationList = {
  items: Application[];
  total: number;
  page: number;
  page_size: number;
};

export type StatsSummary = {
  total: number;
  unattributed_count: number;
  status_counts: Record<string, number>;
  applied_count: number;
  response_count: number;
  response_rate: number;
  applications_over_time: { date: string; count: number }[];
};

export type ReprocessResult = {
  raw_events_processed: number;
  applications_rebuilt: number;
  history_records_rebuilt: number;
  overrides_applied: number;
  errors: string[];
};

export type ParserPattern = {
  id: string;
  ats: string;
  kind: string;
  url_regex: string;
  title_regex: string | null;
  priority: number;
  enabled: boolean;
  created_at: string;
};

export type ParserPatternInput = Pick<
  ParserPattern,
  "ats" | "kind" | "url_regex" | "title_regex" | "priority" | "enabled"
>;

export type PatternTestInput = {
  url: string;
  page_title: string;
  pattern: ParserPatternInput;
};

export type PatternTestResult = {
  matched: boolean;
  ats: string | null;
  company: string | null;
  role: string | null;
  external_id: string | null;
  sources: Record<string, string>;
};

export type ApiErrorCode =
  | "not_configured"
  | "backend_unavailable"
  | "invalid_api_key"
  | "validation_error"
  | "backend_error";
