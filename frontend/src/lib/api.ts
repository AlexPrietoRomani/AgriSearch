/**
 * AgriSearch - API Client.
 * Centralized HTTP client for all backend interactions.
 */

const API_BASE = import.meta.env.PUBLIC_API_URL || "http://localhost:8000/api/v1";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    let errorMessage = error.detail || `API error: ${res.status}`;
    if (Array.isArray(errorMessage)) {
      errorMessage = errorMessage.map((e: any) => e.msg || JSON.stringify(e)).join(", ");
    }
    throw new Error(typeof errorMessage === "string" ? errorMessage : JSON.stringify(errorMessage));
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

// ── Projects ──

export interface Project {
  id: string;
  name: string;
  description: string | null;
  agri_area: string;
  language: string;
  created_at: string;
  updated_at: string;
  article_count: number;
}

export async function listProjects(): Promise<{ projects: Project[]; total: number }> {
  return request("/projects/");
}

export async function createProject(data: {
  name: string;
  description?: string;
  agri_area?: string;
  language?: string;
}): Promise<Project> {
  return request("/projects/", { method: "POST", body: JSON.stringify(data) });
}

export async function getProject(id: string): Promise<Project> {
  return request(`/projects/${id}`);
}

export async function updateProject(id: string, data: {
  name?: string;
  description?: string;
  agri_area?: string;
  language?: string;
}): Promise<Project> {
  return request(`/projects/${id}`, { method: "PUT", body: JSON.stringify(data) });
}

export async function deleteProject(id: string): Promise<void> {
  return request(`/projects/${id}`, { method: "DELETE" });
}

export async function openProjectFolder(id: string): Promise<{ status: string; path: string }> {
  return request(`/projects/${id}/open-folder`, { method: "POST" });
}

export interface SearchQuery {
  id: string;
  project_id: string;
  raw_input: string;
  generated_query: string;
  databases_used: string;
  total_results: number;
  duplicates_removed: number;
  created_at: string;
}

export async function getProjectSearches(id: string): Promise<SearchQuery[]> {
  return request(`/projects/${id}/searches`);
}

// ── Search ──

export interface GeneratedQuery {
  boolean_query: string;
  suggested_terms: string[];
  pico_breakdown: Record<string, string>;
  explanation: string;
}

export async function buildQuery(data: {
  user_input: string;
  agri_area?: string;
  year_from?: number;
  year_to?: number;
  language?: string;
}): Promise<GeneratedQuery> {
  return request("/search/build-query", { method: "POST", body: JSON.stringify(data) });
}

export interface Article {
  id: string;
  doi: string | null;
  title: string;
  authors: string | null;
  year: number | null;
  abstract: string | null;
  journal: string | null;
  url: string | null;
  keywords: string | null;
  source_database: string;
  download_status: string;
  local_pdf_path: string | null;
  is_duplicate: boolean;
  created_at: string;
}

export interface SearchResults {
  project_id: string;
  query_id: string;
  total_found: number;
  duplicates_removed: number;
  articles: Article[];
  counts_by_source: Record<string, number>;
}

export async function executeSearch(data: {
  project_id: string;
  query: string;
  databases?: string[];
  max_results_per_source?: number;
  year_from?: number;
  year_to?: number;
}): Promise<SearchResults> {
  return request("/search/execute", { method: "POST", body: JSON.stringify(data) });
}

export async function listArticles(
  projectId: string,
  skip = 0,
  limit = 50,
  downloadStatus?: string,
  searchQueryId?: string,
): Promise<{ articles: Article[]; total: number }> {
  const params = new URLSearchParams({ skip: String(skip), limit: String(limit) });
  if (downloadStatus) params.set("download_status", downloadStatus);
  if (searchQueryId) params.set("search_query_id", searchQueryId);
  return request(`/search/articles/${projectId}?${params}`);
}

// ── Download ──

export interface DownloadProgress {
  total: number;
  downloaded: number;
  failed: number;
  paywall: number;
  in_progress: number;
}

export async function downloadArticles(data: {
  project_id: string;
  article_ids?: string[];
}): Promise<DownloadProgress> {
  return request("/search/download", { method: "POST", body: JSON.stringify(data) });
}

// ── Screening ──

export interface ScreeningSession {
  id: string;
  project_id: string;
  search_query_ids: string[];
  reading_language: string;
  translation_model: string;
  total_articles: number;
  reviewed_count: number;
  included_count: number;
  excluded_count: number;
  maybe_count: number;
  created_at: string;
  updated_at: string;
}

export interface ScreeningArticle {
  id: string;
  doi: string | null;
  title: string;
  authors: string | null;
  year: number | null;
  abstract: string | null;
  journal: string | null;
  url: string | null;
  keywords: string | null;
  source_database: string;
  download_status: string;
  local_pdf_path: string | null;
  decision_id: string;
  decision: "pending" | "include" | "exclude" | "maybe";
  exclusion_reason: string | null;
  reviewer_note: string | null;
  translated_abstract: string | null;
  display_order: number;
  decided_at: string | null;
}

export interface ScreeningStats {
  total: number;
  reviewed: number;
  pending: number;
  included: number;
  excluded: number;
  maybe: number;
  progress_percent: number;
}

export async function createScreeningSession(data: {
  project_id: string;
  search_query_ids: string[];
  reading_language?: string;
  translation_model?: string;
}): Promise<ScreeningSession> {
  return request("/screening/sessions", { method: "POST", body: JSON.stringify(data) });
}

export async function getScreeningSession(sessionId: string): Promise<ScreeningSession> {
  return request(`/screening/sessions/${sessionId}`);
}

export async function listProjectScreeningSessions(projectId: string): Promise<ScreeningSession[]> {
  return request(`/screening/sessions/project/${projectId}`);
}

export async function listScreeningArticles(
  sessionId: string,
  skip = 0,
  limit = 50,
  filterDecision?: string,
): Promise<ScreeningArticle[]> {
  const params = new URLSearchParams({ skip: String(skip), limit: String(limit) });
  if (filterDecision) params.set("filter_decision", filterDecision);
  return request(`/screening/sessions/${sessionId}/articles?${params}`);
}

export async function updateDecision(
  decisionId: string,
  data: {
    decision: "include" | "exclude" | "maybe" | "pending";
    exclusion_reason?: string;
    reviewer_note?: string;
  },
): Promise<ScreeningArticle> {
  return request(`/screening/decisions/${decisionId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function getScreeningStats(sessionId: string): Promise<ScreeningStats> {
  return request(`/screening/sessions/${sessionId}/stats`);
}

export async function translateAbstract(data: {
  decision_id: string;
  target_language: string;
}): Promise<{ decision_id: string; translated_abstract: string | null; cached: boolean }> {
  return request("/screening/translate", { method: "POST", body: JSON.stringify(data) });
}

