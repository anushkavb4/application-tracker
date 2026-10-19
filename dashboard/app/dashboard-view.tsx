"use client";

import {
  Activity,
  ArrowDown,
  ArrowDownUp,
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  BriefcaseBusiness,
  Building2,
  CalendarDays,
  ChartNoAxesCombined,
  CircleAlert,
  ExternalLink,
  Eye,
  FileSearch,
  Filter,
  LayoutDashboard,
  RefreshCw,
  Search,
  Send,
  Sparkles,
  UsersRound,
} from "lucide-react";
import { useDeferredValue, useEffect, useState, useTransition, type ReactNode } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ApiErrorCode, Application, ApplicationList, StatsSummary } from "@/lib/types";

const PAGE_SIZE = 25;
const COMMON_STATUSES = ["viewed", "applied", "screening", "interview", "offer", "rejected", "withdrawn"];
const FUNNEL_STAGES = [
  { key: "viewed", label: "Viewed" },
  { key: "applied", label: "Applied" },
  { key: "responses", label: "Responses" },
  { key: "interview", label: "Interview" },
  { key: "offer", label: "Offer" },
];

function displayStatus(status: string) {
  return status.replaceAll("_", " ");
}

function statusClass(status: string) {
  const knownStatuses = ["viewed", "applied", "screening", "interview", "offer", "rejected", "withdrawn"];
  return `status-${knownStatuses.includes(status) ? status : "default"}`;
}

function formatCount(value: number | undefined) {
  return new Intl.NumberFormat("en-US").format(value || 0);
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" }).format(new Date(value));
}

function initials(name: string | null) {
  if (!name) return "?";
  return name.split(/\s+/).slice(0, 2).map((part) => part[0]).join("");
}

function applicationUrl(params: URLSearchParams) {
  const query = params.toString();
  return `/api/dashboard/applications${query ? `?${query}` : ""}`;
}

type DashboardError = { code: ApiErrorCode; message: string };

const ERROR_COPY: Record<ApiErrorCode, { title: string; status: string; hint: string }> = {
  not_configured: { title: "Dashboard not configured.", status: "Not configured", hint: "Add API_BASE_URL and API_KEY to dashboard/.env.local." },
  backend_unavailable: { title: "Tracker API unavailable.", status: "API unavailable", hint: "Start the backend and check API_BASE_URL." },
  invalid_api_key: { title: "API key rejected.", status: "API key rejected", hint: "Make dashboard/.env.local match the backend's API_KEY." },
  validation_error: { title: "Request rejected.", status: "Request rejected", hint: "Adjust the current filters and try again." },
  backend_error: { title: "Tracker API error.", status: "API error", hint: "Check the backend logs, then refresh." },
};

class ApiError extends Error {
  constructor(readonly code: ApiErrorCode, message: string) {
    super(message);
  }
}

async function readResponse<T>(response: Response): Promise<T> {
  let payload: (T & { code?: ApiErrorCode; detail?: unknown }) | null = null;
  try {
    payload = (await response.json()) as T & { code?: ApiErrorCode; detail?: unknown };
  } catch {
    payload = null;
  }
  if (!response.ok || !payload) {
    const code = payload?.code && payload.code in ERROR_COPY ? payload.code : "backend_error";
    const message = typeof payload?.detail === "string" ? payload.detail : `The request failed with HTTP ${response.status}.`;
    throw new ApiError(code, message);
  }
  return payload;
}

export default function DashboardView() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [stats, setStats] = useState<StatsSummary | null>(null);
  const [total, setTotal] = useState(0);
  const [query, setQuery] = useState("");
  const [company, setCompany] = useState("");
  const [ats, setAts] = useState("");
  const [status, setStatus] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [unattributed, setUnattributed] = useState(false);
  const [sort, setSort] = useState("last_seen_at");
  const [order, setOrder] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(1);
  const [refreshKey, setRefreshKey] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<DashboardError | null>(null);
  const [isPending, startTransition] = useTransition();
  const deferredQuery = useDeferredValue(query);

  useEffect(() => {
    const controller = new AbortController();
    const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE), sort, order });
    if (deferredQuery.trim()) params.set("q", deferredQuery.trim());
    if (company.trim()) params.set("company", company.trim());
    if (ats.trim()) params.set("ats", ats.trim());
    if (status) params.set("status", status);
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    if (unattributed) params.set("unattributed", "true");

    async function loadDashboard() {
      setLoading(true);
      try {
        const [applicationResponse, statsResponse] = await Promise.all([
          fetch(applicationUrl(params), { signal: controller.signal, cache: "no-store" }),
          fetch("/api/dashboard/stats", { signal: controller.signal, cache: "no-store" }),
        ]);
        const [applicationData, statsData] = await Promise.all([
          readResponse<ApplicationList>(applicationResponse),
          readResponse<StatsSummary>(statsResponse),
        ]);
        startTransition(() => {
          setApplications(applicationData.items);
          setTotal(applicationData.total);
          setStats(statsData);
          setError(null);
        });
      } catch (caught) {
        if (controller.signal.aborted) return;
        setApplications([]);
        setTotal(0);
        setStats(null);
        setError(caught instanceof ApiError
          ? { code: caught.code, message: caught.message }
          : { code: "backend_unavailable", message: "The dashboard could not reach its API routes." });
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }

    void loadDashboard();
    return () => controller.abort();
  }, [ats, company, dateFrom, dateTo, deferredQuery, order, page, refreshKey, sort, status, unattributed]);

  function changeFilter(setter: (value: string) => void, value: string) {
    setter(value);
    setPage(1);
  }

  function changeSort(column: string) {
    if (column === sort) setOrder((current) => current === "asc" ? "desc" : "asc");
    else {
      setSort(column);
      setOrder(column === "company" || column === "status" ? "asc" : "desc");
    }
    setPage(1);
  }

  const appliedCount = stats?.applied_count || 0;
  const interviewCount = stats?.status_counts.interview || 0;
  const interviewRate = appliedCount ? interviewCount / appliedCount : 0;
  const maxFunnelCount = Math.max(
    stats?.status_counts.viewed || 0,
    stats?.applied_count || 0,
    stats?.response_count || 0,
    interviewCount,
    stats?.status_counts.offer || 0,
    1,
  );
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const firstRecord = total ? (page - 1) * PAGE_SIZE + 1 : 0;
  const lastRecord = Math.min(page * PAGE_SIZE, total);

  function toggleUnattributed() {
    setUnattributed((current) => !current);
    setPage(1);
    document.getElementById("applications")?.scrollIntoView({ behavior: "smooth" });
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#top" aria-label="Application Tracker overview">
          <span className="brand-mark"><BriefcaseBusiness size={17} strokeWidth={2.3} /></span>
          <span><span className="brand-name">Fieldnote</span><span className="brand-caption">Application tracker</span></span>
        </a>
        <span className="nav-label">Workspace</span>
        <nav className="side-nav" aria-label="Main navigation">
          <a className="nav-item active" href="#top" aria-current="page"><LayoutDashboard size={16} /><span>Overview</span></a>
          <a className="nav-item" href="#applications"><BriefcaseBusiness size={16} /><span>Applications</span><span className="nav-count">{stats ? formatCount(stats.total) : "N/A"}</span></a>
          <button className={`nav-item${unattributed ? " active" : ""}`} onClick={toggleUnattributed} type="button">
            <FileSearch size={16} /><span>Needs review</span><span className="nav-count">{stats ? formatCount(stats.unattributed_count) : "N/A"}</span>
          </button>
        </nav>
        <div className="sidebar-bottom"><span className={`status-dot${!error ? " online" : ""}`} /><span>{error ? ERROR_COPY[error.code].status : "Local workspace"}</span></div>
      </aside>

      <main className="main-content" id="top">
        <div className="topline">
          <div className="breadcrumb"><span>Workspace</span><span>/</span><strong>Overview</strong></div>
          <div className="top-actions">
            <span className="today-label">APPLICATION PIPELINE</span>
            <button className="icon-button" type="button" aria-label="Refresh dashboard" title="Refresh dashboard" disabled={loading} onClick={() => setRefreshKey((key) => key + 1)}>
              <RefreshCw size={15} className={loading ? "spin" : ""} />
            </button>
          </div>
        </div>

        <section className="page-heading">
          <div>
            <div className="eyebrow"><span className="eyebrow-mark" /> YOUR SEARCH, IN FOCUS</div>
            <h1>Application overview</h1>
            <p className="page-subtitle">A clear read on the roles you are moving toward.</p>
          </div>
          <button className={`review-link${unattributed ? " selected" : ""}`} type="button" onClick={toggleUnattributed}>
            <FileSearch size={15} /> Unattributed <b>{stats ? formatCount(stats.unattributed_count) : "N/A"}</b>
          </button>
        </section>

        {error && <div className="error-banner" role="alert"><CircleAlert size={16} /><span><strong>{ERROR_COPY[error.code].title}</strong> {error.message}</span></div>}

        <section className="metric-grid" aria-label="Application metrics">
          <Metric label="Tracked roles" value={stats ? formatCount(stats.total) : "N/A"} foot="Across all captured sources" icon={<BriefcaseBusiness size={15} />} />
          <Metric label="Applied" value={stats ? formatCount(stats.applied_count) : "N/A"} foot="Confirmed or progressed" icon={<Send size={15} />} />
          <Metric label="Response rate" value={stats ? `${Math.round(stats.response_rate * 100)}%` : "N/A"} foot={stats ? `${formatCount(stats.response_count)} responses` : "Waiting for data"} icon={<Activity size={15} />} />
          <Metric label="Interview rate" value={stats ? `${Math.round(interviewRate * 100)}%` : "N/A"} foot={stats ? `${formatCount(interviewCount)} interview${interviewCount === 1 ? "" : "s"}` : "Waiting for data"} icon={<UsersRound size={15} />} />
        </section>

        <section className="analytics-grid" aria-label="Application analytics">
          <div className="panel">
            <div className="panel-heading"><div><h2 className="panel-title">Application activity</h2><p className="panel-caption">Roles captured over time</p></div><span className="metric-icon"><ChartNoAxesCombined size={15} /></span></div>
            <div className="chart-wrap">
              {stats?.applications_over_time.length ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={stats.applications_over_time} margin={{ top: 10, right: 10, bottom: 0, left: 0 }}>
                    <defs><linearGradient id="activity-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#71a17c" stopOpacity={0.28} /><stop offset="100%" stopColor="#71a17c" stopOpacity={0.02} /></linearGradient></defs>
                    <CartesianGrid vertical={false} stroke="#edf1ed" />
                    <XAxis dataKey="date" tickFormatter={(value: string) => value.slice(5)} tickLine={false} axisLine={false} tick={{ fill: "#87938a", fontSize: 9 }} minTickGap={24} />
                    <YAxis allowDecimals={false} width={28} tickLine={false} axisLine={false} tick={{ fill: "#87938a", fontSize: 9 }} />
                    <Tooltip labelFormatter={(value) => String(value)} contentStyle={{ border: "1px solid #e3eae4", borderRadius: 5, fontSize: 11 }} />
                    <Area type="monotone" dataKey="count" name="Roles" stroke="#477c57" strokeWidth={2} fill="url(#activity-fill)" activeDot={{ r: 4, fill: "#477c57", stroke: "white", strokeWidth: 2 }} />
                  </AreaChart>
                </ResponsiveContainer>
              ) : <div className="empty-state"><span className="empty-icon"><ChartNoAxesCombined size={17} /></span><strong>{error ? ERROR_COPY[error.code].status : stats ? "No activity yet" : "Waiting for data"}</strong><span>{error ? ERROR_COPY[error.code].hint : "Captured roles will appear here."}</span></div>}
            </div>
          </div>
          <div className="panel">
            <div className="panel-heading"><div><h2 className="panel-title">Pipeline stages</h2><p className="panel-caption">Captured intent to offer</p></div><span className="metric-icon"><Sparkles size={15} /></span></div>
            <div className="funnel-list">
              {FUNNEL_STAGES.map((stage) => {
                const count = stage.key === "applied" ? stats?.applied_count || 0 : stage.key === "responses" ? stats?.response_count || 0 : stats?.status_counts[stage.key] || 0;
                const width = count ? Math.max(4, (count / maxFunnelCount) * 100) : 0;
                return <div className="funnel-row" key={stage.key}><span>{stage.label}</span><div className="funnel-track"><div className="funnel-fill" style={{ width: `${width}%` }} /></div><span className="funnel-value">{stats ? formatCount(count) : "..."}</span></div>;
              })}
            </div>
          </div>
        </section>

        <section className="panel table-panel" id="applications" aria-label="Applications">
          <div className="table-head">
            <div className="table-heading-group"><h2>{unattributed ? "Needs review" : "All applications"}</h2><span className="result-count">{error ? "Unavailable" : loading ? "Loading" : `${formatCount(total)} records`}</span></div>
            {unattributed && <button className="icon-button" type="button" aria-label="Clear needs-review filter" title="Clear needs-review filter" onClick={() => setUnattributed(false)}><Filter size={14} /></button>}
          </div>
          <div className="filters" role="search">
            <label className="filter-control filter-search"><Search size={14} /><input aria-label="Search roles" placeholder="Search roles or links" value={query} onChange={(event) => changeFilter(setQuery, event.target.value)} /></label>
            <label className="filter-control"><Activity size={14} /><select aria-label="Filter by status" value={status} onChange={(event) => changeFilter(setStatus, event.target.value)}><option value="">All statuses</option>{Array.from(new Set([...COMMON_STATUSES, ...Object.keys(stats?.status_counts || {})])).map((value) => <option key={value} value={value}>{displayStatus(value)}</option>)}</select></label>
            <label className="filter-control"><Building2 size={14} /><input aria-label="Filter by company" placeholder="Company" value={company} onChange={(event) => changeFilter(setCompany, event.target.value)} /></label>
            <label className="filter-control"><BriefcaseBusiness size={14} /><input aria-label="Filter by ATS" placeholder="ATS" value={ats} onChange={(event) => changeFilter(setAts, event.target.value)} /></label>
            <label className="filter-control date-control"><CalendarDays size={13} /><input aria-label="From date" type="date" value={dateFrom} onChange={(event) => changeFilter(setDateFrom, event.target.value)} /></label>
            <label className="filter-control date-control"><CalendarDays size={13} /><input aria-label="To date" type="date" value={dateTo} onChange={(event) => changeFilter(setDateTo, event.target.value)} /></label>
          </div>

          {loading && applications.length === 0 ? <div className="loading-state"><span className="loading-line" /><span>Loading applications</span></div> : applications.length === 0 ? (
            <div className="empty-state"><span className="empty-icon"><FileSearch size={17} /></span><strong>{error ? "Tracker data is unavailable" : "No matching applications"}</strong><span>{error ? ERROR_COPY[error.code].hint : "Try adjusting the current filters."}</span></div>
          ) : (
            <div className="table-scroll"><table className="application-table">
              <thead><tr>
                <th><SortButton label="Company" column="company" activeColumn={sort} order={order} onSort={changeSort} /></th>
                <th><SortButton label="Role" column="role" activeColumn={sort} order={order} onSort={changeSort} /></th>
                <th><SortButton label="Status" column="status" activeColumn={sort} order={order} onSort={changeSort} /></th>
                <th>Source</th>
                <th><SortButton label="Confidence" column="confidence" activeColumn={sort} order={order} onSort={changeSort} /></th>
                <th><SortButton label="Last seen" column="last_seen_at" activeColumn={sort} order={order} onSort={changeSort} /></th>
                <th>Link</th>
              </tr></thead>
              <tbody>{applications.map((application) => <ApplicationRow key={application.id} application={application} />)}</tbody>
            </table></div>
          )}

          <div className="table-footer"><span>{stats ? `Showing ${firstRecord}-${lastRecord} of ${formatCount(total)}` : error ? "Application data unavailable" : "Loading records"}</span><div className="pagination">
            <button className="icon-button" type="button" aria-label="Previous page" title="Previous page" disabled={page <= 1 || loading} onClick={() => setPage((current) => Math.max(1, current - 1))}><ArrowLeft size={14} /></button>
            <button className="icon-button" type="button" aria-label="Next page" title="Next page" disabled={page >= pageCount || loading} onClick={() => setPage((current) => Math.min(pageCount, current + 1))}><ArrowRight size={14} /></button>
          </div></div>
        </section>
        <div className="footer-note"><span>FIELDNOTE / PRIVATE BY DEFAULT</span><span>{isPending ? "Updating view..." : "LOCAL DATA"}</span></div>
      </main>
    </div>
  );
}

function Metric({ label, value, foot, icon }: { label: string; value: string; foot: string; icon: ReactNode }) {
  return <article className="metric"><div className="metric-top"><span>{label}</span><span className="metric-icon">{icon}</span></div><strong className="metric-value">{value}</strong><p className="metric-foot">{foot}</p></article>;
}

function SortButton({ label, column, activeColumn, order, onSort }: { label: string; column: string; activeColumn: string; order: "asc" | "desc"; onSort: (column: string) => void }) {
  const icon = column === activeColumn ? order === "asc" ? <ArrowUp size={11} /> : <ArrowDown size={11} /> : <ArrowDownUp size={11} />;
  return <button className="sort-button" type="button" onClick={() => onSort(column)}>{label} {icon}</button>;
}

function ApplicationRow({ application }: { application: Application }) {
  const host = application.url.replace(/^https?:\/\//, "").split("/")[0];
  return <tr>
    <td><div className="company-cell"><span className="company-monogram">{initials(application.company_name)}</span><span className="company-name">{application.company_name || "Unattributed"}</span></div></td>
    <td><span className="role-name">{application.role || "Role not identified"}</span><span className="role-subtitle">{application.external_id || host}</span></td>
    <td><span className={`status-badge ${statusClass(application.status)}`}>{application.status === "viewed" && <Eye size={11} />}{displayStatus(application.status)}</span></td>
    <td>{application.ats || "N/A"}</td>
    <td><span className="confidence-cell"><span className="confidence-track"><span className="confidence-fill" style={{ display: "block", width: `${Math.min(100, Math.max(0, application.confidence))}%` }} /></span>{application.confidence}%</span></td>
    <td>{formatDate(application.last_seen_at)}</td>
    <td><a className="external-link" href={application.url} target="_blank" rel="noreferrer" aria-label={`Open ${application.role || "job listing"}`}><ExternalLink size={13} /></a></td>
  </tr>;
}