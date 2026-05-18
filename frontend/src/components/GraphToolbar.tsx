interface Props {
  graphType: "citation" | "thematic";
  threshold: number;
  statusFilter: "all" | "included" | "cited_external";
  layout: "hierarchical" | "force" | "circular";
  onThresholdChange: (t: number) => void;
  onStatusFilterChange: (s: "all" | "included" | "cited_external") => void;
  onLayoutChange: (l: "hierarchical" | "force" | "circular") => void;
  onGraphTypeChange: (t: "citation" | "thematic") => void;
  nodeCount: number;
  edgeCount: number;
}

export default function GraphToolbar({
  graphType, threshold, statusFilter, layout,
  onThresholdChange, onStatusFilterChange, onLayoutChange, onGraphTypeChange,
  nodeCount, edgeCount
}: Props) {
  return (
    <div className="mb-4 bg-slate-900/40 rounded-xl border border-slate-800 p-4">
      <div className="flex flex-wrap items-center gap-4">
        {/* Graph Type Toggle */}
        <div className="flex bg-slate-800 rounded-lg p-1">
          <button
            onClick={() => onGraphTypeChange("citation")}
            className={`px-3 py-1.5 rounded-md text-xs font-bold transition-all ${
              graphType === "citation" ? "bg-emerald-500 text-slate-950" : "text-slate-400 hover:text-white"
            }`}
          >
            Citación
          </button>
          <button
            onClick={() => onGraphTypeChange("thematic")}
            className={`px-3 py-1.5 rounded-md text-xs font-bold transition-all ${
              graphType === "thematic" ? "bg-indigo-500 text-white" : "text-slate-400 hover:text-white"
            }`}
          >
            Temático
          </button>
        </div>

        {/* Threshold Slider (thematic only) */}
        {graphType === "thematic" && (
          <div className="flex items-center gap-2">
            <span className="text-[10px] uppercase tracking-[0.15em] text-slate-500 font-bold">Umbral</span>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={threshold}
              onChange={(e) => onThresholdChange(parseFloat(e.target.value))}
              className="w-24 accent-indigo-500"
            />
            <span className="text-xs text-slate-300 font-mono w-10">{threshold.toFixed(2)}</span>
          </div>
        )}

        {/* Status Filter (citation only) */}
        {graphType === "citation" && (
          <div className="flex items-center gap-2">
            <span className="text-[10px] uppercase tracking-[0.15em] text-slate-500 font-bold">Filtro</span>
            <select
              value={statusFilter}
              onChange={(e) => onStatusFilterChange(e.target.value as any)}
              className="bg-slate-800 border border-slate-700 rounded-lg px-2 py-1 text-xs text-slate-300 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            >
              <option value="all">Todos</option>
              <option value="included">Incluidos</option>
              <option value="cited_external">Externos</option>
            </select>
          </div>
        )}

        {/* Layout Selector */}
        <div className="flex items-center gap-2">
          <span className="text-[10px] uppercase tracking-[0.15em] text-slate-500 font-bold">Layout</span>
          <div className="flex bg-slate-800 rounded-lg p-1">
            {(["force", "hierarchical", "circular"] as const).map((l) => (
              <button
                key={l}
                onClick={() => onLayoutChange(l)}
                className={`px-2 py-1 rounded-md text-[10px] font-bold uppercase transition-all ${
                  layout === l ? "bg-slate-600 text-white" : "text-slate-500 hover:text-slate-300"
                }`}
              >
                {l === "force" ? "Fuerza" : l === "hierarchical" ? "Jerárq." : "Circular"}
              </button>
            ))}
          </div>
        </div>

        {/* Counts */}
        <div className="ml-auto flex items-center gap-4 text-xs text-slate-500">
          <span>{nodeCount} nodos</span>
          <span>{edgeCount} aristas</span>
        </div>
      </div>
    </div>
  );
}
