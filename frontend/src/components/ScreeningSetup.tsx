/**
 * ScreeningSetup — Page 1 of Screening.
 * 
 * Flow:
 * - If session exists → Show summary card (Continue / Delete)
 * - If no session → Show creation form with name, goal, search selection, config
 * - Only articles with download_status=SUCCESS are included
 */

import { useState, useEffect } from "react";
import {
    getProject,
    getProjectSearches,
    listProjectScreeningSessions,
    createScreeningSession,
    deleteScreeningSession,
    type Project,
    type SearchQuery,
    type ScreeningSession,
} from "../lib/api";
import { useOllamaModels } from "../hooks/useOllamaModels";
import ProgressModal from "./ProgressModal";

const LANGUAGES = [
    { code: "es", label: "🇪🇸 Español" },
    { code: "en", label: "🇺🇸 English" },
    { code: "pt", label: "🇧🇷 Português" },
];

export default function ScreeningSetup() {
    const { models, recommendedModel, loading: modelsLoading, error: modelsError } = useOllamaModels();
    const params = new URLSearchParams(window.location.search);
    const projectId = params.get("id") || "";
    const hasSession = params.has("session");
    const setupSessionId = params.get("setup_session");
    const isNew = params.has("new");

    const [project, setProject] = useState<Project | null>(null);
    const [searches, setSearches] = useState<(SearchQuery & { originalIndex: number })[]>([]);
    const [sessionsCount, setSessionsCount] = useState(0);
    const [existingSession, setExistingSession] = useState<ScreeningSession | null>(null);
    const [selectedSearchIds, setSelectedSearchIds] = useState<Set<string>>(new Set());
    const [readingLanguage, setReadingLanguage] = useState("es");
    const [translationModel, setTranslationModel] = useState("");
    const [existingSessionModel, setExistingSessionModel] = useState<string>("");
    const [sessionName, setSessionName] = useState("");
    const [sessionGoal, setSessionGoal] = useState("");
    const [isCustomModel, setIsCustomModel] = useState(false);
    const [customModelName, setCustomModelName] = useState("");
    const [isCustomExistingModel, setIsCustomExistingModel] = useState(false);
    const [customExistingModelName, setCustomExistingModelName] = useState("");
    const [loading, setLoading] = useState(true);
    const [creating, setCreating] = useState(false);
    const [showProgressModal, setShowProgressModal] = useState(false);
    const [deleting, setDeleting] = useState(false);
    const [error, setError] = useState("");

    useEffect(() => {
        if (!projectId || hasSession) return;
        (async () => {
            try {
                const [proj, srch, sessions] = await Promise.all([
                    getProject(projectId),
                    getProjectSearches(projectId),
                    listProjectScreeningSessions(projectId),
                ]);
                setProject(proj);
                setSessionsCount(sessions.length);

                // Use the project's LLM model as the default translation model
                const projectModel = proj.llm_model || "qwen2.5:7b";
                setTranslationModel(projectModel);

                const availableSearches = srch.map((s, i) => ({ ...s, originalIndex: i + 1 })).filter(s => s.unassigned_articles > 0);
                setSearches(availableSearches);

                if (sessions.length > 0 && !isNew) {
                    const targetSession = setupSessionId
                        ? sessions.find(s => s.id === setupSessionId) || sessions[0]
                        : sessions[0];
                    setExistingSession(targetSession);
                    // Use session's model, fallback to project model
                    const savedModel = targetSession.translation_model || projectModel;
                    setExistingSessionModel(savedModel);

                    const isRecommended = models.some(m => m.name === savedModel);
                    if (!isRecommended && savedModel) {
                        setIsCustomExistingModel(true);
                        setCustomExistingModelName(savedModel);
                    }
                }

                setSelectedSearchIds(new Set(availableSearches.map((s) => s.id)));
            } catch (e: any) {
                setError(e.message);
            } finally {
                setLoading(false);
            }
        })();
    }, [projectId, hasSession, setupSessionId, isNew]);

    if (hasSession) return null;

    const handleModelChange = (val: string, isExisting: boolean) => {
        if (isExisting) {
            if (val === "custom") setIsCustomExistingModel(true);
            else {
                setIsCustomExistingModel(false);
                setExistingSessionModel(val);
            }
        } else {
            if (val === "custom") setIsCustomModel(true);
            else {
                setIsCustomModel(false);
                setTranslationModel(val);
            }
        }
    };

    const toggleSearch = (id: string) => {
        setSelectedSearchIds((prev) => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id);
            else next.add(id);
            return next;
        });
    };

    const selectAll = () => setSelectedSearchIds(new Set(searches.map((s) => s.id)));
    const deselectAll = () => setSelectedSearchIds(new Set());

    const handleDeleteSession = async () => {
        if (!existingSession) return;
        if (!confirm("¿Eliminar sesión?")) return;
        setDeleting(true);
        try {
            await deleteScreeningSession(existingSession.id);
            setExistingSession(null);
        } catch (e: any) {
            setError(e.message);
        } finally {
            setDeleting(false);
        }
    };

    const handleProgressDoneEnrich = async () => {
        setShowProgressModal(false);
        if (!creating) return;
        try {
            const sessions = await listProjectScreeningSessions(projectId);
            if (sessions.length > 0) {
                window.location.href = `/screening?id=${projectId}&session=${sessions[0].id}`;
            }
        } catch (e: any) {
            setError(e.message);
            setCreating(false);
        }
    };

    const handleStartScreening = async () => {
        if (selectedSearchIds.size === 0) return;
        setCreating(true);
        setShowProgressModal(true);
        setError("");
        try {
            await createScreeningSession({
                project_id: projectId,
                name: sessionName.trim() || `Revisión ${sessionsCount + 1}`,
                goal: sessionGoal.trim(),
                search_query_ids: Array.from(selectedSearchIds),
                reading_language: readingLanguage,
                translation_model: translationModel,
            });
        } catch (e: any) {
            setError(e.message);
            setCreating(false);
            setShowProgressModal(false);
        }
    };

    const handleContinueScreening = async () => {
        if (!existingSession) return;
        setCreating(true);
        try {
            if (existingSessionModel !== existingSession.translation_model) {
                const { updateScreeningSession } = await import('../lib/api');
                await updateScreeningSession(existingSession.id, {
                    translation_model: existingSessionModel,
                });
            }
            window.location.href = `/screening?id=${projectId}&session=${existingSession.id}`;
        } catch (e: any) {
            setError(e.message);
            setCreating(false);
        }
    };

    if (loading) return <div className="max-w-4xl mx-auto mt-8 px-4 text-slate-200">Cargando...</div>;

    if (!project || (searches.length === 0 && !existingSession)) {
        return (
            <div className="max-w-4xl mx-auto mt-8 px-4 text-slate-200 text-center py-20">
                <h2 className="text-2xl font-bold text-slate-300 mb-4">Sin Artículos Elegibles</h2>
                <p className="text-slate-400 mb-8">No hay artículos con PDF descargado disponibles para revisión.</p>
                <a href={`/project?id=${projectId}`} className="px-6 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold rounded-xl transition-colors">
                    ← Volver al Proyecto
                </a>
            </div>
        );
    }

    const totalArticles = searches
        .filter((s) => selectedSearchIds.has(s.id))
        .reduce((sum, s) => sum + s.total_results - s.duplicates_removed, 0);

    if (existingSession) {
        const progress = existingSession.total_articles > 0
            ? Math.round((existingSession.reviewed_count / existingSession.total_articles) * 100)
            : 0;
        return (
            <div className="max-w-4xl mx-auto mt-8 px-4 text-slate-200">
                <div className="mb-8">
                    <a href={`/project?id=${projectId}`} className="text-slate-400 hover:text-emerald-400 transition-colors flex items-center gap-2 w-fit mb-4">
                        ← Volver
                    </a>
                    <h1 className="text-3xl font-bold bg-gradient-to-r from-emerald-400 to-teal-400 bg-clip-text text-transparent">
                        🗂️ Screening: {project.name}
                    </h1>
                </div>
                <div className="bg-slate-900/60 border border-slate-700/50 p-8 rounded-2xl backdrop-blur-xl shadow-xl">
                    <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
                        <span className="text-2xl">📋</span> {existingSession.name}
                    </h2>
                    <div className="flex gap-8 mb-6">
                        <div className="flex flex-col">
                            <span className="text-3xl font-black text-slate-200">{existingSession.total_articles}</span>
                            <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">Total</span>
                        </div>
                        <div className="flex flex-col">
                            <span className="text-3xl font-black text-emerald-400">{existingSession.reviewed_count}</span>
                            <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">Revisados</span>
                        </div>
                    </div>
                    <div className="h-3 bg-slate-800 rounded-full overflow-hidden border border-slate-700/50 mb-8">
                        <div className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 transition-all duration-500" style={{ width: `${progress}%` }} />
                    </div>
                    <div className="flex gap-4">
                        <button onClick={handleContinueScreening} className="px-6 py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-bold rounded-xl shadow-lg shadow-blue-900/20 transition-all">
                            Continuar Revisión
                        </button>
                        <button onClick={handleDeleteSession} className="px-6 py-2.5 bg-rose-500/10 text-rose-400 hover:bg-rose-500 hover:text-white font-bold border border-rose-500/20 rounded-xl transition-all">
                            Eliminar Sesión
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-4xl mx-auto mt-8 px-4 text-slate-200">
            <div className="mb-8">
                <a href={`/project?id=${projectId}`} className="text-slate-400 hover:text-emerald-400 transition-colors flex items-center gap-2 w-fit mb-4">
                    ← Volver
                </a>
                <h1 className="text-3xl font-bold bg-gradient-to-r from-emerald-400 to-teal-400 bg-clip-text text-transparent">
                    Nueva Revisión
                </h1>
                <p className="text-slate-400 mt-2">Configura los parámetros para tu nueva sesión de cribado (screening).</p>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Columna Izquierda: Configuración Principal */}
                <div className="flex flex-col gap-6">
                    <div className="bg-slate-900/60 border border-slate-700/50 p-6 rounded-2xl backdrop-blur-xl">
                        <label className="block text-sm font-bold text-slate-300 mb-2">Nombre de la sesión</label>
                        <input 
                            type="text" 
                            value={sessionName} 
                            onChange={(e) => setSessionName(e.target.value)} 
                            className="w-full px-4 py-3 bg-slate-950/50 border border-slate-700 rounded-xl text-white focus:outline-none focus:border-emerald-500 transition-colors"
                            placeholder="Ej: Revisión Inicial" 
                        />
                    </div>
                    
                    <div className="bg-slate-900/60 border border-slate-700/50 p-6 rounded-2xl backdrop-blur-xl">
                        <label className="block text-sm font-bold text-slate-300 mb-2">Descripción u Objetivo (Opcional)</label>
                        <textarea 
                            value={sessionGoal} 
                            onChange={(e) => setSessionGoal(e.target.value)} 
                            className="w-full px-4 py-3 bg-slate-950/50 border border-slate-700 rounded-xl text-white focus:outline-none focus:border-emerald-500 transition-colors min-h-[100px] resize-y"
                            placeholder="Ej: Identificar algoritmos de IA aplicados en drones..."
                        />
                        <p className="text-[11px] text-slate-500 mt-2 font-medium">
                            Esta descripción ayudará al modelo de Active Learning y al LLM a sugerirte mejores artículos y entender tus criterios de inclusión.
                        </p>
                    </div>

                    <div className="bg-slate-900/60 border border-slate-700/50 p-6 rounded-2xl backdrop-blur-xl">
                        <label className="block text-sm font-bold text-slate-300 mb-2">Idioma de lectura (Abstracts/Keywords)</label>
                        <select 
                            value={readingLanguage} 
                            onChange={(e) => setReadingLanguage(e.target.value)}
                            className="w-full px-4 py-3 bg-slate-950/50 border border-slate-700 rounded-xl text-white focus:outline-none focus:border-emerald-500 transition-colors appearance-none"
                        >
                            {LANGUAGES.map(lang => (
                                <option key={lang.code} value={lang.code}>{lang.label}</option>
                            ))}
                        </select>
                        <p className="text-[11px] text-slate-500 mt-2 font-medium">
                            Si los artículos están en inglés, se traducirán automáticamente al idioma seleccionado para facilitar tu lectura.
                        </p>
                    </div>
                </div>

                {/* Columna Derecha: Búsquedas e Iniciar */}
                <div className="flex flex-col gap-6">
                    <div className="bg-slate-900/60 border border-slate-700/50 p-6 rounded-2xl backdrop-blur-xl">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-sm font-bold text-slate-300">Búsquedas a Incluir</h3>
                            <div className="flex gap-2">
                                <button onClick={selectAll} className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-xs font-bold text-slate-300 rounded-lg transition-colors">Todas</button>
                                <button onClick={deselectAll} className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-xs font-bold text-slate-300 rounded-lg transition-colors">Ninguna</button>
                            </div>
                        </div>
                        <div className="flex flex-col gap-2 max-h-[300px] overflow-y-auto pr-2 custom-scrollbar">
                            {searches.map(s => (
                                <label key={s.id} className={`flex items-center gap-3 p-3 rounded-xl border cursor-pointer transition-all ${selectedSearchIds.has(s.id) ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300' : 'bg-slate-950/50 border-slate-800 text-slate-400 hover:border-slate-700'}`}>
                                    <input 
                                        type="checkbox" 
                                        className="w-4 h-4 rounded border-slate-700 bg-slate-900 text-emerald-500 focus:ring-emerald-500 focus:ring-offset-slate-900" 
                                        checked={selectedSearchIds.has(s.id)} 
                                        onChange={() => toggleSearch(s.id)} 
                                    />
                                    <span className="font-medium text-sm">Búsqueda {s.originalIndex} <span className="text-xs opacity-70 ml-1">({s.unassigned_articles} art.)</span></span>
                                </label>
                            ))}
                            {searches.length === 0 && (
                                <div className="p-4 text-center text-sm text-slate-500">No hay búsquedas con artículos disponibles.</div>
                            )}
                        </div>
                    </div>
                    
                    <div className="bg-slate-900/60 border border-slate-700/50 p-6 rounded-2xl backdrop-blur-xl mt-auto">
                        <div className="flex items-center justify-between mb-4">
                            <span className="text-sm font-bold text-slate-400">Total a revisar:</span>
                            <span className="text-2xl font-black text-emerald-400">{totalArticles}</span>
                        </div>
                        <button 
                            onClick={handleStartScreening} 
                            disabled={creating || !sessionName || selectedSearchIds.size === 0} 
                            className="w-full py-3.5 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-white font-bold rounded-xl shadow-lg shadow-emerald-900/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex justify-center items-center gap-2"
                        >
                            {creating ? (
                                <>
                                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                    Creando Revisión...
                                </>
                            ) : (
                                <>
                                    🚀 Iniciar Revisión
                                </>
                            )}
                        </button>
                    </div>
                </div>
            </div>
            <ProgressModal isOpen={showProgressModal} projectId={projectId} onClose={handleProgressDoneEnrich} title="Preparando Revisión" />
        </div>
    );
}
