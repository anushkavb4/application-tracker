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
  first_seen_at: string;
  last_seen_at: string;
  applied_at: string | null;
  notes: string | null;
};

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

export type ApiErrorCode =
  | "not_configured"
  | "backend_unavailable"
  | "invalid_api_key"
  | "validation_error"
  | "backend_error";
