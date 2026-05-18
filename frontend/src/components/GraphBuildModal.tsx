import { useState, useEffect, useRef, useCallback } from "react";
import type { GraphBuildProgressEvent } from "../lib/graph-api";

interface GraphBuildModalProps {
  projectId: string;
  buildId: string | null;
  isOpen: boolean;
  onClose: () => void;
  onComplete: () => void;
}

const API_BASE = import.meta.env.PUBLIC_API_URL || "http://localhost:8000/api/v1";

const stepIcons: Record<string, string> = {
  initializing: "⚙️",
  extracting_references: "📄",
  references_complete: "✅",
  building_citation_graph: "🔗",
  citation_graph_complete: "✅",
  building_thematic_graph: "🌐",
  thematic_graph_complete: "✅",
  complete: "🎉",
  error: "❌",
};

export default function GraphBuildModal({ projectId, buildId, isOpen, onClose, onComplete }: GraphBuildModalProps) {
  const [progress, setProgress] = useState(0);
  const [step, setStep] = useState("initializing");
  const [message, setMessage] = useState("Iniciando construcción del grafo...");
  const [status, setStatus] = useState<"running" | "success" | "error">("running");
  const [results, setResults] = useState<Record<string, any> | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const completedRef = useRef(false);

  const cleanup = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!isOpen || !projectId || !buildId) return;

    completedRef.current = false;
    setProgress(0);
    setStep("initializing");
    setMessage("Iniciando construcción del grafo...");
    setStatus("running");
    setResults(null);
    setErrorMsg(null);

    const url = `${API_BASE}/events/${projectId}`;
    const es = new EventSource(url);
    eventSourceRef.current = es;

    const handler = (event: MessageEvent) => {
      try {
        const data: GraphBuildProgressEvent = JSON.parse(event.data);

        if (data.build_id !== buildId) return;

        if (data.type === "graph_build_progress") {
          setProgress(Math.max(0, data.progress));
          setStep(data.step);
          setMessage(data.message);
        } else if (data.type === "graph_build_success") {
          setProgress(100);
          setStep("complete");
          setMessage(data.message);
          setStatus("success");
          setResults(data.results || null);
          cleanup();
          if (!completedRef.current) {
            completedRef.current = true;
            setTimeout(() => onComplete(), 1500);
          }
        } else if (data.type === "graph_build_error") {
          setProgress(-1);
          setStep("error");
          setMessage(data.message);
          setStatus("error");
          setErrorMsg(data.error || null);
          cleanup();
        }
      } catch {
        // Ignore non-JSON messages (keep-alive, comments)
      }
    };

    es.addEventListener("message", handler);

    es.onerror = () => {
      if (es.readyState === EventSource.CLOSED) return;
      // Connection error - don't mark as failed, let SSE reconnect
    };

    return cleanup;
  }, [isOpen, projectId, buildId, onComplete, cleanup]);

  if (!isOpen) return null;

  const currentIcon = stepIcons[step] || "⏳";
  const isSuccess = status === "success";
  const isError = status === "error";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={isSuccess || isError ? onClose : undefined}
      />

      {/* Modal */}
      <div className="relative w-full max-w-lg rounded-2xl border border-white/10 bg-slate-900/80 backdrop-blur-xl shadow-2xl shadow-emerald-500/5 p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <span className="text-2xl">{currentIcon}</span>
            {isSuccess ? "Construcción Completada" : isError ? "Error en la Construcción" : "Construyendo Grafos"}
          </h2>
          {(isSuccess || isError) && (
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-white/10 transition-colors text-slate-400 hover:text-white"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        {/* Progress Bar */}
        <div className="mb-6">
          <div className="flex justify-between text-sm text-slate-400 mb-2">
            <span>{message}</span>
            <span>{isError ? "—" : `${Math.max(0, progress)}%`}</span>
          </div>
          <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ease-out ${
                isError
                  ? "bg-rose-500"
                  : isSuccess
                  ? "bg-emerald-500"
                  : "bg-emerald-500"
              }`}
              style={{ width: `${Math.max(0, progress)}%` }}
            />
          </div>
        </div>

        {/* Step Indicator */}
        <div className="space-y-3 mb-6">
          <StepItem step="extracting_references" label="Extrayendo referencias" currentStep={step} status={status} />
          <StepItem step="building_citation_graph" label="Construyendo grafo de citaciones" currentStep={step} status={status} />
          <StepItem step="building_thematic_graph" label="Construyendo grafo temático" currentStep={step} status={status} />
        </div>

        {/* Results Summary (on success) */}
        {isSuccess && results && (
          <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-4 mb-4">
            <h3 className="text-sm font-semibold text-emerald-400 mb-2">Resumen</h3>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-slate-500">Referencias:</span>
                <span className="ml-2 text-emerald-300 font-mono">
                  {results.reference_extraction?.total_references_extracted ?? 0}
                </span>
              </div>
              <div>
                <span className="text-slate-500">Nodos citación:</span>
                <span className="ml-2 text-emerald-300 font-mono">
                  {results.citation_graph?.nodes ?? 0}
                </span>
              </div>
              <div>
                <span className="text-slate-500">Aristas citación:</span>
                <span className="ml-2 text-emerald-300 font-mono">
                  {results.citation_graph?.edges ?? 0}
                </span>
              </div>
              <div>
                <span className="text-slate-500">Nodos temático:</span>
                <span className="ml-2 text-emerald-300 font-mono">
                  {results.thematic_graph?.nodes ?? 0}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Error Details */}
        {isError && errorMsg && (
          <div className="bg-rose-500/10 border border-rose-500/20 rounded-xl p-4 mb-4">
            <h3 className="text-sm font-semibold text-rose-400 mb-2">Detalle del Error</h3>
            <p className="text-sm text-rose-300 font-mono break-all">{errorMsg}</p>
          </div>
        )}

        {/* Loading Spinner */}
        {status === "running" && (
          <div className="flex items-center justify-center py-4">
            <div className="w-8 h-8 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin" />
          </div>
        )}

        {/* Close Button (success/error) */}
        {(isSuccess || isError) && (
          <button
            onClick={onClose}
            className={`w-full py-3 rounded-xl font-bold transition-all ${
              isSuccess
                ? "bg-emerald-500 hover:bg-emerald-400 text-slate-950"
                : "bg-rose-500 hover:bg-rose-400 text-white"
            }`}
          >
            {isSuccess ? "Explorar Grafos" : "Cerrar"}
          </button>
        )}
      </div>
    </div>
  );
}

function StepItem({
  step,
  label,
  currentStep,
  status,
}: {
  step: string;
  label: string;
  currentStep: string;
  status: "running" | "success" | "error";
}) {
  const stepOrder = ["extracting_references", "building_citation_graph", "building_thematic_graph"];
  const currentIndex = stepOrder.indexOf(currentStep.replace("_complete", ""));
  const thisIndex = stepOrder.indexOf(step);
  const isComplete = currentStep === `${step}_complete` || currentStep === "complete";
  const isActive = currentStep === step;
  const isPending = thisIndex > currentIndex && !isComplete;

  let icon = "⏳";
  let color = "text-slate-600";

  if (isComplete || (status === "success" && thisIndex <= currentIndex)) {
    icon = "✅";
    color = "text-emerald-400";
  } else if (isActive && status === "running") {
    icon = "🔄";
    color = "text-emerald-400";
  } else if (status === "error" && isActive) {
    icon = "❌";
    color = "text-rose-400";
  }

  return (
    <div className={`flex items-center gap-3 text-sm ${isPending ? "text-slate-600" : color}`}>
      <span className="text-lg">{icon}</span>
      <span className={isActive && status === "running" ? "font-semibold text-white" : ""}>{label}</span>
      {isActive && status === "running" && (
        <span className="ml-auto text-xs text-emerald-400 animate-pulse">en progreso...</span>
      )}
    </div>
  );
}
