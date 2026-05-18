import { useState, useEffect, useCallback } from "react";
import {
  getGraphStats, buildGraphs, getCitationGraph, getThematicGraph,
  type GraphStatsResponse, type GraphResponse, type GraphNode, type GraphEdge
} from "../lib/graph-api";
import GraphVisualization from "./GraphVisualization";
import GraphToolbar from "./GraphToolbar";
import GraphStatsBar from "./GraphStatsBar";
import GraphNodePanel from "./GraphNodePanel";

export default function GraphExplorer() {
  const [projectId, setProjectId] = useState("");
  const [stats, setStats] = useState<GraphStatsResponse | null>(null);
  const [graphData, setGraphData] = useState<GraphResponse | null>(null);
  const [graphType, setGraphType] = useState<"citation" | "thematic">("citation");
  const [loading, setLoading] = useState(false);
  const [building, setBuilding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [threshold, setThreshold] = useState(0.75);
  const [statusFilter, setStatusFilter] = useState<"all" | "included" | "cited_external">("all");
  const [screeningStatus, setScreeningStatus] = useState<"included" | "maybe" | "all">("included");
  const [hasScreeningData, setHasScreeningData] = useState(true);
  const [layout, setLayout] = useState<"hierarchical" | "force" | "circular">("force");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const id = params.get("id");
    if (!id) { window.location.href = "/"; return; }
    setProjectId(id);
    loadStats(id);
  }, []);

  async function loadStats(id: string) {
    try {
      const s = await getGraphStats(id, screeningStatus);
      setStats(s);
      // Fallback to "all" if no screening data exists
      if (s.total_included_articles === 0 && s.total_references === 0) {
        setHasScreeningData(false);
        setScreeningStatus("all");
      }
    } catch (e: any) {
      console.error("Failed to load graph stats", e);
    }
  }

  const handleBuild = async () => {
    setBuilding(true);
    setError(null);
    try {
      await buildGraphs(projectId, screeningStatus);
      await loadStats(projectId);
      await loadGraph(projectId, graphType);
    } catch (e: any) {
      setError(e.message || "Error al construir los grafos");
    } finally {
      setBuilding(false);
    }
  };

  const loadGraph = async (id: string, type: "citation" | "thematic") => {
    setLoading(true);
    setError(null);
    setSelectedNode(null);
    try {
      let data: GraphResponse;
      if (type === "citation") {
        data = await getCitationGraph(id, {
          screening_status: screeningStatus,
          status: statusFilter === "all" ? undefined : statusFilter,
        });
      } else {
        data = await getThematicGraph(id, {
          screening_status: screeningStatus,
          threshold,
        });
      }
      setGraphData(data);
      setGraphType(type);
    } catch (e: any) {
      setError(e.message || "Error al cargar el grafo");
      setGraphData(null);
    } finally {
      setLoading(false);
    }
  };

  const handleNodeSelect = useCallback((node: GraphNode | null) => {
    setSelectedNode(node);
  }, []);

  const handleThresholdChange = (t: number) => {
    setThreshold(t);
    if (graphType === "thematic") loadGraph(projectId, "thematic");
  };

  const handleStatusFilterChange = (s: "all" | "included" | "cited_external") => {
    setStatusFilter(s);
    if (graphType === "citation") loadGraph(projectId, "citation");
  };

  const handleScreeningStatusChange = (s: "included" | "maybe" | "all") => {
    setScreeningStatus(s);
    loadGraph(projectId, graphType);
  };

  const handleLayoutChange = (l: "hierarchical" | "force" | "circular") => {
    setLayout(l);
  };

  return (
    <div className="relative">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-slate-500 mb-6">
        <a href="/" className="hover:text-emerald-400 transition-colors">Proyectos</a>
        <span>/</span>
        <a href={`/project?id=${projectId}`} className="hover:text-emerald-400 transition-colors">Dashboard</a>
        <span>/</span>
        <span className="text-emerald-400">Grafos</span>
      </div>

      {/* Stats Bar */}
      {stats && (
        <GraphStatsBar
          stats={stats}
          onBuild={handleBuild}
          building={building}
          onLoadGraph={loadGraph}
          graphType={graphType}
          loading={loading}
        />
      )}

      {/* Error Banner */}
      {error && (
        <div className="mb-4 px-4 py-3 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400 text-sm">
          {error}
          <button onClick={() => setError(null)} className="ml-4 font-bold hover:underline">Descartar</button>
        </div>
      )}

      {/* Toolbar */}
      {graphData && (
        <GraphToolbar
          graphType={graphType}
          threshold={threshold}
          statusFilter={statusFilter}
          screeningStatus={screeningStatus}
          layout={layout}
          onThresholdChange={handleThresholdChange}
          onStatusFilterChange={handleStatusFilterChange}
          onScreeningStatusChange={handleScreeningStatusChange}
          onLayoutChange={handleLayoutChange}
          onGraphTypeChange={(t) => loadGraph(projectId, t)}
          nodeCount={graphData.nodes.length}
          edgeCount={graphData.edges.length}
          hasScreeningData={hasScreeningData}
        />
      )}

      {/* Main Content */}
      <div className={`grid gap-6 ${selectedNode ? "grid-cols-1 lg:grid-cols-3" : "grid-cols-1"}`}>
        <div className={selectedNode ? "lg:col-span-2" : ""}>
          {loading && (
            <div className="flex items-center justify-center h-96 bg-slate-900/40 rounded-2xl border border-slate-800">
              <div className="w-10 h-10 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
            </div>
          )}
          {!loading && graphData && (
            <GraphVisualization
              nodes={graphData.nodes}
              edges={graphData.edges}
              graphType={graphType}
              layout={layout}
              onNodeSelect={handleNodeSelect}
              selectedNodeId={selectedNode?.id || null}
            />
          )}
          {!loading && !graphData && stats?.build_status === "not_built" && (
            <div className="flex flex-col items-center justify-center h-96 bg-slate-900/40 rounded-2xl border border-slate-800 text-center">
              <svg className="w-16 h-16 text-slate-600 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
              </svg>
              <h3 className="text-xl font-bold text-slate-300 mb-2">No hay grafos construidos</h3>
              <p className="text-slate-500 mb-6 max-w-md">Construye los grafos de citación y temáticos para visualizar las relaciones entre artículos.</p>
              <button
                onClick={handleBuild}
                disabled={building}
                className="px-6 py-3 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-black rounded-xl transition-all disabled:opacity-50"
              >
                {building ? "CONSTRUYENDO..." : "CONSTRUIR GRAFOS"}
              </button>
            </div>
          )}
        </div>

        {/* Node Detail Panel */}
        {selectedNode && (
          <GraphNodePanel node={selectedNode} onClose={() => setSelectedNode(null)} />
        )}
      </div>
    </div>
  );
}
