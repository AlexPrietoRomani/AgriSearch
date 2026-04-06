import { useState, useEffect } from "react";

interface ProgressEvent {
    type: "reparse_start" | "reparse_end" | "progress" | "sub_progress" | "error";
    msg?: string;
    article?: string;
    sub_msg?: string;
    current?: number;
    total?: number;
    stats?: any;
}

interface Props {
    isOpen: boolean;
    projectId: string;
    onClose: (stats?: any) => void;
    onStop?: () => void;
    title?: string;
}

const API_BASE = import.meta.env.PUBLIC_API_URL || "http://localhost:8000/api/v1";

export default function ProgressModal({ isOpen, projectId, onClose, onStop, title = "Procesando Artículos" }: Props) {
    const [status, setStatus] = useState<"connecting" | "processing" | "completed" | "error" | "stopped">("connecting");
    const [message, setMessage] = useState("Conectando...");
    const [subMessage, setSubMessage] = useState("");
    const [currentArticle, setCurrentArticle] = useState("");
    const [progress, setProgress] = useState(0);
    const [counts, setCounts] = useState({ current: 0, total: 0 });
    const [finalStats, setFinalStats] = useState<any>(null);

    useEffect(() => {
        if (!isOpen || !projectId) return;

        // Reset state
        setStatus("connecting");
        setMessage("Estableciendo canal de eventos...");
        setSubMessage("");
        setCurrentArticle("");
        setProgress(0);
        setCounts({ current: 0, total: 0 });
        setFinalStats(null);

        const eventSource = new EventSource(`${API_BASE}/events/${projectId}`);

        eventSource.onmessage = (event) => {
            try {
                const data: ProgressEvent = JSON.parse(event.data);
                console.log("SSE Event:", data);

                switch (data.type) {
                    case "reparse_start":
                        setStatus("processing");
                        setMessage(data.msg || "Iniciando...");
                        break;
                    case "progress":
                        setStatus("processing");
                        if (data.article) setCurrentArticle(data.article);
                        if (data.current && data.total) {
                            setCounts({ current: data.current, total: data.total });
                            setProgress(Math.round((data.current / data.total) * 100));
                            setMessage(`Procesando ${data.current} de ${data.total}`);
                        }
                        if (data.sub_msg) {
                            setSubMessage(data.sub_msg);
                        } else {
                            setSubMessage("");
                        }
                        break;
                    case "sub_progress":
                        if (data.msg) setSubMessage(data.msg);
                        break;
                    case "reparse_end":
                        setStatus("completed");
                        setMessage("¡Proceso finalizado con éxito!");
                        setFinalStats(data.stats);
                        eventSource.close();
                        break;
                    case "error":
                        setStatus("error");
                        setMessage(data.msg || "Ocurrió un error en el servidor.");
                        eventSource.close();
                        break;
                }
            } catch (e) {
                console.error("Error parsing SSE data", e);
            }
        };

        eventSource.onerror = (err) => {
            console.error("SSE Error:", err);
            // Don't immediately show error for keep-alive or temporary blips
            // but if it stays closed we might need to alert
        };

        return () => {
            eventSource.close();
        };
    }, [isOpen, projectId]);

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[300] flex items-center justify-center p-4 bg-slate-950/90 backdrop-blur-md">
            <div className="bg-slate-900 border border-slate-700/50 w-full max-w-xl rounded-3xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
                <div className="p-8">
                    <div className="flex items-center justify-between mb-6">
                        <h3 className="text-2xl font-black text-white">{title}</h3>
                        {status === "processing" && (
                            <div className="w-6 h-6 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
                        )}
                        {status === "completed" && (
                            <div className="w-6 h-6 text-emerald-400 bg-emerald-500/10 rounded-full flex items-center justify-center">
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                                </svg>
                            </div>
                        )}
                    </div>

                    <div className="space-y-6">
                        <div className="space-y-2">
                            <div className="flex justify-between text-sm mb-1">
                                <span className="text-slate-400 font-medium">{message}</span>
                                <span className="text-emerald-400 font-bold">{progress}%</span>
                            </div>
                            <div className="w-full h-3 bg-slate-800 rounded-full overflow-hidden border border-slate-700/50">
                                <div 
                                    className="h-full bg-gradient-to-r from-emerald-600 to-teal-400 transition-all duration-500 ease-out shadow-[0_0_15px_rgba(16,185,129,0.3)]"
                                    style={{ width: `${progress}%` }}
                                />
                            </div>
                        </div>

                        {currentArticle && (
                            <div className="bg-slate-950/50 rounded-2xl p-4 border border-slate-800 animate-in fade-in slide-in-from-bottom-2">
                                <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest block mb-1">Artículo Actual</span>
                                <p className="text-slate-300 text-sm font-medium line-clamp-2 italic mb-2">
                                    "{currentArticle}"
                                </p>
                                {subMessage && (
                                    <div className="flex items-center gap-2 text-xs text-indigo-300 bg-indigo-950/30 p-2 rounded-lg border border-indigo-900/50">
                                        <svg className="w-4 h-4 animate-spin text-indigo-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                        </svg>
                                        <span>{subMessage}</span>
                                    </div>
                                )}
                            </div>
                        )}

                        {status === "completed" && finalStats && (
                            <div className="grid grid-cols-3 gap-4 pt-4 border-t border-slate-800">
                                <div className="text-center">
                                    <div className="text-xl font-black text-emerald-400">{finalStats.processed}</div>
                                    <div className="text-[10px] text-slate-500 uppercase font-bold">Éxito</div>
                                </div>
                                <div className="text-center border-x border-slate-800">
                                    <div className="text-xl font-black text-rose-400">{finalStats.failed}</div>
                                    <div className="text-[10px] text-slate-500 uppercase font-bold">Fallidos</div>
                                </div>
                                <div className="text-center">
                                    <div className="text-xl font-black text-slate-300">{finalStats.total}</div>
                                    <div className="text-[10px] text-slate-500 uppercase font-bold">Total</div>
                                </div>
                            </div>
                        )}

                        <div className="pt-4 flex justify-between gap-4">
                            {status === "processing" && onStop && (
                                <button
                                    onClick={onStop}
                                    className="px-6 py-3 rounded-xl border border-rose-500/50 text-rose-400 font-bold hover:bg-rose-500/10 transition-colors"
                                >
                                    Detener Proceso
                                </button>
                            )}
                            <button
                                onClick={() => onClose(finalStats)}
                                disabled={status !== "completed" && status !== "error" && status !== "stopped"}
                                className={`px-8 py-3 rounded-xl font-bold transition-all ml-auto ${
                                    status === "completed" 
                                        ? "bg-emerald-500 hover:bg-emerald-400 text-slate-950"
                                        : status === "error" || status === "stopped"
                                        ? "bg-slate-700 text-white hover:bg-slate-600"
                                        : "bg-slate-800 text-slate-500 cursor-not-allowed"
                                }`}
                            >
                                {status === "completed" ? "Finalizar" : (status === "error" || status === "stopped") ? "Cerrar" : "Procesando..."}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
