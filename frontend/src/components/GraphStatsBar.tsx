import type { GraphStatsResponse } from "../lib/graph-api";

interface Props {
  stats: GraphStatsResponse;
  onBuild: () => void;
  building: boolean;
  onLoadGraph: (id: string, type: "citation" | "thematic") => void;
  graphType: "citation" | "thematic";
  loading: boolean;
}

export default function GraphStatsBar({ stats, onBuild, building, onLoadGraph, graphType, loading }: Props) {
  const isReady = stats.build_status === "ready";
  const isPartial = stats.build_status === "partial";
  const citationMeta = stats.citation_graph;
  const thematicMeta = stats.thematic_graph;

  return (
    <div className="mb-6 bg-slate-900/40 rounded-2xl border border-slate-800 p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-bold text-white">Estado de Grafos</h2>
        <button
          onClick={onBuild}
          disabled={building}
          className="px-4 py-2 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold rounded-xl transition-all text-sm disabled:opacity-50"
        >
          {building ? "Construyendo..." : isReady ? "Reconstruir" : "Construir Grafos"}
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <div className="bg-slate-800/50 rounded-xl p-4">
          <span className="text-[10px] uppercase tracking-[0.2em] text-slate-500 font-bold">Estado</span>
          <span className={`block mt-1 text-sm font-bold ${
            isReady ? "text-emerald-400" : isPartial ? "text-amber-400" : "text-slate-500"
          }`}>
            {isReady ? "Listo" : isPartial ? "Parcial" : "No construido"}
          </span>
        </div>

        <div className="bg-slate-800/50 rounded-xl p-4">
          <span className="text-[10px] uppercase tracking-[0.2em] text-slate-500 font-bold">Artículos</span>
          <span className="block mt-1 text-sm font-bold text-white">{stats.total_included_articles}</span>
        </div>

        <div className="bg-slate-800/50 rounded-xl p-4">
          <span className="text-[10px] uppercase tracking-[0.2em] text-slate-500 font-bold">Referencias</span>
          <span className="block mt-1 text-sm font-bold text-white">{stats.total_references}</span>
        </div>

        <div className="bg-slate-800/50 rounded-xl p-4">
          <span className="text-[10px] uppercase tracking-[0.2em] text-slate-500 font-bold">Clusters</span>
          <span className="block mt-1 text-sm font-bold text-white">
            {thematicMeta?.num_clusters ?? "—"}
          </span>
        </div>
      </div>

      {isReady && (
        <div className="flex gap-3">
          <button
            onClick={() => onLoadGraph(stats.project_id, "citation")}
            disabled={loading}
            className={`flex-1 py-2 rounded-xl font-bold text-sm transition-all ${
              graphType === "citation"
                ? "bg-emerald-500 text-slate-950"
                : "bg-slate-800 text-slate-300 hover:bg-slate-700"
            } disabled:opacity-50`}
          >
            Grafo de Citación
          </button>
          <button
            onClick={() => onLoadGraph(stats.project_id, "thematic")}
            disabled={loading}
            className={`flex-1 py-2 rounded-xl font-bold text-sm transition-all ${
              graphType === "thematic"
                ? "bg-indigo-500 text-white"
                : "bg-slate-800 text-slate-300 hover:bg-slate-700"
            } disabled:opacity-50`}
          >
            Grafo Temático
          </button>
        </div>
      )}
    </div>
  );
}
