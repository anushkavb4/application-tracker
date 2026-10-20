"use client";

import {
  CircleAlert,
  FlaskConical,
  Pencil,
  Plus,
  RefreshCw,
  Save,
  Trash2,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";
import type {
  ParserPattern,
  ParserPatternInput,
  PatternTestResult,
} from "@/lib/types";

const EMPTY_PATTERN: ParserPatternInput = {
  ats: "",
  kind: "job_posting",
  url_regex: "",
  title_regex: "",
  priority: 100,
  enabled: true,
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

async function readJson<T>(response: Response): Promise<T> {
  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  if (!response.ok) {
    const detail = isRecord(payload) && typeof payload.detail === "string"
      ? payload.detail
      : `The request failed with HTTP ${response.status}.`;
    throw new Error(detail);
  }
  if (payload === null) throw new Error("The backend returned an empty response.");
  return payload as T;
}

function formatCreatedAt(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "Unknown"
    : new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    }).format(date);
}

export default function PatternManagement() {
  const [patterns, setPatterns] = useState<ParserPattern[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(0);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editorOpen, setEditorOpen] = useState(true);
  const [draft, setDraft] = useState<ParserPatternInput>(EMPTY_PATTERN);
  const [testUrl, setTestUrl] = useState("");
  const [testTitle, setTestTitle] = useState("");
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<PatternTestResult | null>(null);
  const [testError, setTestError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    async function loadPatterns() {
      setLoading(true);
      setError("");
      try {
        const response = await fetch("/api/dashboard/patterns", {
          signal: controller.signal,
          cache: "no-store",
        });
        setPatterns(await readJson<ParserPattern[]>(response));
      } catch (caught) {
        if (controller.signal.aborted) return;
        setPatterns([]);
        setError(caught instanceof Error ? caught.message : "Patterns could not be loaded.");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void loadPatterns();
    return () => controller.abort();
  }, [refreshing]);

  function resetEditor() {
    setEditorOpen(false);
    setEditingId(null);
    setDraft(EMPTY_PATTERN);
    setTestUrl("");
    setTestTitle("");
    setTestResult(null);
    setTestError("");
    setError("");
    setNotice("");
  }

  function newPattern() {
    resetEditor();
    setEditorOpen(true);
  }

  function editPattern(pattern: ParserPattern) {
    setEditorOpen(true);
    setEditingId(pattern.id);
    setDraft({
      ats: pattern.ats,
      kind: pattern.kind,
      url_regex: pattern.url_regex,
      title_regex: pattern.title_regex || "",
      priority: pattern.priority,
      enabled: pattern.enabled,
    });
    setTestUrl("");
    setTestTitle("");
    setTestResult(null);
    setTestError("");
    setError("");
    setNotice("");
  }

  function updateDraft<K extends keyof ParserPatternInput>(
    key: K,
    value: ParserPatternInput[K],
  ) {
    setDraft((current) => ({ ...current, [key]: value }));
    setTestResult(null);
    setTestError("");
  }

  function candidatePattern(): ParserPatternInput {
    return {
      ...draft,
      ats: draft.ats.trim(),
      kind: draft.kind.trim(),
      url_regex: draft.url_regex,
      title_regex: draft.title_regex?.trim() || null,
      priority: Number(draft.priority),
    };
  }

  async function savePattern(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const response = await fetch(
        editingId
          ? `/api/dashboard/patterns/${encodeURIComponent(editingId)}`
          : "/api/dashboard/patterns",
        {
          method: editingId ? "PATCH" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(candidatePattern()),
          cache: "no-store",
        },
      );
      await readJson<ParserPattern>(response);
      resetEditor();
      setNotice(editingId ? "Pattern updated." : "Pattern created.");
      setRefreshing((current) => current + 1);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The pattern could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  async function testCandidate() {
    setTesting(true);
    setTestError("");
    setTestResult(null);
    try {
      const response = await fetch("/api/dashboard/patterns/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: testUrl.trim(),
          page_title: testTitle.trim() || null,
          pattern: candidatePattern(),
        }),
        cache: "no-store",
      });
      setTestResult(await readJson<PatternTestResult>(response));
    } catch (caught) {
      setTestError(caught instanceof Error ? caught.message : "The candidate pattern could not be tested.");
    } finally {
      setTesting(false);
    }
  }

  async function togglePattern(pattern: ParserPattern) {
    setError("");
    setNotice("");
    try {
      const response = await fetch(`/api/dashboard/patterns/${encodeURIComponent(pattern.id)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: !pattern.enabled }),
        cache: "no-store",
      });
      await readJson<ParserPattern>(response);
      setNotice(`Pattern ${pattern.enabled ? "disabled" : "enabled"}.`);
      setRefreshing((current) => current + 1);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The pattern state could not be changed.");
    }
  }

  async function deletePattern(pattern: ParserPattern) {
    if (!window.confirm(`Delete the ${pattern.ats} pattern? Existing raw events are not changed.`)) return;
    setError("");
    setNotice("");
    try {
      const response = await fetch(`/api/dashboard/patterns/${encodeURIComponent(pattern.id)}`, {
        method: "DELETE",
        cache: "no-store",
      });
      if (!response.ok) await readJson<unknown>(response);
      if (editingId === pattern.id) resetEditor();
      setNotice("Pattern deleted.");
      setRefreshing((current) => current + 1);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The pattern could not be deleted.");
    }
  }

  return (
    <section className="pattern-page">
      <div className="page-heading">
        <div>
          <div className="eyebrow"><span className="eyebrow-mark" /> PARSER WORKSPACE</div>
          <h1>Parser patterns</h1>
          <p className="page-subtitle">Tune URL and title matching, then test changes before saving.</p>
        </div>
        <button
          className="review-link"
          type="button"
          onClick={() => setRefreshing((current) => current + 1)}
          disabled={loading}
        >
          <RefreshCw size={14} className={loading ? "spin" : ""} /> Refresh patterns
        </button>
      </div>

      {error && <div className="error-banner" role="alert"><CircleAlert size={16} /><span>{error}</span></div>}
      {notice && <div className="success-banner" role="status">{notice}</div>}

      <section className="panel pattern-panel" aria-label="Parser patterns">
        <div className="panel-heading pattern-list-heading">
          <div><h2 className="panel-title">Pattern catalog</h2><p className="panel-caption">Earlier priorities are evaluated first.</p></div>
          <button className="primary-button" type="button" onClick={newPattern}><Plus size={14} /> New pattern</button>
        </div>
        {loading && patterns.length === 0 ? (
          <div className="loading-state"><span className="loading-line" /><span>Loading patterns</span></div>
        ) : patterns.length === 0 ? (
          <div className="empty-state"><strong>{error ? "Patterns unavailable" : "No patterns found"}</strong><span>{error || "Create a candidate pattern to begin."}</span></div>
        ) : (
          <div className="table-scroll">
            <table className="pattern-table">
              <thead><tr><th>ATS</th><th>Kind</th><th>Priority</th><th>State</th><th>URL regex</th><th>Title regex</th><th>Created</th><th>Actions</th></tr></thead>
              <tbody>
                {patterns.map((pattern) => (
                  <tr key={pattern.id}>
                    <td className="pattern-ats">{pattern.ats}</td>
                    <td>{pattern.kind}</td>
                    <td className="pattern-mono">{pattern.priority}</td>
                    <td><span className={`pattern-state${pattern.enabled ? " enabled" : ""}`}>{pattern.enabled ? "Enabled" : "Disabled"}</span></td>
                    <td><code title={pattern.url_regex}>{pattern.url_regex}</code></td>
                    <td><code title={pattern.title_regex || "Not configured"}>{pattern.title_regex || "—"}</code></td>
                    <td>{formatCreatedAt(pattern.created_at)}</td>
                    <td>
                      <div className="pattern-actions">
                        <button className="icon-button" type="button" aria-label={`Edit ${pattern.ats} pattern`} title="Edit" onClick={() => editPattern(pattern)}><Pencil size={13} /></button>
                        <button className="secondary-button" type="button" onClick={() => void togglePattern(pattern)}>{pattern.enabled ? "Disable" : "Enable"}</button>
                        <button className="icon-button danger-button" type="button" aria-label={`Delete ${pattern.ats} pattern`} title="Delete" onClick={() => void deletePattern(pattern)}><Trash2 size={13} /></button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {editorOpen && (
        <section className="panel pattern-editor">
          <div className="panel-heading">
            <div><h2 className="panel-title">{editingId ? "Edit pattern" : "Create pattern"}</h2><p className="panel-caption">Patterns are stored by the backend and take effect on future parsing or reprocessing.</p></div>
          </div>
          <form className="pattern-form" onSubmit={savePattern}>
            <div className="pattern-fields">
              <label className="edit-field">ATS identifier<input required maxLength={128} value={draft.ats} onChange={(event) => updateDraft("ats", event.target.value)} placeholder="greenhouse" /></label>
              <label className="edit-field">Pattern kind<input required maxLength={32} value={draft.kind} onChange={(event) => updateDraft("kind", event.target.value)} placeholder="ats" /></label>
              <label className="edit-field">Priority<input required type="number" value={draft.priority} onChange={(event) => updateDraft("priority", Number(event.target.value))} /></label>
              <label className="edit-field pattern-checkbox"><input type="checkbox" checked={draft.enabled} onChange={(event) => updateDraft("enabled", event.target.checked)} /> Enabled</label>
              <label className="edit-field pattern-regex-field">URL regex<textarea required value={draft.url_regex} onChange={(event) => updateDraft("url_regex", event.target.value)} rows={3} spellCheck={false} /></label>
              <label className="edit-field pattern-regex-field">Title regex<textarea value={draft.title_regex || ""} onChange={(event) => updateDraft("title_regex", event.target.value)} rows={3} spellCheck={false} /></label>
              <p className="pattern-help">Named groups supported for extraction: <code>company</code>, <code>role</code>, and <code>external_id</code>. URL captures are decoded and slug-normalized; title captures override company and role when present.</p>
            </div>
            <div className="pattern-test">
              <div><h3>Dry-run candidate</h3><p>Testing does not save or activate this pattern.</p></div>
              <label className="edit-field">Test URL<input type="text" inputMode="url" value={testUrl} onChange={(event) => setTestUrl(event.target.value)} placeholder="https://jobs.example.com/acme/123" /></label>
              <label className="edit-field">Page title<input value={testTitle} onChange={(event) => setTestTitle(event.target.value)} placeholder="Senior Engineer at Acme" /></label>
              <button className="secondary-button" type="button" disabled={testing || !testUrl.trim() || !draft.ats.trim() || !draft.url_regex.trim()} onClick={() => void testCandidate()}><FlaskConical size={13} />{testing ? "Testing" : "Test candidate"}</button>
              {testError && <p className="edit-error" role="alert">{testError}</p>}
              {testResult && (
                <div className={`pattern-result${testResult.matched ? " matched" : ""}`} role="status">
                  <strong>{testResult.matched ? "Pattern matched" : "No match"}</strong>
                  <dl>
                    <div><dt>ATS</dt><dd>{testResult.ats || "—"}</dd></div>
                    <div><dt>Company</dt><dd>{testResult.company || "—"}{testResult.sources.company && <small> from {testResult.sources.company}</small>}</dd></div>
                    <div><dt>Role</dt><dd>{testResult.role || "—"}{testResult.sources.role && <small> from {testResult.sources.role}</small>}</dd></div>
                    <div><dt>External ID</dt><dd>{testResult.external_id || "—"}{testResult.sources.external_id && <small> from {testResult.sources.external_id}</small>}</dd></div>
                  </dl>
                </div>
              )}
            </div>
            <div className="edit-actions">
              <button className="primary-button" type="submit" disabled={saving}><Save size={13} />{saving ? "Saving" : editingId ? "Save changes" : "Create pattern"}</button>
              <button className="secondary-button" type="button" disabled={saving} onClick={resetEditor}><X size={13} />Cancel</button>
            </div>
          </form>
        </section>
      )}
    </section>
  );
}
