/**
 * ScreeningSession — Page 2 of Screening.
 *
 * Article-by-article screening interface inspired by Rayyan.ai.
 * Supports keyboard shortcuts, abstract translation, and live stats.
 */

import { useState, useEffect, useCallback, useRef } from "react";
import 'katex/dist/katex.min.css';
import Latex from 'react-latex-next';
import {
    getScreeningSession,
    listScreeningArticles,
    updateDecision,
    getScreeningStats,
    translateAbstract,
    getArticleSuggestion,
    type ScreeningSession as ScreeningSessionType,
    type ScreeningArticle,
    type ScreeningStats,
    type ScreeningSuggestion,
} from "../lib/api";

const EXCLUSION_REASONS = [
    "Fuera de alcance",
    "No es artículo original",
    "Idioma no aceptado",
    "Duplicado no detectado",
    "Sin acceso al texto completo",
    "Otro",
];

/**
 * Truncate an author string to show at most `maxAuthors` names + "et al."
 */
function formatAuthors(authors: string | null, maxAuthors = 3): string {
    if (!authors) return "Autor desconocido";
    const list = authors.split(",").map(a => a.trim()).filter(Boolean);
    if (list.length <= maxAuthors) return list.join(", ");
    return list.slice(0, maxAuthors).join(", ") + " et al.";
}

interface Props {
    sessionId?: string;
    projectId?: string;
}

export default function ScreeningSession({ sessionId: propSessionId, projectId: propProjectId }: Props) {
    // Parse from URL if not passed as props
    const params = new URLSearchParams(window.location.search);
    const sessionId = propSessionId || params.get("session") || "";
    const projectId = propProjectId || params.get("id") || "";

    const [session, setSession] = useState<ScreeningSessionType | null>(null);
    const [articles, setArticles] = useState<ScreeningArticle[]>([]);
    const [stats, setStats] = useState<ScreeningStats | null>(null);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [loading, setLoading] = useState(true);
    const [showNote, setShowNote] = useState(false);
    const [noteText, setNoteText] = useState("");
    const [showExcludeModal, setShowExcludeModal] = useState(false);
    const [excludeReason, setExcludeReason] = useState(EXCLUSION_REASONS[0]);
    const [aiAssistEnabled, setAiAssistEnabled] = useState(true);
    const [translating, setTranslating] = useState(false);
    const [deciding, setDeciding] = useState(false);
    const [showPdf, setShowPdf] = useState(false);
    const [viewMode, setViewMode] = useState<"card" | "table">("card");
    const [filterDecision, setFilterDecision] = useState<string | undefined>(undefined);
    const [suggestion, setSuggestion] = useState<ScreeningSuggestion | null>(null);
    const [loadingSuggestion, setLoadingSuggestion] = useState(false);
    const [error, setError] = useState("");

    const containerRef = useRef<HTMLDivElement>(null);

    // Load session data
    useEffect(() => {
        if (!sessionId) return;
        (async () => {
            try {
                const [sess, arts, st] = await Promise.all([
                    getScreeningSession(sessionId),
                    listScreeningArticles(sessionId, 0, 500),
                    getScreeningStats(sessionId),
                ]);
                setSession(sess);
                setArticles(arts);
                setStats(st);
                // Find first pending article
                const firstPending = arts.findIndex((a) => a.decision === "pending");
                setCurrentIndex(firstPending >= 0 ? firstPending : 0);
            } catch (e: any) {
                setError(e.message);
            } finally {
                setLoading(false);
            }
        })();
    }, [sessionId]);

    const currentArticle = articles[currentIndex] || null;

    // Fetch AI Suggestion
    useEffect(() => {
        if (!sessionId || !currentArticle || viewMode !== "card" || currentArticle.decision !== "pending" || !aiAssistEnabled) {
            setSuggestion(null);
            return;
        }

        // Only suggest if at least 10 have been reviewed
        if (!stats || stats.reviewed < 10) {
            setSuggestion(null);
            return;
        }

        const timer = setTimeout(async () => {
            setLoadingSuggestion(true);
            try {
                const sugg = await getArticleSuggestion(sessionId, currentArticle.id);
                setSuggestion(sugg);
            } catch (e) {
                console.error("Failed to get suggestion", e);
                setSuggestion(null);
            } finally {
                setLoadingSuggestion(false);
            }
        }, 600); // 600ms delay to avoid flickering while navigating

        return () => clearTimeout(timer);
    }, [sessionId, currentArticle?.id, stats?.reviewed, viewMode, aiAssistEnabled]);

    // Keyboard shortcuts
    const handleKeyDown = useCallback(
        (e: KeyboardEvent) => {
            if (showExcludeModal || showNote) return; // Don't capture when modals are open
            const target = e.target as HTMLElement;
            if (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.tagName === "SELECT") return;

            switch (e.key.toLowerCase()) {
                case "i":
                    e.preventDefault();
                    handleDecision("include");
                    break;
                case "e":
                    e.preventDefault();
                    setShowExcludeModal(true);
                    break;
                case "m":
                    e.preventDefault();
                    handleDecision("maybe");
                    break;
                case "arrowleft":
                    e.preventDefault();
                    goToArticle(currentIndex - 1);
                    break;
                case "arrowright":
                    e.preventDefault();
                    goToArticle(currentIndex + 1);
                    break;
                case "n":
                    e.preventDefault();
                    setShowNote((v) => !v);
                    break;
                case "p":
                    e.preventDefault();
                    setShowPdf((v) => !v);
                    break;
                case "escape":
                    setShowExcludeModal(false);
                    setShowNote(false);
                    break;
            }
        },
        [currentIndex, articles, showExcludeModal, showNote],
    );

    useEffect(() => {
        window.addEventListener("keydown", handleKeyDown);
        return () => window.removeEventListener("keydown", handleKeyDown);
    }, [handleKeyDown]);

    const goToArticle = (index: number) => {
        if (index >= 0 && index < articles.length) {
            setCurrentIndex(index);
            setShowNote(false);
            setShowExcludeModal(false);
            setShowPdf(false);
            setNoteText(articles[index]?.reviewer_note || "");
        }
    };

    const handleDecision = async (decision: "include" | "exclude" | "maybe") => {
        if (!currentArticle || deciding) return;
        setDeciding(true);
        try {
            const updated = await updateDecision(currentArticle.decision_id, {
                decision,
                exclusion_reason: decision === "exclude" ? excludeReason : undefined,
                reviewer_note: noteText || undefined,
            });
            // Update local state
            const newArticles = [...articles];
            newArticles[currentIndex] = updated;
            setArticles(newArticles);
            // Refresh stats
            const newStats = await getScreeningStats(sessionId);
            setStats(newStats);
            // Auto-advance to next pending
            setShowExcludeModal(false);
            const nextPending = newArticles.findIndex((a, i) => i > currentIndex && a.decision === "pending");
            if (nextPending >= 0) {
                goToArticle(nextPending);
            } else if (currentIndex < newArticles.length - 1) {
                goToArticle(currentIndex + 1);
            }
        } catch (e: any) {
            setError(e.message);
        } finally {
            setDeciding(false);
        }
    };

    const handleExclude = () => {
        handleDecision("exclude");
    };

    const handleTranslate = async () => {
        if (!currentArticle || !session || translating) return;
        setTranslating(true);
        try {
            const result = await translateAbstract({
                decision_id: currentArticle.decision_id,
                target_language: session.reading_language,
            });
            if (result.translated_abstract) {
                const newArticles = [...articles];
                newArticles[currentIndex] = {
                    ...newArticles[currentIndex],
                    translated_abstract: result.translated_abstract,
                };
                setArticles(newArticles);
            }
        } catch (e: any) {
            setError(`Error al traducir: ${e.message}`);
        } finally {
            setTranslating(false);
        }
    };

    // If no session ID, don't render (Setup page is showing instead)
    if (!sessionId) return null;

    if (loading) {
        return (
            <div style={styles.loadingContainer}>
                <div style={styles.spinner} />
                <p style={styles.loadingText}>Cargando sesión de screening...</p>
            </div>
        );
    }

    if (!session || articles.length === 0) {
        return (
            <div style={styles.emptyState}>
                <span style={{ fontSize: "3rem" }}>😕</span>
                <h2>No se pudo cargar la sesión</h2>
                <p>{error || "Sin artículos en esta sesión."}</p>
                <a href={`/screening?id=${projectId}`} style={styles.backLink}>← Volver a configuración</a>
            </div>
        );
    }

    // For table view
    if (viewMode === "table") {
        return (
            <div style={{ ...styles.container, maxWidth: "95%" }} ref={containerRef}>
                <Header
                    session={session}
                    stats={stats}
                    projectId={projectId}
                    viewMode={viewMode}
                    setViewMode={setViewMode}
                    filterDecision={filterDecision}
                    setFilterDecision={setFilterDecision}
                    aiAssistEnabled={aiAssistEnabled}
                    setAiAssistEnabled={setAiAssistEnabled}
                />
                {error && <div style={styles.errorBanner}>{error}</div>}
                <table style={styles.table}>
                    <thead>
                        <tr>
                            <th style={styles.th}>#</th>
                            <th style={styles.th}>Título</th>
                            <th style={styles.th}>Autores</th>
                            <th style={styles.th}>Búsqueda</th>
                            <th style={styles.th}>Año</th>
                            <th style={styles.th}>Fuente</th>
                            <th style={styles.th}>Estado</th>
                            <th style={styles.th}>Acción</th>
                        </tr>
                    </thead>
                    <tbody>
                        {articles
                            .filter((a) => !filterDecision || a.decision === filterDecision)
                            .map((article, idx) => (
                                <tr key={article.id} style={idx % 2 === 0 ? styles.trEven : styles.trOdd}>
                                    <td style={styles.td}>{article.display_order + 1}</td>
                                    <td style={{ ...styles.td, maxWidth: "400px" }}>
                                        {article.title.length > 100 ? <Latex>{article.title.slice(0, 100) + "..."}</Latex> : <Latex>{article.title}</Latex>}
                                    </td>
                                    <td style={styles.td}>{formatAuthors(article.authors, 2)}</td>
                                    <td style={{ ...styles.td, color: "#60a5fa" }}>{article.search_query_name || "—"}</td>
                                    <td style={styles.td}>{article.year || "—"}</td>
                                    <td style={styles.td}>
                                        <span style={styles.sourceBadge}>{article.source_database}</span>
                                    </td>
                                    <td style={styles.td}>
                                        <DecisionBadge decision={article.decision} />
                                    </td>
                                    <td style={styles.td}>
                                        <button
                                            onClick={() => { setViewMode("card"); setCurrentIndex(articles.indexOf(article)); }}
                                            style={styles.reviewButton}
                                        >
                                            Revisar
                                        </button>
                                    </td>
                                </tr>
                            ))}
                    </tbody>
                </table>
            </div>
        );
    }

    // Card view (main screening interface)
    return (
        <div style={styles.container} ref={containerRef}>
            <Header
                session={session}
                stats={stats}
                projectId={projectId}
                viewMode={viewMode}
                setViewMode={setViewMode}
                filterDecision={filterDecision}
                setFilterDecision={setFilterDecision}
                aiAssistEnabled={aiAssistEnabled}
                setAiAssistEnabled={setAiAssistEnabled}
            />

            {error && <div style={styles.errorBanner}>{error}</div>}

            <div style={styles.mainGrid}>
                {/* Main Article Card */}
                <div style={styles.articleCard}>
                    {/* Navigation bar */}
                    <div style={styles.navBar}>
                        <button
                            onClick={() => goToArticle(currentIndex - 1)}
                            disabled={currentIndex === 0}
                            style={{ ...styles.navButton, ...(currentIndex === 0 ? styles.navDisabled : {}) }}
                        >
                            ← Anterior
                        </button>
                        <span style={styles.navCounter}>
                            {currentIndex + 1} / {articles.length}
                        </span>
                        <button
                            onClick={() => goToArticle(currentIndex + 1)}
                            disabled={currentIndex === articles.length - 1}
                            style={{
                                ...styles.navButton,
                                ...(currentIndex === articles.length - 1 ? styles.navDisabled : {}),
                            }}
                        >
                            Siguiente →
                        </button>
                    </div>

                    {/* Article content */}
                    {currentArticle && (
                        <>
                            <h2 style={styles.articleTitle}>
                                <Latex>{currentArticle.title}</Latex>
                            </h2>
                            <div style={styles.articleMeta}>
                                {currentArticle.authors && (
                                    <span>👥 {formatAuthors(currentArticle.authors)}</span>
                                )}
                                {currentArticle.year && <span>📅 {currentArticle.year}</span>}
                                {currentArticle.journal && <span>📰 {currentArticle.journal}</span>}
                                {currentArticle.doi && (
                                    <a
                                        href={`https://doi.org/${currentArticle.doi}`}
                                        target="_blank"
                                        rel="noreferrer"
                                        style={styles.doiLink}
                                    >
                                        🔗 DOI
                                    </a>
                                )}
                                <span style={styles.sourceBadge}>{currentArticle.source_database}</span>
                            </div>

                            {/* Keywords */}
                            {currentArticle.keywords && (
                                <div style={styles.keywords}>
                                    {currentArticle.keywords.split(",").map((kw, i) => (
                                        <span key={i} style={styles.keywordBadge}>{kw.trim()}</span>
                                    ))}
                                </div>
                            )}

                            {/* AI Suggestion */}
                            {loadingSuggestion && (
                                <div style={styles.suggestionLoading}>
                                    <div style={styles.miniSpinner} /> Generando sugerencia inteligente...
                                </div>
                            )}
                            {suggestion && currentArticle.decision === "pending" && (
                                <div style={{
                                    ...styles.suggestionBox,
                                    borderLeft: `5px solid ${suggestion.suggested_status === 'include' ? '#22c55e' : '#ef4444'}`
                                }}>
                                    <div style={styles.suggestionHeader}>
                                        <span style={{
                                            color: suggestion.suggested_status === 'include' ? '#4ade80' : '#f87171',
                                            fontWeight: 700
                                        }}>
                                            🤖 Sugerencia AI: {suggestion.suggested_status === 'include' ? 'INCLUIR' : 'EXCLUIR'}
                                        </span>
                                        {suggestion.confidence && (
                                            <span style={styles.confidenceBadge}>
                                                Confianza: {Math.round(suggestion.confidence * 100)}%
                                            </span>
                                        )}
                                    </div>
                                    <p style={styles.suggestionReason}>"{suggestion.justification}"</p>
                                </div>
                            )}

                            {/* Abstract */}
                            <div style={styles.abstractSection}>
                                <h3 style={styles.sectionTitle}>
                                    📝 Abstract original
                                    {!currentArticle.translated_abstract && session.reading_language !== "en" && (
                                        <button onClick={handleTranslate} disabled={translating} style={styles.translateButton}>
                                            {translating ? "⏳ Traduciendo..." : `🌐 Traducir a ${session.reading_language.toUpperCase()}`}
                                        </button>
                                    )}
                                </h3>
                                <div style={styles.abstractText}>
                                    {currentArticle.abstract ? <Latex>{currentArticle.abstract}</Latex> : "Sin abstract disponible."}
                                </div>
                            </div>

                            {/* Translated Abstract */}
                            {currentArticle.translated_abstract && (
                                <div style={styles.translatedSection}>
                                    <h3 style={styles.sectionTitle}>
                                        🌐 Abstract traducido ({session.reading_language.toUpperCase()})
                                    </h3>
                                    <div style={styles.abstractText}>
                                        <Latex>{currentArticle.translated_abstract}</Latex>
                                    </div>
                                </div>
                            )}

                            {/* Current decision badge */}
                            {currentArticle.decision !== "pending" && (
                                <div style={styles.currentDecisionBar}>
                                    <DecisionBadge decision={currentArticle.decision} />
                                    {currentArticle.exclusion_reason && (
                                        <span style={{ color: "#fca5a5", fontSize: "0.85rem" }}>
                                            Motivo: {currentArticle.exclusion_reason}
                                        </span>
                                    )}
                                </div>
                            )}

                            {/* Decision Buttons */}
                            <div style={styles.decisionBar}>
                                <button
                                    onClick={() => handleDecision("include")}
                                    disabled={deciding}
                                    style={styles.includeButton}
                                    title="Incluir (I)"
                                >
                                    ✅ Incluir
                                    <span style={styles.shortcut}>I</span>
                                </button>
                                <button
                                    onClick={() => setShowExcludeModal(true)}
                                    disabled={deciding}
                                    style={styles.excludeButton}
                                    title="Excluir (E)"
                                >
                                    ❌ Excluir
                                    <span style={styles.shortcut}>E</span>
                                </button>
                                <button
                                    onClick={() => handleDecision("maybe")}
                                    disabled={deciding}
                                    style={styles.maybeButton}
                                    title="Tal Vez (M)"
                                >
                                    🟡 Tal Vez
                                    <span style={styles.shortcut}>M</span>
                                </button>
                                <button onClick={() => setShowNote((v) => !v)} style={styles.noteToggle} title="Nota (N)">
                                    📝 Nota <span style={styles.shortcut}>N</span>
                                </button>
                                <button onClick={() => setShowPdf((v) => !v)} style={styles.pdfToggle} title="Ver PDF (P)">
                                    📄 PDF <span style={styles.shortcut}>P</span>
                                </button>
                            </div>

                            {/* Note input */}
                            {showNote && (
                                <div style={styles.noteSection}>
                                    <textarea
                                        value={noteText}
                                        onChange={(e) => setNoteText(e.target.value)}
                                        placeholder="Escribe una nota sobre este artículo..."
                                        style={styles.noteInput}
                                        rows={3}
                                        autoFocus
                                    />
                                </div>
                            )}

                            {/* PDF Viewer */}
                            {showPdf && currentArticle && (
                                <div style={styles.pdfSection}>
                                    <iframe
                                        src={`http://localhost:8000/api/v1/screening/sessions/${sessionId}/articles/${currentArticle.id}/pdf`}
                                        style={styles.pdfIframe}
                                        title={`PDF ${currentArticle.title}`}
                                    />
                                </div>
                            )}
                        </>
                    )}
                </div>

                {/* Stats Sidebar */}
                {stats && (
                    <div style={styles.sidebar}>
                        <h3 style={styles.sidebarTitle}>📊 Progreso</h3>
                        <div style={styles.progressContainer}>
                            <div style={styles.progressBackground}>
                                <div
                                    style={{
                                        ...styles.progressFill,
                                        width: `${stats.progress_percent}%`,
                                    }}
                                />
                            </div>
                            <span style={styles.progressLabel}>
                                {stats.reviewed} / {stats.total} ({stats.progress_percent}%)
                            </span>
                        </div>

                        <div style={styles.statGrid}>
                            <div style={{ ...styles.statCard, borderLeft: "3px solid #94a3b8" }}>
                                <div style={styles.statNumber}>{stats.pending}</div>
                                <div style={styles.statLabel}>Pendientes</div>
                            </div>
                            <div style={{ ...styles.statCard, borderLeft: "3px solid #22c55e" }}>
                                <div style={{ ...styles.statNumber, color: "#22c55e" }}>{stats.included}</div>
                                <div style={styles.statLabel}>✅ Incluidos</div>
                            </div>
                            <div style={{ ...styles.statCard, borderLeft: "3px solid #ef4444" }}>
                                <div style={{ ...styles.statNumber, color: "#ef4444" }}>{stats.excluded}</div>
                                <div style={styles.statLabel}>❌ Excluidos</div>
                            </div>
                            <div style={{ ...styles.statCard, borderLeft: "3px solid #eab308" }}>
                                <div style={{ ...styles.statNumber, color: "#eab308" }}>{stats.maybe}</div>
                                <div style={styles.statLabel}>🟡 Tal Vez</div>
                            </div>
                        </div>

                        {/* Keyboard shortcuts reference */}
                        <div style={styles.shortcutsCard}>
                            <h4 style={styles.shortcutsTitle}>⌨️ Atajos de teclado</h4>
                            <div style={styles.shortcutsList}>
                                <div><kbd style={styles.kbd}>I</kbd> Incluir</div>
                                <div><kbd style={styles.kbd}>E</kbd> Excluir</div>
                                <div><kbd style={styles.kbd}>M</kbd> Tal Vez</div>
                                <div><kbd style={styles.kbd}>←</kbd><kbd style={styles.kbd}>→</kbd> Navegar</div>
                                <div><kbd style={styles.kbd}>N</kbd> Nota</div>
                                <div><kbd style={styles.kbd}>P</kbd> Ver PDF</div>
                                <div><kbd style={styles.kbd}>Esc</kbd> Cerrar modal</div>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* Exclude Modal */}
            {showExcludeModal && (
                <div style={styles.modalOverlay} onClick={() => setShowExcludeModal(false)}>
                    <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
                        <h3 style={styles.modalTitle}>❌ Motivo de Exclusión</h3>
                        <select
                            value={excludeReason}
                            onChange={(e) => setExcludeReason(e.target.value)}
                            style={styles.excludeSelect}
                            autoFocus
                        >
                            {EXCLUSION_REASONS.map((r) => (
                                <option key={r} value={r}>{r}</option>
                            ))}
                        </select>
                        <div style={styles.modalActions}>
                            <button onClick={() => setShowExcludeModal(false)} style={styles.cancelButton}>
                                Cancelar
                            </button>
                            <button onClick={handleExclude} style={styles.confirmExclude}>
                                Confirmar Exclusión
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

// ── Sub-components ──

function DecisionBadge({ decision }: { decision: string }) {
    const badgeStyles: Record<string, React.CSSProperties> = {
        pending: { background: "rgba(148, 163, 184, 0.15)", color: "#94a3b8", border: "1px solid rgba(148,163,184,0.3)" },
        include: { background: "rgba(34, 197, 94, 0.15)", color: "#22c55e", border: "1px solid rgba(34,197,94,0.3)" },
        exclude: { background: "rgba(239, 68, 68, 0.15)", color: "#ef4444", border: "1px solid rgba(239,68,68,0.3)" },
        maybe: { background: "rgba(234, 179, 8, 0.15)", color: "#eab308", border: "1px solid rgba(234,179,8,0.3)" },
    };
    const labels: Record<string, string> = {
        pending: "⏳ Pendiente",
        include: "✅ Incluido",
        exclude: "❌ Excluido",
        maybe: "🟡 Tal Vez",
    };
    return (
        <span style={{ ...styles.decisionBadge, ...badgeStyles[decision] }}>
            {labels[decision] || decision}
        </span>
    );
}

function Header({
    session,
    stats,
    projectId,
    viewMode,
    setViewMode,
    filterDecision,
    setFilterDecision,
    aiAssistEnabled,
    setAiAssistEnabled,
}: {
    session: ScreeningSessionType;
    stats: ScreeningStats | null;
    projectId: string;
    viewMode: "card" | "table";
    setViewMode: (v: "card" | "table") => void;
    filterDecision: string | undefined;
    setFilterDecision: (v: string | undefined) => void;
    aiAssistEnabled: boolean;
    setAiAssistEnabled: (v: boolean) => void;
}) {
    return (
        <div style={styles.headerBar}>
            <div style={styles.headerLeft}>
                <a href={`/screening?id=${projectId}`} style={styles.backLink}>
                    ← Setup
                </a>
                <h1 style={styles.headerTitle}>🔬 Sesión de Screening</h1>
            </div>
            <div style={styles.headerControls}>
                <select
                    value={filterDecision || ""}
                    onChange={(e) => setFilterDecision(e.target.value || undefined)}
                    style={styles.filterSelect}
                >
                    <option value="">Todos</option>
                    <option value="pending">⏳ Pendientes</option>
                    <option value="include">✅ Incluidos</option>
                    <option value="exclude">❌ Excluidos</option>
                    <option value="maybe">🟡 Tal Vez</option>
                </select>
                <button
                    onClick={() => setAiAssistEnabled(!aiAssistEnabled)}
                    style={aiAssistEnabled ? styles.viewActive : styles.viewInactive}
                    title="Activar/Desactivar Sugerencias de IA"
                >
                    {aiAssistEnabled ? "🤖 AI: On" : "🤖 AI: Off"}
                </button>
                <div style={styles.viewToggle}>
                    <button
                        onClick={() => setViewMode("card")}
                        style={viewMode === "card" ? styles.viewActive : styles.viewInactive}
                    >
                        🃏 Tarjeta
                    </button>
                    <button
                        onClick={() => setViewMode("table")}
                        style={viewMode === "table" ? styles.viewActive : styles.viewInactive}
                    >
                        📋 Tabla
                    </button>
                </div>
            </div>
        </div>
    );
}

// ── Styles ──
const styles: Record<string, React.CSSProperties> = {
    container: {
        maxWidth: "1200px",
        margin: "0 auto",
        padding: "1.5rem",
        fontFamily: "'Inter', -apple-system, sans-serif",
        color: "#e2e8f0",
    },
    loadingContainer: {
        display: "flex",
        flexDirection: "column" as const,
        alignItems: "center",
        justifyContent: "center",
        minHeight: "400px",
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
    loadingText: { color: "#94a3b8" },
    emptyState: { textAlign: "center" as const, padding: "3rem" },
    backLink: {
        color: "#94a3b8",
        textDecoration: "none",
        fontSize: "0.85rem",
    },
    errorBanner: {
        background: "rgba(239, 68, 68, 0.15)",
        border: "1px solid rgba(239, 68, 68, 0.3)",
        borderRadius: "8px",
        padding: "0.75rem 1rem",
        color: "#fca5a5",
        marginBottom: "1rem",
    },
    // Header
    headerBar: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: "1.25rem",
        flexWrap: "wrap" as const,
        gap: "0.75rem",
    },
    headerLeft: { display: "flex", alignItems: "center", gap: "1rem" },
    headerTitle: { fontSize: "1.35rem", fontWeight: 700, color: "#f1f5f9", margin: 0 },
    headerControls: { display: "flex", alignItems: "center", gap: "0.75rem" },
    filterSelect: {
        background: "rgba(30, 41, 59, 0.8)",
        border: "1px solid rgba(148, 163, 184, 0.2)",
        borderRadius: "6px",
        color: "#e2e8f0",
        padding: "0.4rem 0.6rem",
        fontSize: "0.85rem",
    },
    viewToggle: { display: "flex", borderRadius: "6px", overflow: "hidden" },
    viewActive: {
        background: "rgba(96, 165, 250, 0.2)",
        color: "#93c5fd",
        border: "1px solid rgba(96,165,250,0.3)",
        padding: "0.4rem 0.75rem",
        fontSize: "0.85rem",
        cursor: "pointer",
    },
    viewInactive: {
        background: "rgba(30, 41, 59, 0.5)",
        color: "#94a3b8",
        border: "1px solid rgba(148,163,184,0.1)",
        padding: "0.4rem 0.75rem",
        fontSize: "0.85rem",
        cursor: "pointer",
    },
    // Main grid
    mainGrid: {
        display: "grid",
        gridTemplateColumns: "1fr 280px",
        gap: "1.25rem",
        alignItems: "start",
    },
    // Article card
    articleCard: {
        background: "rgba(30, 41, 59, 0.6)",
        border: "1px solid rgba(148, 163, 184, 0.1)",
        borderRadius: "12px",
        padding: "1.5rem",
        backdropFilter: "blur(10px)",
    },
    navBar: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: "1.25rem",
        padding: "0 0 0.75rem",
        borderBottom: "1px solid rgba(148,163,184,0.1)",
    },
    navButton: {
        background: "rgba(96, 165, 250, 0.1)",
        border: "1px solid rgba(96,165,250,0.2)",
        color: "#93c5fd",
        padding: "0.4rem 1rem",
        borderRadius: "6px",
        cursor: "pointer",
        fontSize: "0.85rem",
        transition: "all 0.2s",
    },
    navDisabled: { opacity: 0.4, cursor: "not-allowed" },
    navCounter: { color: "#94a3b8", fontSize: "0.9rem", fontWeight: 600 },
    articleTitle: {
        fontSize: "1.2rem",
        fontWeight: 600,
        color: "#f1f5f9",
        lineHeight: 1.4,
        margin: "0 0 0.75rem",
    },
    articleMeta: {
        display: "flex",
        flexWrap: "wrap" as const,
        gap: "0.75rem",
        fontSize: "0.82rem",
        color: "#94a3b8",
        marginBottom: "0.75rem",
    },
    doiLink: { color: "#60a5fa", textDecoration: "none" },
    sourceBadge: {
        background: "rgba(96, 165, 250, 0.15)",
        color: "#60a5fa",
        padding: "0.15rem 0.5rem",
        borderRadius: "4px",
        fontSize: "0.75rem",
        fontWeight: 600,
    },
    keywords: {
        display: "flex",
        flexWrap: "wrap" as const,
        gap: "0.35rem",
        marginBottom: "1rem",
    },
    keywordBadge: {
        background: "rgba(148, 163, 184, 0.1)",
        color: "#94a3b8",
        padding: "0.2rem 0.5rem",
        borderRadius: "4px",
        fontSize: "0.75rem",
    },
    abstractSection: {
        marginBottom: "1rem",
    },
    sectionTitle: {
        fontSize: "0.95rem",
        fontWeight: 600,
        color: "#cbd5e1",
        margin: "0 0 0.5rem",
        display: "flex",
        alignItems: "center",
        gap: "0.5rem",
    },
    abstractText: {
        fontSize: "0.9rem",
        lineHeight: 1.7,
        color: "#cbd5e1",
        margin: 0,
        whiteSpace: "pre-wrap" as const,
    },
    translateButton: {
        background: "rgba(96, 165, 250, 0.15)",
        border: "1px solid rgba(96,165,250,0.3)",
        color: "#93c5fd",
        padding: "0.25rem 0.65rem",
        borderRadius: "6px",
        fontSize: "0.78rem",
        cursor: "pointer",
        marginLeft: "auto",
    },
    translatedSection: {
        marginBottom: "1rem",
        padding: "1rem",
        background: "rgba(34, 197, 94, 0.05)",
        border: "1px solid rgba(34,197,94,0.15)",
        borderRadius: "8px",
    },
    currentDecisionBar: {
        display: "flex",
        alignItems: "center",
        gap: "0.75rem",
        marginBottom: "1rem",
        padding: "0.5rem 0.75rem",
        background: "rgba(15, 23, 42, 0.4)",
        borderRadius: "6px",
    },
    decisionBar: {
        display: "flex",
        gap: "0.5rem",
        marginTop: "1.25rem",
        paddingTop: "1.25rem",
        borderTop: "1px solid rgba(148,163,184,0.1)",
        flexWrap: "wrap" as const,
    },
    includeButton: {
        flex: 1,
        padding: "0.75rem",
        background: "linear-gradient(135deg, rgba(34,197,94,0.2), rgba(34,197,94,0.1))",
        border: "1px solid rgba(34,197,94,0.4)",
        color: "#22c55e",
        borderRadius: "8px",
        fontSize: "0.95rem",
        fontWeight: 600,
        cursor: "pointer",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: "0.5rem",
        transition: "all 0.2s",
    },
    excludeButton: {
        flex: 1,
        padding: "0.75rem",
        background: "linear-gradient(135deg, rgba(239,68,68,0.2), rgba(239,68,68,0.1))",
        border: "1px solid rgba(239,68,68,0.4)",
        color: "#ef4444",
        borderRadius: "8px",
        fontSize: "0.95rem",
        fontWeight: 600,
        cursor: "pointer",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: "0.5rem",
        transition: "all 0.2s",
    },
    maybeButton: {
        flex: 1,
        padding: "0.75rem",
        background: "linear-gradient(135deg, rgba(234,179,8,0.2), rgba(234,179,8,0.1))",
        border: "1px solid rgba(234,179,8,0.4)",
        color: "#eab308",
        borderRadius: "8px",
        fontSize: "0.95rem",
        fontWeight: 600,
        cursor: "pointer",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: "0.5rem",
        transition: "all 0.2s",
    },
    noteToggle: {
        background: "rgba(148, 163, 184, 0.1)",
        border: "1px solid rgba(148,163,184,0.2)",
        color: "#cbd5e1",
        padding: "0.25rem 0.65rem",
        borderRadius: "6px",
        cursor: "pointer",
        display: "flex",
        alignItems: "center",
        gap: "0.3rem",
        fontSize: "0.85rem",
        marginLeft: "auto",
    },
    pdfToggle: {
        background: "rgba(148, 163, 184, 0.1)",
        border: "1px solid rgba(148,163,184,0.2)",
        color: "#cbd5e1",
        padding: "0.25rem 0.65rem",
        borderRadius: "6px",
        cursor: "pointer",
        display: "flex",
        alignItems: "center",
        gap: "0.3rem",
        fontSize: "0.85rem",
    },
    pdfSection: {
        marginTop: "1.5rem",
        borderTop: "1px solid rgba(148,163,184,0.1)",
        paddingTop: "1.5rem",
    },
    pdfIframe: {
        width: "100%",
        height: "600px",
        border: "none",
        borderRadius: "8px",
        backgroundColor: "#fff",
    },
    shortcut: {
        background: "rgba(0,0,0,0.3)",
        padding: "0.1rem 0.35rem",
        borderRadius: "3px",
        fontSize: "0.7rem",
        fontFamily: "monospace",
        marginLeft: "0.25rem",
    },
    noteSection: { marginTop: "0.75rem" },
    noteInput: {
        width: "100%",
        background: "rgba(15, 23, 42, 0.5)",
        border: "1px solid rgba(148,163,184,0.2)",
        borderRadius: "8px",
        padding: "0.75rem",
        color: "#e2e8f0",
        fontSize: "0.9rem",
        resize: "vertical" as const,
        fontFamily: "inherit",
    },
    decisionBadge: {
        padding: "0.25rem 0.6rem",
        borderRadius: "6px",
        fontSize: "0.8rem",
        fontWeight: 600,
    },
    // Sidebar
    sidebar: {
        display: "flex",
        flexDirection: "column" as const,
        gap: "0.75rem",
        position: "sticky" as const,
        top: "1.5rem",
    },
    sidebarTitle: {
        fontSize: "1rem",
        fontWeight: 600,
        color: "#f1f5f9",
        margin: 0,
    },
    progressContainer: { marginBottom: "0.25rem" },
    progressBackground: {
        height: "10px",
        background: "rgba(148, 163, 184, 0.15)",
        borderRadius: "5px",
        overflow: "hidden",
        marginBottom: "0.35rem",
    },
    progressFill: {
        height: "100%",
        background: "linear-gradient(90deg, #60a5fa, #22c55e)",
        borderRadius: "5px",
        transition: "width 0.5s ease",
    },
    progressLabel: {
        fontSize: "0.82rem",
        color: "#94a3b8",
    },
    statGrid: {
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: "0.5rem",
    },
    statCard: {
        background: "rgba(30, 41, 59, 0.6)",
        borderRadius: "8px",
        padding: "0.65rem",
    },
    statNumber: {
        fontSize: "1.4rem",
        fontWeight: 700,
        color: "#f1f5f9",
    },
    statLabel: {
        fontSize: "0.75rem",
        color: "#94a3b8",
        marginTop: "0.15rem",
    },
    shortcutsCard: {
        background: "rgba(30, 41, 59, 0.6)",
        borderRadius: "8px",
        padding: "0.75rem",
        border: "1px solid rgba(148,163,184,0.1)",
    },
    shortcutsTitle: {
        fontSize: "0.85rem",
        fontWeight: 600,
        color: "#cbd5e1",
        margin: "0 0 0.5rem",
    },
    shortcutsList: {
        display: "flex",
        flexDirection: "column" as const,
        gap: "0.25rem",
        fontSize: "0.8rem",
        color: "#94a3b8",
    },
    kbd: {
        background: "rgba(15, 23, 42, 0.8)",
        border: "1px solid rgba(148,163,184,0.2)",
        borderRadius: "3px",
        padding: "0.1rem 0.35rem",
        fontSize: "0.72rem",
        fontFamily: "monospace",
        color: "#e2e8f0",
        marginRight: "0.35rem",
    },
    // Modal
    modalOverlay: {
        position: "fixed" as const,
        inset: 0,
        background: "rgba(0,0,0,0.6)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
    },
    modal: {
        background: "#1e293b",
        border: "1px solid rgba(148,163,184,0.2)",
        borderRadius: "12px",
        padding: "1.5rem",
        width: "380px",
        maxWidth: "90vw",
    },
    modalTitle: {
        fontSize: "1.1rem",
        fontWeight: 600,
        color: "#f1f5f9",
        margin: "0 0 1rem",
    },
    excludeSelect: {
        width: "100%",
        background: "rgba(15, 23, 42, 0.8)",
        border: "1px solid rgba(148,163,184,0.2)",
        borderRadius: "8px",
        color: "#e2e8f0",
        padding: "0.6rem",
        fontSize: "0.9rem",
        marginBottom: "1rem",
    },
    modalActions: {
        display: "flex",
        gap: "0.5rem",
        justifyContent: "flex-end",
    },
    cancelButton: {
        padding: "0.5rem 1rem",
        background: "transparent",
        border: "1px solid rgba(148,163,184,0.3)",
        color: "#94a3b8",
        borderRadius: "6px",
        cursor: "pointer",
        fontSize: "0.85rem",
    },
    confirmExclude: {
        padding: "0.5rem 1rem",
        background: "rgba(239, 68, 68, 0.2)",
        border: "1px solid rgba(239,68,68,0.4)",
        color: "#ef4444",
        borderRadius: "6px",
        cursor: "pointer",
        fontSize: "0.85rem",
        fontWeight: 600,
    },
    // Table
    table: {
        width: "100%",
        borderCollapse: "collapse" as const,
        fontSize: "0.85rem",
        marginTop: "0.75rem",
    },
    th: {
        textAlign: "left" as const,
        padding: "0.6rem 0.75rem",
        borderBottom: "1px solid rgba(148,163,184,0.2)",
        color: "#94a3b8",
        fontWeight: 600,
        fontSize: "0.8rem",
    },
    td: {
        padding: "0.6rem 0.75rem",
        borderBottom: "1px solid rgba(148,163,184,0.08)",
        color: "#e2e8f0",
    },
    trEven: { background: "rgba(15, 23, 42, 0.3)" },
    trOdd: { background: "transparent" },
    reviewButton: {
        background: "rgba(96, 165, 250, 0.15)",
        border: "1px solid rgba(96,165,250,0.3)",
        color: "#93c5fd",
        padding: "0.3rem 0.6rem",
        borderRadius: "4px",
        fontSize: "0.78rem",
        cursor: "pointer",
    },
    // AI Suggestions
    suggestionBox: {
        background: "rgba(15, 23, 42, 0.4)",
        borderRadius: "8px",
        padding: "0.8rem 1rem",
        marginBottom: "1rem",
        fontSize: "0.9rem",
    },
    suggestionHeader: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: "0.4rem",
    },
    suggestionReason: {
        color: "#cbd5e1",
        fontSize: "0.85rem",
        fontStyle: "italic",
        lineHeight: 1.4,
        margin: 0,
    },
    confidenceBadge: {
        background: "rgba(148, 163, 184, 0.15)",
        color: "#94a3b8",
        padding: "0.15rem 0.45rem",
        borderRadius: "4px",
        fontSize: "0.7rem",
        fontWeight: 600,
    },
    suggestionLoading: {
        display: "flex",
        alignItems: "center",
        gap: "0.6rem",
        color: "#94a3b8",
        fontSize: "0.85rem",
        marginBottom: "1rem",
        paddingLeft: "0.5rem",
    },
    miniSpinner: {
        width: "14px",
        height: "14px",
        border: "2px solid rgba(148, 163, 184, 0.2)",
        borderTopColor: "#94a3b8",
        borderRadius: "50%",
        animation: "spin 1s linear infinite",
    },
};
