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
import ProgressModal from "./ProgressModal";

const LANGUAGES = [
    { code: "es", label: "🇪🇸 Español" },
    { code: "en", label: "🇺🇸 English" },
    { code: "pt", label: "🇧🇷 Português" },
];

const GPU_MODELS = [
    { value: "deepseek-r1:7b", label: "DeepSeek R1 7B (Excelente)", desc: "Gran balance en razonamiento y precisión." },
    { value: "deepseek-r1:14b", label: "DeepSeek R1 14B (Recomendado GPU)", desc: "Alta capacidad analítica para screening complejo." },
    { value: "qwen2.5:7b", label: "Qwen 2.5 7B (Veloz)", desc: "Traducción muy buena y rápida." },
];

const CPU_MODELS = [
    { value: "deepseek-r1:1.5b", label: "DeepSeek R1 1.5B (Ligero)", desc: "Ideal para CPUs básicas, buen razonamiento." },
    { value: "phi4-mini:3.8b", label: "Phi-4 Mini 3.8B (Recomendado CPU)", desc: "Eficiente en general." },
    { value: "qwen3:0.6b", label: "Qwen 3 0.6B (Micro)", desc: "Extra ligero para tareas simples." },
];

export default function ScreeningSetup() {
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
    const [translationModel, setTranslationModel] = useState("deepseek-r1:7b");
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

                const availableSearches = srch.map((s, i) => ({ ...s, originalIndex: i + 1 })).filter(s => s.unassigned_articles > 0);
                setSearches(availableSearches);

                if (sessions.length > 0 && !isNew) {
                    const targetSession = setupSessionId
                        ? sessions.find(s => s.id === setupSessionId) || sessions[0]
                        : sessions[0];
                    setExistingSession(targetSession);
                    let savedModel = targetSession.translation_model || "deepseek-r1:7b";
                    if (savedModel === "aya-expanse" || savedModel === "aya:8b") savedModel = "deepseek-r1:7b";
                    setExistingSessionModel(savedModel);

                    const isRecommended = [...GPU_MODELS, ...CPU_MODELS].some(m => m.value === savedModel);
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

    if (loading) return <div style={styles.container}>Cargando...</div>;

    if (!project || (searches.length === 0 && !existingSession)) {
        return (
            <div style={styles.container}>
                <h2>Sin Artículos Elegibles</h2>
                <a href={`/project?id=${projectId}`} style={styles.backLink}>← Volver</a>
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
            <div style={styles.container}>
                <div style={styles.header}>
                    <a href={`/project?id=${projectId}`} style={styles.backLink}>← Volver</a>
                    <h1 style={styles.title}>🗂️ Screening: {project.name}</h1>
                </div>
                <div style={styles.existingCard}>
                    <h2>📋 {existingSession.name}</h2>
                    <div style={styles.statsGrid}>
                        <div style={styles.stat}><span style={styles.statNum}>{existingSession.total_articles}</span><span>Total</span></div>
                        <div style={styles.stat}><span style={styles.statNum}>{existingSession.reviewed_count}</span><span>Revisados</span></div>
                    </div>
                    <div style={styles.progressOuter}><div style={{ ...styles.progressInner, width: `${progress}%` }} /></div>
                    <div style={{ marginTop: '1rem', display: 'flex', gap: '1rem' }}>
                        <button onClick={handleContinueScreening} style={styles.continueButton}>Continuar</button>
                        <button onClick={handleDeleteSession} style={styles.deleteButton}>Eliminar</button>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div style={styles.container}>
            <div style={styles.header}>
                <a href={`/project?id=${projectId}`} style={styles.backLink}>← Volver</a>
                <h1 style={styles.title}>Nueva Revisión</h1>
            </div>
            <div style={styles.card}>
                <label style={styles.inputLabel}>Nombre de la sesión</label>
                <input type="text" value={sessionName} onChange={(e) => setSessionName(e.target.value)} style={styles.textInput} />
            </div>
            <div style={styles.grid}>
                <div style={styles.card}>
                    <h3>Búsquedas</h3>
                    {searches.map(s => (
                        <label key={s.id} style={styles.searchItem}>
                            <input type="checkbox" checked={selectedSearchIds.has(s.id)} onChange={() => toggleSearch(s.id)} />
                            <span>Búsqueda {s.originalIndex} ({s.unassigned_articles} art.)</span>
                        </label>
                    ))}
                </div>
                <div style={styles.card}>
                    <button onClick={handleStartScreening} disabled={creating || !sessionName} style={styles.startButton}>🚀 Iniciar</button>
                </div>
            </div>
            <ProgressModal isOpen={showProgressModal} projectId={projectId} onClose={handleProgressDoneEnrich} title="Preparando Revisión" />
        </div>
    );
}

const styles: Record<string, React.CSSProperties> = {
    container: { maxWidth: "1000px", margin: "2rem auto", padding: "0 1rem", color: "#e2e8f0" },
    header: { marginBottom: "2rem" },
    title: { fontSize: "1.5rem" },
    backLink: { color: "#94a3b8", textDecoration: "none" },
    card: { background: "#1e293b", padding: "1.5rem", borderRadius: "12px", marginBottom: "1rem" },
    existingCard: { background: "#1e293b", padding: "2rem", borderRadius: "16px" },
    grid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" },
    inputLabel: { display: "block", marginBottom: "0.5rem" },
    textInput: { width: "100%", padding: "0.5rem", background: "#0f172a", border: "1px solid #334155", color: "#fff" },
    searchItem: { display: "flex", gap: "0.5rem", padding: "0.5rem" },
    startButton: { width: "100%", padding: "1rem", background: "#22c55e", borderRadius: "8px", fontWeight: "bold", border: "none" },
    deleteButton: { background: "none", border: "none", color: "#ef4444", cursor: "pointer" },
    continueButton: { padding: "0.5rem 1rem", background: "#60a5fa", borderRadius: "4px", border: "none" },
    progressOuter: { background: "#0f172a", height: "8px", borderRadius: "4px" },
    progressInner: { background: "#60a5fa", height: "100%" },
    statNum: { fontSize: "1.2rem", fontWeight: "bold" },
    statsGrid: { display: "flex", gap: "2rem", margin: "1rem 0" }
};
