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
    createScreeningSession,
    listProjectScreeningSessions,
    deleteScreeningSession,
    enrichArticles,
    type Project,
    type SearchQuery,
    type ScreeningSession,
    type EnrichmentStats,
} from "../lib/api";

const LANGUAGES = [
    { code: "es", label: "🇪🇸 Español" },
    { code: "en", label: "🇺🇸 English" },
    { code: "pt", label: "🇧🇷 Português" },
];

const MODELS = [
    { id: "aya:8b", label: "Aya 8B (Multilingüe Avanzado)", desc: "El mejor para traducciones exactas EN↔ES/PT." },
    { id: "llama3.1:8b", label: "Llama 3.1 8B (General)", desc: "Buen rendimiento general, traducción aceptable." },
    { id: "qwen2.5:7b", label: "Qwen 2.5 7B (Excelente Multilingüe)", desc: "Alternativa rápida y precisa en varios idiomas." },
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
    const [translationModel, setTranslationModel] = useState("aya:8b");
    const [existingSessionModel, setExistingSessionModel] = useState<string>("");
    const [sessionName, setSessionName] = useState("");
    const [sessionGoal, setSessionGoal] = useState("");
    const [loading, setLoading] = useState(true);
    const [creating, setCreating] = useState(false);
    const [enriching, setEnriching] = useState(false);
    const [enrichStep, setEnrichStep] = useState("");
    const [enrichStats, setEnrichStats] = useState<EnrichmentStats | null>(null);
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

                // Keep only searches with unassigned articles to review
                const availableSearches = srch.map((s, i) => ({ ...s, originalIndex: i + 1 })).filter(s => s.unassigned_articles > 0);
                setSearches(availableSearches);

                if (sessions.length > 0 && !isNew) {
                    const targetSession = setupSessionId
                        ? sessions.find(s => s.id === setupSessionId) || sessions[0]
                        : sessions[0];
                    setExistingSession(targetSession);
                    let savedModel = targetSession.translation_model || "aya:8b";
                    if (savedModel === "aya-expanse") savedModel = "aya:8b";
                    setExistingSessionModel(savedModel);
                }

                // Auto-select by default only the available searches
                setSelectedSearchIds(new Set(availableSearches.map((s) => s.id)));
            } catch (e: any) {
                setError(e.message);
            } finally {
                setLoading(false);
            }
        })();
    }, [projectId, hasSession]);

    if (hasSession) return null;

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
        if (!confirm("¿Estás seguro de eliminar esta sesión? Se perderán todas las decisiones de cribado. Esta acción es IRREVERSIBLE.")) return;
        setDeleting(true);
        setError("");
        try {
            await deleteScreeningSession(existingSession.id);
            setExistingSession(null);
        } catch (e: any) {
            setError(e.message);
        } finally {
            setDeleting(false);
        }
    };

    const handleStartScreening = async () => {
        if (selectedSearchIds.size === 0) {
            setError("Selecciona al menos una búsqueda.");
            return;
        }
        setCreating(true);
        setEnriching(true);
        setError("");
        try {
            setEnrichStep("📂 Escaneando PDFs descargados...");
            const stats = await enrichArticles(projectId);
            setEnrichStats(stats);

            setEnrichStep("✅ Enriquecimiento completado. Creando sesión...");
            await new Promise(r => setTimeout(r, 800));

            setEnriching(false);
            const finalName = sessionName.trim() || `Revisión ${sessionsCount + 1}`;
            const session = await createScreeningSession({
                project_id: projectId,
                name: finalName,
                goal: sessionGoal.trim(),
                search_query_ids: Array.from(selectedSearchIds),
                reading_language: readingLanguage,
                translation_model: translationModel,
            });
            window.location.href = `/screening?id=${projectId}&session=${session.id}`;
        } catch (e: any) {
            setError(e.message);
            setCreating(false);
            setEnriching(false);
        }
    };

    const handleContinueScreening = async () => {
        if (!existingSession) return;
        setCreating(true);
        setError("");
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

    // ── Loading ──
    if (loading) {
        return (
            <div className="screening-setup" style={styles.container}>
                <div style={styles.loadingContainer}>
                    <div style={styles.spinner} />
                    <p style={styles.loadingText}>Cargando datos del proyecto...</p>
                </div>
            </div>
        );
    }

    // ── Enrichment loading screen ──
    if (creating && enriching) {
        return (
            <div className="screening-setup" style={styles.container}>
                <div style={styles.enrichScreen}>
                    <div style={styles.enrichIcon}>📄</div>
                    <h2 style={styles.enrichTitle}>Preparando artículos para el screening</h2>
                    <p style={styles.enrichSubtitle}>
                        Analizando PDFs descargados para extraer información faltante...
                    </p>
                    <div style={styles.enrichProgress}>
                        <div style={styles.spinner} />
                        <p style={styles.enrichStep}>{enrichStep}</p>
                    </div>
                    {enrichStats && (
                        <div style={styles.enrichResults}>
                            <div style={styles.enrichStat}>
                                <span style={styles.enrichStatNumber}>{enrichStats.pdfs_matched}</span>
                                <span style={styles.enrichStatLabel}>PDFs analizados</span>
                            </div>
                            <div style={styles.enrichStat}>
                                <span style={{ ...styles.enrichStatNumber, color: '#22c55e' }}>{enrichStats.abstracts_extracted}</span>
                                <span style={styles.enrichStatLabel}>Abstracts extraídos</span>
                            </div>
                            <div style={styles.enrichStat}>
                                <span style={{ ...styles.enrichStatNumber, color: '#60a5fa' }}>{enrichStats.keywords_extracted}</span>
                                <span style={styles.enrichStatLabel}>Keywords extraídas</span>
                            </div>
                            <div style={styles.enrichStat}>
                                <span style={{ ...styles.enrichStatNumber, color: '#eab308' }}>{enrichStats.paths_updated}</span>
                                <span style={styles.enrichStatLabel}>Rutas actualizadas</span>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        );
    }

    // ── Post-enrichment creating ──
    if (creating && !enriching) {
        return (
            <div className="screening-setup" style={styles.container}>
                <div style={styles.loadingContainer}>
                    <div style={styles.spinner} />
                    <p style={styles.loadingText}>Creando sesión de screening (solo artículos con PDF)...</p>
                </div>
            </div>
        );
    }

    // ── No searches / No eligible articles ──
    if (!project || (searches.length === 0 && !existingSession)) {
        return (
            <div className="screening-setup" style={styles.container}>
                <div style={styles.emptyState}>
                    <span style={{ fontSize: "3rem" }}>📭</span>
                    <h2 style={styles.emptyTitle}>Sin Artículos Disponibles</h2>
                    <p style={styles.emptyDesc}>
                        Para iniciar un nuevo screening, realiza primero una búsqueda y descarga los PDFs. Si ya lo hiciste, es posible que todos los artículos ya estén asignados a otras revisiones activas.
                    </p>
                    <a href={`/project?id=${projectId}`} style={styles.backLink}>
                        ← Volver al proyecto
                    </a>
                </div>
            </div>
        );
    }

    const totalArticles = searches
        .filter((s) => selectedSearchIds.has(s.id))
        .reduce((sum, s) => sum + s.total_results - s.duplicates_removed, 0);

    // ═══════════════════════════════════════════════════════
    // ── EXISTING SESSION → Continue / Delete ──
    // ═══════════════════════════════════════════════════════
    if (existingSession) {
        const progress = existingSession.total_articles > 0
            ? Math.round((existingSession.reviewed_count / existingSession.total_articles) * 100)
            : 0;

        return (
            <div className="screening-setup" style={styles.container}>
                <div style={styles.header}>
                    <a href={`/project?id=${projectId}`} style={styles.backLink}>← Volver al proyecto</a>
                    <h1 style={styles.title}>🗂️ Screening del Proyecto</h1>
                    <p style={styles.subtitle}>Proyecto: <strong>{project.name}</strong></p>
                </div>

                {error && <div style={styles.errorBanner}>⚠️ {error}</div>}

                <div style={styles.existingCard}>
                    <div style={styles.existingHeader}>
                        <h2 style={{ ...styles.cardTitle, fontSize: "1.2rem" }}>
                            📋 {existingSession.name || "Sesión de Screening"}
                        </h2>
                        <span style={styles.existingDate}>
                            Creada el {new Date(existingSession.created_at).toLocaleDateString("es", { day: "numeric", month: "long", year: "numeric" })}
                        </span>
                    </div>

                    {existingSession.goal && (
                        <div style={styles.goalBox}>
                            <strong>🎯 Objetivo:</strong> {existingSession.goal}
                        </div>
                    )}

                    {/* Stats */}
                    <div style={styles.statsGrid}>
                        <div style={styles.stat}>
                            <span style={{ ...styles.statNum, color: "#f1f5f9" }}>{existingSession.total_articles}</span>
                            <span style={styles.statLabel}>Total</span>
                        </div>
                        <div style={styles.stat}>
                            <span style={{ ...styles.statNum, color: "#60a5fa" }}>{existingSession.reviewed_count}</span>
                            <span style={styles.statLabel}>Revisados</span>
                        </div>
                        <div style={styles.stat}>
                            <span style={{ ...styles.statNum, color: "#22c55e" }}>{existingSession.included_count}</span>
                            <span style={styles.statLabel}>✅ Incluidos</span>
                        </div>
                        <div style={styles.stat}>
                            <span style={{ ...styles.statNum, color: "#ef4444" }}>{existingSession.excluded_count}</span>
                            <span style={styles.statLabel}>❌ Excluidos</span>
                        </div>
                        <div style={styles.stat}>
                            <span style={{ ...styles.statNum, color: "#eab308" }}>{existingSession.maybe_count}</span>
                            <span style={styles.statLabel}>🟡 Tal vez</span>
                        </div>
                    </div>

                    {/* Progress bar */}
                    <div style={styles.progressOuter}>
                        <div style={{ ...styles.progressInner, width: `${progress}%` }} />
                    </div>
                    <div style={{ textAlign: "center" as const, fontSize: "0.85rem", color: "#94a3b8", marginTop: "0.5rem" }}>
                        {progress}% completado
                    </div>

                    {/* Actions */}
                    <div style={{ ...styles.existingActions, flexDirection: "column", gap: "1.5rem" }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', background: 'rgba(15,23,42,0.4)', padding: '1rem', borderRadius: '8px', border: '1px solid rgba(148,163,184,0.1)' }}>
                            <div style={{ flex: 1 }}>
                                <label style={{ display: 'block', marginBottom: '0.4rem', fontSize: '0.9rem', color: '#cbd5e1' }}>
                                    🤖 Modelo para continuar traducciones:
                                </label>
                                <select
                                    value={existingSessionModel}
                                    onChange={(e) => setExistingSessionModel(e.target.value)}
                                    style={styles.modelSelect}
                                >
                                    {MODELS.map(m => (
                                        <option key={m.id} value={m.id}>{m.label}</option>
                                    ))}
                                </select>
                            </div>
                            <button
                                onClick={handleContinueScreening}
                                disabled={creating}
                                style={{ ...styles.continueButton, flexShrink: 0 }}
                            >
                                {creating ? "Actualizando..." : "▶️ Continuar Screening"}
                            </button>
                        </div>

                        <div style={{ display: 'flex', justifyContent: 'flex-end', paddingTop: '1rem', borderTop: '1px outset rgba(148,163,184,0.1)' }}>
                            <button
                                onClick={handleDeleteSession}
                                disabled={deleting}
                                style={styles.deleteButton}
                            >
                                {deleting ? "Eliminando..." : "🗑️ Eliminar sesión y crear nueva"}
                            </button>
                        </div>
                    </div>

                    <p style={styles.futureNote}>
                        💡 <strong>Nota futura:</strong> En versiones posteriores se permitirá tener múltiples sesiones para que varias personas trabajen simultáneamente en el screening de un mismo proyecto, cada una con sus artículos asignados.
                    </p>
                </div>
            </div>
        );
    }

    // ═══════════════════════════════════════════════════════
    // ── NEW SESSION FORM ──
    // ═══════════════════════════════════════════════════════
    return (
        <div className="screening-setup" style={styles.container}>
            <div style={styles.header}>
                <a href={`/project?id=${projectId}`} style={styles.backLink}>← Volver al proyecto</a>
                <h1 style={styles.title}>🗂️ Nueva Sesión de Screening</h1>
                <p style={styles.subtitle}>Proyecto: <strong>{project.name}</strong></p>
            </div>

            {error && <div style={styles.errorBanner}>⚠️ {error}</div>}

            {/* Session Identity */}
            <div style={{ ...styles.card, marginBottom: "1.5rem" }}>
                <h2 style={styles.cardTitle}>📝 Identificación de la Sesión</h2>
                <p style={styles.configDesc}>
                    Dale un nombre descriptivo y define el objetivo de esta sesión de cribado.
                </p>
                <div style={{ display: "flex", flexDirection: "column" as const, gap: "0.75rem" }}>
                    <div>
                        <label style={styles.inputLabel}>Nombre de la sesión *</label>
                        <input
                            type="text"
                            value={sessionName}
                            onChange={(e) => setSessionName(e.target.value)}
                            placeholder="Ej: Cribado inicial PRISMA — Control biológico"
                            style={styles.textInput}
                        />
                    </div>
                    <div>
                        <label style={styles.inputLabel}>Objetivo / Meta de la sesión</label>
                        <textarea
                            value={sessionGoal}
                            onChange={(e) => setSessionGoal(e.target.value)}
                            placeholder="Ej: Identificar estudios relevantes sobre biocontrol de plagas con Telenomus podisi en soja para una revisión sistemática..."
                            rows={3}
                            style={styles.textArea}
                        />
                    </div>
                </div>
            </div>

            <div style={styles.grid}>
                {/* Left: Search Selection */}
                <div style={styles.card}>
                    <div style={styles.cardHeader}>
                        <h2 style={styles.cardTitle}>📜 Seleccionar Búsquedas</h2>
                        <div style={styles.selectActions}>
                            <button onClick={selectAll} style={styles.linkButton}>Seleccionar todas</button>
                            <span style={{ color: "#64748b" }}>|</span>
                            <button onClick={deselectAll} style={styles.linkButton}>Deseleccionar</button>
                        </div>
                    </div>
                    <div style={styles.searchList}>
                        {searches.map((search) => (
                            <label key={search.id} style={styles.searchItem}>
                                <input
                                    type="checkbox"
                                    checked={selectedSearchIds.has(search.id)}
                                    onChange={() => toggleSearch(search.id)}
                                    style={styles.checkbox}
                                />
                                <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", width: "100%" }}>
                                    <div style={{ fontWeight: 600, color: "#e2e8f0", fontSize: "1rem" }}>
                                        Búsqueda {search.originalIndex}
                                    </div>
                                    <div style={{ fontSize: "0.85rem", color: "#94a3b8", fontStyle: "italic", marginBottom: "0.2rem" }}>
                                        "{search.raw_input.length > 120 ? search.raw_input.slice(0, 120) + "..." : search.raw_input}"
                                    </div>
                                    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem", fontSize: "0.80rem", color: "#cbd5e1" }}>
                                        <span title="Fecha de búsqueda">📅 {new Date(search.created_at).toLocaleDateString("es")}</span>
                                        <span title="Total de artículos (incluyendo no descargados y duplicados)">📚 {search.total_results} totales</span>
                                        <span title="Artículos duplicados removidos" style={{ color: "#ef4444" }}>🗑️ {search.duplicates_removed} duplicados</span>
                                        <span title="Artículos descargados con éxito" style={{ color: "#22c55e" }}>📥 {search.total_downloaded} descargados</span>
                                        <span title="Artículos descargados pendientes de evaluar" style={{ color: "#a855f7", fontWeight: 600 }}>🔍 {search.unassigned_articles} por revisar</span>
                                    </div>
                                    <div style={{ marginTop: "0.2rem" }}>
                                        <span style={{ fontSize: "0.75rem", padding: "0.2rem 0.5rem", borderRadius: "4px", backgroundColor: "rgba(30,41,59,0.8)", border: "1px solid rgba(148,163,184,0.2)", display: "inline-block" }}>
                                            {search.databases_used.split(",").join(" • ")}
                                        </span>
                                    </div>
                                </div>
                            </label>
                        ))}
                    </div>

                    <div style={styles.summary}>
                        <span style={styles.summaryIcon}>📊</span>
                        <div>
                            <strong>{selectedSearchIds.size}</strong> búsquedas seleccionadas
                            <br />
                            <strong>{totalArticles}</strong> artículos descargados entrarán al nuevo screening
                        </div>
                    </div>
                </div>

                {/* Right: Configuration */}
                <div style={styles.configColumn}>
                    {/* Language Card */}
                    <div style={styles.card}>
                        <h2 style={styles.cardTitle}>🌐 Idioma de Lectura</h2>
                        <p style={styles.configDesc}>
                            Si el abstract está en un idioma diferente, se traducirá automáticamente de forma literal (sin resumir).
                        </p>
                        <div style={styles.languageGrid}>
                            {LANGUAGES.map((lang) => (
                                <button
                                    key={lang.code}
                                    onClick={() => setReadingLanguage(lang.code)}
                                    style={{
                                        ...styles.languageOption,
                                        ...(readingLanguage === lang.code ? styles.languageActive : {}),
                                    }}
                                >
                                    {lang.label}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Model Card */}
                    <div style={styles.card}>
                        <h2 style={styles.cardTitle}>🤖 Modelo de Traducción</h2>
                        <p style={styles.configDesc}>
                            Modelo Ollama para traducir abstracts. Selecciona según tu balance velocidad/calidad.
                        </p>
                        <div style={styles.modelList}>
                            {MODELS.map((model) => (
                                <label key={model.id} style={styles.modelItem}>
                                    <input
                                        type="radio"
                                        name="translation_model"
                                        value={model.id}
                                        checked={translationModel === model.id}
                                        onChange={() => setTranslationModel(model.id)}
                                        style={styles.radio}
                                    />
                                    <div>
                                        <strong>{model.label}</strong>
                                        <div style={styles.modelDesc}>{model.desc}</div>
                                    </div>
                                </label>
                            ))}
                        </div>
                    </div>

                    {/* Start Button */}
                    <button
                        onClick={handleStartScreening}
                        disabled={creating || selectedSearchIds.size === 0 || !sessionName.trim()}
                        style={{
                            ...styles.startButton,
                            ...(creating || selectedSearchIds.size === 0 || !sessionName.trim() ? styles.startButtonDisabled : {}),
                        }}
                    >
                        {creating ? (
                            <>
                                <div style={styles.miniSpinner} /> Creando sesión...
                            </>
                        ) : (
                            <>🚀 Crear Sesión de Screening</>
                        )}
                    </button>
                </div>
            </div>
        </div >
    );
}

// ── Styles ──
const styles: Record<string, React.CSSProperties> = {
    container: {
        maxWidth: "1100px",
        margin: "0 auto",
        padding: "2rem 1.5rem",
        fontFamily: "'Inter', -apple-system, sans-serif",
        color: "#e2e8f0",
    },
    header: { marginBottom: "2rem" },
    backLink: {
        color: "#94a3b8",
        textDecoration: "none",
        fontSize: "0.9rem",
        display: "inline-block",
        marginBottom: "0.5rem",
    },
    title: {
        fontSize: "1.75rem",
        fontWeight: 700,
        color: "#f1f5f9",
        margin: "0 0 0.25rem",
    },
    subtitle: { color: "#94a3b8", margin: 0, fontSize: "0.95rem" },
    errorBanner: {
        background: "rgba(239, 68, 68, 0.15)",
        border: "1px solid rgba(239, 68, 68, 0.3)",
        borderRadius: "8px",
        padding: "0.75rem 1rem",
        color: "#fca5a5",
        marginBottom: "1.5rem",
    },
    grid: {
        display: "grid",
        gridTemplateColumns: "1fr 380px",
        gap: "1.5rem",
        alignItems: "start",
    },
    card: {
        background: "rgba(30, 41, 59, 0.6)",
        border: "1px solid rgba(148, 163, 184, 0.1)",
        borderRadius: "12px",
        padding: "1.25rem",
        backdropFilter: "blur(10px)",
    },
    cardHeader: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: "1rem",
    },
    cardTitle: {
        fontSize: "1.1rem",
        fontWeight: 600,
        color: "#f1f5f9",
        margin: 0,
    },
    selectActions: { display: "flex", gap: "0.5rem", alignItems: "center" },
    linkButton: {
        background: "none",
        border: "none",
        color: "#60a5fa",
        cursor: "pointer",
        fontSize: "0.85rem",
        padding: 0,
    },
    searchList: {
        display: "flex",
        flexDirection: "column" as const,
        gap: "0.5rem",
        maxHeight: "350px",
        overflowY: "auto" as const,
    },
    searchItem: {
        display: "flex",
        alignItems: "flex-start",
        gap: "0.75rem",
        padding: "0.75rem",
        background: "rgba(15, 23, 42, 0.5)",
        borderRadius: "8px",
        cursor: "pointer",
        transition: "background 0.2s",
        border: "1px solid transparent",
    },
    checkbox: {
        marginTop: "0.25rem",
        accentColor: "#60a5fa",
        width: "18px",
        height: "18px",
        cursor: "pointer",
    },
    searchInfo: { flex: 1 },
    searchQuery: {
        fontSize: "0.9rem",
        color: "#e2e8f0",
        marginBottom: "0.35rem",
        lineHeight: 1.4,
    },
    searchMeta: {
        display: "flex",
        gap: "0.75rem",
        fontSize: "0.78rem",
        color: "#94a3b8",
        flexWrap: "wrap" as const,
    },
    dbBadge: {
        background: "rgba(96, 165, 250, 0.15)",
        color: "#60a5fa",
        padding: "0.1rem 0.4rem",
        borderRadius: "4px",
        fontSize: "0.72rem",
    },
    summary: {
        display: "flex",
        alignItems: "center",
        gap: "0.75rem",
        marginTop: "1rem",
        padding: "0.75rem",
        background: "rgba(96, 165, 250, 0.08)",
        borderRadius: "8px",
        border: "1px solid rgba(96, 165, 250, 0.2)",
        fontSize: "0.9rem",
        color: "#93c5fd",
    },
    summaryIcon: { fontSize: "1.5rem" },
    configColumn: {
        display: "flex",
        flexDirection: "column" as const,
        gap: "1rem",
    },
    configDesc: {
        fontSize: "0.85rem",
        color: "#94a3b8",
        marginBottom: "0.75rem",
        lineHeight: 1.5,
    },
    languageGrid: { display: "flex", gap: "0.5rem" },
    languageOption: {
        flex: 1,
        padding: "0.65rem 0.5rem",
        borderRadius: "8px",
        border: "1px solid rgba(148, 163, 184, 0.2)",
        background: "rgba(15, 23, 42, 0.5)",
        color: "#e2e8f0",
        cursor: "pointer",
        textAlign: "center" as const,
        fontSize: "0.9rem",
        transition: "all 0.2s",
    },
    languageActive: {
        border: "1px solid #60a5fa",
        background: "rgba(96, 165, 250, 0.15)",
        color: "#93c5fd",
        fontWeight: 600,
    },
    modelList: {
        display: "flex",
        flexDirection: "column" as const,
        gap: "0.5rem",
    },
    modelItem: {
        display: "flex",
        alignItems: "flex-start",
        gap: "0.75rem",
        padding: "0.6rem",
        background: "rgba(15, 23, 42, 0.5)",
        borderRadius: "8px",
        cursor: "pointer",
        fontSize: "0.88rem",
        color: "#e2e8f0",
    },
    radio: { marginTop: "0.2rem", accentColor: "#60a5fa" },
    modelDesc: { fontSize: "0.78rem", color: "#94a3b8", marginTop: "0.15rem" },
    startButton: {
        width: "100%",
        padding: "1rem",
        background: "linear-gradient(135deg, #22c55e, #16a34a)",
        color: "#fff",
        border: "none",
        borderRadius: "12px",
        fontSize: "1.05rem",
        fontWeight: 700,
        cursor: "pointer",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: "0.5rem",
        transition: "all 0.3s",
        boxShadow: "0 4px 12px rgba(34, 197, 94, 0.3)",
    },
    startButtonDisabled: {
        opacity: 0.5,
        cursor: "not-allowed",
        boxShadow: "none",
    },
    // ── Input styles ──
    inputLabel: {
        display: "block",
        fontSize: "0.85rem",
        color: "#94a3b8",
        marginBottom: "0.35rem",
        fontWeight: 500,
    },
    textInput: {
        width: "100%",
        padding: "0.7rem 0.9rem",
        background: "rgba(15, 23, 42, 0.7)",
        border: "1px solid rgba(148, 163, 184, 0.2)",
        borderRadius: "8px",
        color: "#e2e8f0",
        fontSize: "0.95rem",
        outline: "none",
        transition: "border 0.2s",
        boxSizing: "border-box" as const,
    },
    textArea: {
        width: "100%",
        padding: "0.7rem 0.9rem",
        background: "rgba(15, 23, 42, 0.7)",
        border: "1px solid rgba(148, 163, 184, 0.2)",
        borderRadius: "8px",
        color: "#e2e8f0",
        fontSize: "0.9rem",
        outline: "none",
        resize: "vertical" as const,
        lineHeight: 1.5,
        fontFamily: "'Inter', -apple-system, sans-serif",
        boxSizing: "border-box" as const,
    },
    // ── Existing session card ──
    existingCard: {
        background: "rgba(30, 41, 59, 0.6)",
        border: "1px solid rgba(96, 165, 250, 0.2)",
        borderRadius: "16px",
        padding: "2rem",
        backdropFilter: "blur(10px)",
    },
    existingHeader: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: "1rem",
        flexWrap: "wrap" as const,
        gap: "0.5rem",
    },
    existingDate: {
        fontSize: "0.85rem",
        color: "#94a3b8",
    },
    goalBox: {
        background: "rgba(96, 165, 250, 0.08)",
        border: "1px solid rgba(96, 165, 250, 0.15)",
        borderRadius: "8px",
        padding: "0.75rem 1rem",
        fontSize: "0.9rem",
        color: "#93c5fd",
        marginBottom: "1.5rem",
        lineHeight: 1.5,
    },
    statsGrid: {
        display: "grid",
        gridTemplateColumns: "repeat(5, 1fr)",
        gap: "1rem",
        marginBottom: "1.5rem",
    },
    stat: {
        display: "flex",
        flexDirection: "column" as const,
        alignItems: "center",
        gap: "0.25rem",
    },
    statNum: {
        fontSize: "1.8rem",
        fontWeight: 700,
    },
    statLabel: {
        fontSize: "0.78rem",
        color: "#94a3b8",
    },
    progressOuter: {
        width: "100%",
        height: "10px",
        background: "rgba(148, 163, 184, 0.15)",
        borderRadius: "5px",
        overflow: "hidden",
    },
    progressInner: {
        height: "100%",
        background: "linear-gradient(90deg, #60a5fa, #22c55e)",
        borderRadius: "5px",
        transition: "width 0.3s",
    },
    existingActions: {
        display: "flex",
        gap: "1rem",
        marginTop: "1.5rem",
    },
    continueButton: {
        flex: 2,
        padding: "0.85rem 1.5rem",
        background: "linear-gradient(135deg, #22c55e, #16a34a)",
        color: "#fff",
        border: "none",
        borderRadius: "12px",
        fontSize: "1rem",
        fontWeight: 700,
        textDecoration: "none",
        textAlign: "center" as const,
        cursor: "pointer",
        boxShadow: "0 4px 12px rgba(34, 197, 94, 0.3)",
        display: "block",
    },
    deleteButton: {
        flex: 1,
        padding: "0.85rem 1rem",
        background: "rgba(239, 68, 68, 0.1)",
        color: "#fca5a5",
        border: "1px solid rgba(239, 68, 68, 0.3)",
        borderRadius: "12px",
        fontSize: "0.9rem",
        fontWeight: 600,
        cursor: "pointer",
        transition: "all 0.2s",
    },
    modelSelect: {
        width: "100%",
        padding: "0.65rem",
        background: "rgba(15, 23, 42, 0.6)",
        border: "1px solid rgba(148, 163, 184, 0.2)",
        color: "#e2e8f0",
        borderRadius: "8px",
        outline: "none",
        fontSize: "0.95rem",
        fontFamily: "'Inter', -apple-system, sans-serif",
    },
    futureNote: {
        marginTop: "1.5rem",
        padding: "0.75rem 1rem",
        background: "rgba(234, 179, 8, 0.08)",
        border: "1px solid rgba(234, 179, 8, 0.2)",
        borderRadius: "8px",
        fontSize: "0.82rem",
        color: "#fde68a",
        lineHeight: 1.5,
    },
    // ── Loading / Enrichment ──
    loadingContainer: {
        display: "flex",
        flexDirection: "column" as const,
        alignItems: "center",
        justifyContent: "center",
        minHeight: "300px",
        gap: "1rem",
    },
    spinner: {
        width: "40px",
        height: "40px",
        border: "3px solid rgba(148, 163, 184, 0.2)",
        borderTop: "3px solid #60a5fa",
        borderRadius: "50%",
        animation: "spin 0.8s linear infinite",
    },
    loadingText: { color: "#94a3b8", fontSize: "0.95rem" },
    miniSpinner: {
        width: "18px",
        height: "18px",
        border: "2px solid rgba(255,255,255,0.3)",
        borderTop: "2px solid #fff",
        borderRadius: "50%",
        animation: "spin 0.8s linear infinite",
    },
    emptyState: { textAlign: "center" as const, padding: "3rem 1rem" },
    emptyTitle: { fontSize: "1.3rem", color: "#f1f5f9", marginTop: "1rem" },
    emptyDesc: {
        color: "#94a3b8",
        maxWidth: "400px",
        margin: "0.5rem auto 1.5rem",
        lineHeight: 1.6,
    },
    enrichScreen: {
        display: "flex",
        flexDirection: "column" as const,
        alignItems: "center",
        justifyContent: "center",
        minHeight: "400px",
        gap: "1rem",
        textAlign: "center" as const,
    },
    enrichIcon: { fontSize: "3.5rem", animation: "pulse 2s ease-in-out infinite" },
    enrichTitle: { fontSize: "1.5rem", fontWeight: 700, color: "#f1f5f9", margin: 0 },
    enrichSubtitle: { color: "#94a3b8", fontSize: "0.95rem", maxWidth: "500px", lineHeight: 1.6 },
    enrichProgress: {
        display: "flex",
        flexDirection: "column" as const,
        alignItems: "center",
        gap: "1rem",
        marginTop: "1rem",
    },
    enrichStep: { color: "#93c5fd", fontSize: "0.95rem", fontWeight: 500 },
    enrichResults: {
        display: "grid",
        gridTemplateColumns: "1fr 1fr 1fr 1fr",
        gap: "1rem",
        marginTop: "1.5rem",
        padding: "1rem 1.5rem",
        background: "rgba(30, 41, 59, 0.6)",
        border: "1px solid rgba(148, 163, 184, 0.1)",
        borderRadius: "12px",
    },
    enrichStat: {
        display: "flex",
        flexDirection: "column" as const,
        alignItems: "center",
        gap: "0.25rem",
    },
    enrichStatNumber: { fontSize: "1.8rem", fontWeight: 700, color: "#f1f5f9" },
    enrichStatLabel: { fontSize: "0.78rem", color: "#94a3b8" },
};
