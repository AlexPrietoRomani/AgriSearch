/**
 * ScreeningSetup — Page 1 of Screening.
 * 
 * Allows the user to:
 * - Select which searches to include in the screening session
 * - Configure the reading language for abstract translation
 * - Choose the translation model
 * - Start the screening session
 * 
 * Once "Iniciar Screening" is pressed, navigates to the Session page.
 */

import { useState, useEffect } from "react";
import {
    getProject,
    getProjectSearches,
    createScreeningSession,
    listProjectScreeningSessions,
    type Project,
    type SearchQuery,
    type ScreeningSession,
} from "../lib/api";

const LANGUAGES = [
    { code: "es", label: "🇪🇸 Español" },
    { code: "en", label: "🇺🇸 English" },
    { code: "pt", label: "🇧🇷 Português" },
];

const MODELS = [
    { id: "llama3.1:8b", label: "Llama 3.1 8B (General)", desc: "Buen rendimiento general, traducción aceptable." },
    { id: "aya-23:8b", label: "Aya 23 8B (Multilingüe)", desc: "Optimizado para tareas multilingües, incluyendo EN↔ES/PT." },
    { id: "gemma3:4b", label: "Gemma 3 4B (Ligero)", desc: "Más rápido pero con menor calidad de traducción." },
];

export default function ScreeningSetup() {
    // Parse URL params
    const params = new URLSearchParams(window.location.search);
    const projectId = params.get("id") || "";
    const hasSession = params.has("session");

    const [project, setProject] = useState<Project | null>(null);
    const [searches, setSearches] = useState<SearchQuery[]>([]);
    const [existingSessions, setExistingSessions] = useState<ScreeningSession[]>([]);
    const [selectedSearchIds, setSelectedSearchIds] = useState<Set<string>>(new Set());
    const [readingLanguage, setReadingLanguage] = useState("es");
    const [translationModel, setTranslationModel] = useState("llama3.1:8b");
    const [loading, setLoading] = useState(true);
    const [creating, setCreating] = useState(false);
    const [error, setError] = useState("");

    // Load project data
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
                setSearches(srch);
                setExistingSessions(sessions);
                // Select all searches by default
                setSelectedSearchIds(new Set(srch.map((s) => s.id)));
            } catch (e: any) {
                setError(e.message);
            } finally {
                setLoading(false);
            }
        })();
    }, [projectId, hasSession]);

    // If a session is active, ScreeningSession component handles rendering
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

    const handleStartScreening = async () => {
        if (selectedSearchIds.size === 0) {
            setError("Selecciona al menos una búsqueda.");
            return;
        }
        setCreating(true);
        setError("");
        try {
            const session = await createScreeningSession({
                project_id: projectId,
                search_query_ids: Array.from(selectedSearchIds),
                reading_language: readingLanguage,
                translation_model: translationModel,
            });
            // Navigate to the session
            window.location.href = `/screening?id=${projectId}&session=${session.id}`;
        } catch (e: any) {
            setError(e.message);
            setCreating(false);
        }
    };

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

    if (!project || searches.length === 0) {
        return (
            <div className="screening-setup" style={styles.container}>
                <div style={styles.emptyState}>
                    <span style={{ fontSize: "3rem" }}>📭</span>
                    <h2 style={styles.emptyTitle}>No hay búsquedas disponibles</h2>
                    <p style={styles.emptyDesc}>
                        Para iniciar un screening, primero necesitas realizar al menos una búsqueda en el proyecto.
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

    return (
        <div className="screening-setup" style={styles.container}>
            {/* Header */}
            <div style={styles.header}>
                <a href={`/project?id=${projectId}`} style={styles.backLink}>
                    ← Volver al proyecto
                </a>
                <h1 style={styles.title}>🗂️ Configuración del Screening</h1>
                <p style={styles.subtitle}>
                    Proyecto: <strong>{project.name}</strong>
                </p>
            </div>

            {error && <div style={styles.errorBanner}>{error}</div>}

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
                                <div style={styles.searchInfo}>
                                    <div style={styles.searchQuery}>
                                        {search.raw_input.length > 80
                                            ? search.raw_input.slice(0, 80) + "..."
                                            : search.raw_input}
                                    </div>
                                    <div style={styles.searchMeta}>
                                        <span>📅 {new Date(search.created_at).toLocaleDateString("es")}</span>
                                        <span>📊 {search.total_results} artículos</span>
                                        <span>🗑️ {search.duplicates_removed} duplicados</span>
                                        <span style={styles.dbBadge}>{search.databases_used}</span>
                                    </div>
                                </div>
                            </label>
                        ))}
                    </div>

                    {/* Summary */}
                    <div style={styles.summary}>
                        <span style={styles.summaryIcon}>📊</span>
                        <div>
                            <strong>{selectedSearchIds.size}</strong> búsquedas seleccionadas
                            <br />
                            <strong>~{totalArticles}</strong> artículos únicos a cribar
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
                        disabled={creating || selectedSearchIds.size === 0}
                        style={{
                            ...styles.startButton,
                            ...(creating || selectedSearchIds.size === 0 ? styles.startButtonDisabled : {}),
                        }}
                    >
                        {creating ? (
                            <>
                                <div style={styles.miniSpinner} /> Creando sesión...
                            </>
                        ) : (
                            <>🚀 Iniciar Screening ({totalArticles} artículos)</>
                        )}
                    </button>
                </div>
            </div>

            {/* Existing Sessions */}
            {existingSessions.length > 0 && (
                <div style={{ ...styles.card, marginTop: "1.5rem" }}>
                    <h2 style={styles.cardTitle}>📋 Sesiones Anteriores</h2>
                    <div style={styles.sessionList}>
                        {existingSessions.map((s) => (
                            <a
                                key={s.id}
                                href={`/screening?id=${projectId}&session=${s.id}`}
                                style={styles.sessionItem}
                            >
                                <div>
                                    <strong>Sesión del {new Date(s.created_at).toLocaleDateString("es")}</strong>
                                    <div style={styles.sessionMeta}>
                                        {s.total_articles} artículos · {s.reviewed_count} revisados ·{" "}
                                        <span style={{ color: "#22c55e" }}>✅ {s.included_count}</span>{" "}
                                        <span style={{ color: "#ef4444" }}>❌ {s.excluded_count}</span>{" "}
                                        <span style={{ color: "#eab308" }}>🟡 {s.maybe_count}</span>
                                    </div>
                                </div>
                                <div style={styles.progressMini}>
                                    <div
                                        style={{
                                            ...styles.progressBar,
                                            width: `${(s.reviewed_count / Math.max(s.total_articles, 1)) * 100}%`,
                                        }}
                                    />
                                </div>
                            </a>
                        ))}
                    </div>
                </div>
            )}
        </div>
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
    header: {
        marginBottom: "2rem",
    },
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
    subtitle: {
        color: "#94a3b8",
        margin: 0,
        fontSize: "0.95rem",
    },
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
    selectActions: {
        display: "flex",
        gap: "0.5rem",
        alignItems: "center",
    },
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
    searchInfo: {
        flex: 1,
    },
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
    languageGrid: {
        display: "flex",
        gap: "0.5rem",
    },
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
    radio: {
        marginTop: "0.2rem",
        accentColor: "#60a5fa",
    },
    modelDesc: {
        fontSize: "0.78rem",
        color: "#94a3b8",
        marginTop: "0.15rem",
    },
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
    sessionList: {
        display: "flex",
        flexDirection: "column" as const,
        gap: "0.5rem",
        marginTop: "0.75rem",
    },
    sessionItem: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "0.75rem 1rem",
        background: "rgba(15, 23, 42, 0.5)",
        borderRadius: "8px",
        textDecoration: "none",
        color: "#e2e8f0",
        transition: "background 0.2s",
    },
    sessionMeta: {
        fontSize: "0.8rem",
        color: "#94a3b8",
        marginTop: "0.25rem",
    },
    progressMini: {
        width: "80px",
        height: "6px",
        background: "rgba(148, 163, 184, 0.2)",
        borderRadius: "3px",
        overflow: "hidden",
    },
    progressBar: {
        height: "100%",
        background: "linear-gradient(90deg, #60a5fa, #22c55e)",
        borderRadius: "3px",
        transition: "width 0.3s",
    },
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
    loadingText: {
        color: "#94a3b8",
        fontSize: "0.95rem",
    },
    miniSpinner: {
        width: "18px",
        height: "18px",
        border: "2px solid rgba(255,255,255,0.3)",
        borderTop: "2px solid #fff",
        borderRadius: "50%",
        animation: "spin 0.8s linear infinite",
    },
    emptyState: {
        textAlign: "center" as const,
        padding: "3rem 1rem",
    },
    emptyTitle: {
        fontSize: "1.3rem",
        color: "#f1f5f9",
        marginTop: "1rem",
    },
    emptyDesc: {
        color: "#94a3b8",
        maxWidth: "400px",
        margin: "0.5rem auto 1.5rem",
        lineHeight: 1.6,
    },
};
