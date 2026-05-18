import type { GraphNode } from "../lib/graph-api";

interface Props {
  node: GraphNode;
  onClose: () => void;
}

export default function GraphNodePanel({ node, onClose }: Props) {
  return (
    <div className="bg-slate-900/60 rounded-2xl border border-slate-800 p-6 h-fit">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-bold text-white">Detalles del Nodo</h3>
        <button
          onClick={onClose}
          className="p-1 text-slate-500 hover:text-white transition-colors"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div className="space-y-4">
        <div>
          <span className="text-[10px] uppercase tracking-[0.2em] text-slate-500 font-bold">Título</span>
          <p className="text-sm text-slate-200 mt-1 leading-relaxed">{node.title || node.label}</p>
        </div>

        <div>
          <span className="text-[10px] uppercase tracking-[0.2em] text-slate-500 font-bold">DOI / ID</span>
          <p className="text-xs text-slate-400 mt-1 font-mono break-all">{node.id}</p>
        </div>

        <div className="flex gap-4">
          <div>
            <span className="text-[10px] uppercase tracking-[0.2em] text-slate-500 font-bold">Estado</span>
            <span className={`block mt-1 px-2 py-0.5 rounded text-xs font-semibold ${
              node.status === "included"
                ? "bg-emerald-500/10 text-emerald-400"
                : node.status === "cited_external"
                  ? "bg-slate-500/10 text-slate-400"
                  : "bg-amber-500/10 text-amber-400"
            }`}>
              {node.status}
            </span>
          </div>

          {node.cluster !== undefined && node.cluster !== null && (
            <div>
              <span className="text-[10px] uppercase tracking-[0.2em] text-slate-500 font-bold">Cluster</span>
              <span className="block mt-1 px-2 py-0.5 rounded text-xs font-semibold bg-indigo-500/10 text-indigo-400">
                {node.cluster}
              </span>
            </div>
          )}
        </div>

        <div>
          <span className="text-[10px] uppercase tracking-[0.2em] text-slate-500 font-bold">Tamaño</span>
          <p className="text-sm text-slate-300 mt-1">{node.size}</p>
        </div>
      </div>
    </div>
  );
}
