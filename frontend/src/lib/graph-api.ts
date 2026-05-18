/**
 * AgriSearch - Graph API Client.
 * TypeScript client for bibliographic graph visualization endpoints.
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

// ── Graph Types ──

export interface GraphNode {
  id: string;
  label: string;
  title: string;
  color: { background?: string; border?: string; highlight?: string; hover?: string };
  size: number;
  shape: string;
  status: string;
  cluster?: number;
}

export interface GraphEdge {
  from: string;
  to: string;
  arrows?: string;
  color: { color?: string; highlight?: string; hover?: string };
  width: number;
  dashes?: number[];
  cosine_similarity?: number;
  shared_keywords?: string[];
}

export interface GraphMetadata {
  total_nodes: number;
  total_edges: number;
  total_included: number;
  total_external: number;
  most_cited: Array<{ id: string; label: string; citation_count: number }>;
  bridge_articles: Array<{ id: string; label: string; betweenness: number }>;
  density: number;
  threshold?: number;
  num_clusters?: number;
  cluster_sizes?: Record<string, number>;
}

export interface GraphResponse {
  graph_type: "citation" | "thematic";
  project_id: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  metadata: GraphMetadata;
}

export interface GraphStatsResponse {
  project_id: string;
  citation_graph: Record<string, any>;
  thematic_graph: Record<string, any>;
  total_included_articles: number;
  total_references: number;
  build_status: "ready" | "not_built" | "partial";
}

export interface NeighborResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface BuildGraphsResponse {
  status: string;
  reference_extraction: Record<string, any>;
  citation_graph: Record<string, any>;
  thematic_graph: Record<string, any>;
  citation_path: string;
}

// ── Graph API ──

export async function buildGraphs(projectId: string): Promise<BuildGraphsResponse> {
  return request(`/graphs/${projectId}/build`, { method: "POST" });
}

export async function getCitationGraph(
  projectId: string,
  params?: {
    year_min?: number;
    year_max?: number;
    status?: "included" | "cited_external";
    depth?: number;
  },
): Promise<GraphResponse> {
  const qs = new URLSearchParams();
  if (params?.year_min) qs.set("year_min", String(params.year_min));
  if (params?.year_max) qs.set("year_max", String(params.year_max));
  if (params?.status) qs.set("status", params.status);
  if (params?.depth) qs.set("depth", String(params.depth));
  const query = qs.toString();
  return request(`/graphs/${projectId}/citation${query ? `?${query}` : ""}`);
}

export async function getThematicGraph(
  projectId: string,
  threshold = 0.75,
): Promise<GraphResponse> {
  return request(`/graphs/${projectId}/thematic?threshold=${threshold}`);
}

export async function getArticleNeighbors(
  projectId: string,
  doi: string,
  depth = 1,
): Promise<NeighborResponse> {
  return request(`/graphs/${projectId}/article/${encodeURIComponent(doi)}/neighbors?depth=${depth}`);
}

export async function getGraphStats(projectId: string): Promise<GraphStatsResponse> {
  return request(`/graphs/${projectId}/stats`);
}
