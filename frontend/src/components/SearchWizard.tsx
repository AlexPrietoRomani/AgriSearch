/**
 * AgriSearch - Search Wizard Component.
 *
 * Multi-step wizard for: 1) Describe topic → 2) Review generated query → 3) Execute search → 4) View results → 5) Download PDFs
 */

import { useState, useEffect } from "react";
import type { GeneratedQuery, Article, SearchResults, DownloadProgress } from "../lib/api";
import { buildQuery, executeSearch, downloadArticles, listArticles, getProject } from "../lib/api";

type Step = "describe" | "review_query" | "searching" | "results" | "downloading";

const DB_OPTIONS = [
    { id: "openalex", label: "OpenAlex", icon: "📚", desc: ">200M works" },
    { id: "semantic_scholar", label: "Semantic Scholar", icon: "🔬", desc: "AI-powered" },
    { id: "arxiv", label: "ArXiv", icon: "📄", desc: "Preprints" },
];

export default function SearchWizard() {
    // Project info (loaded from URL param)
    const [projectId, setProjectId] = useState("");
    const [projectName, setProjectName] = useState("Cargando...");

    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        const id = params.get("id");
        if (!id) { window.location.href = "/"; return; }
        setProjectId(id);
        getProject(id).then(async (p) => {
            setProjectName(p.name);
            try {
                const { articles, total } = await listArticles(id, 0, 500);
                if (total > 0) {
                    setArticles(articles);
                    const counts: Record<string, number> = {};
                    articles.forEach(a => {
                        counts[a.source_database] = (counts[a.source_database] || 0) + 1;
                    });
                    setSearchResults({
                        project_id: id,
                        query_id: "historical",
                        total_found: total,
                        duplicates_removed: 0,
                        articles: articles,
                        counts_by_source: counts
                    });
                    setStep("results");
                }
            } catch (e) {
                console.error("No historical articles loaded", e);
            }
        }).catch(() => window.location.href = "/");
    }, []);
    // State
    const [step, setStep] = useState<Step>("describe");
    const [userInput, setUserInput] = useState("");
    const [yearFrom, setYearFrom] = useState<number | undefined>();
    const [yearTo, setYearTo] = useState<number | undefined>();
    const [selectedDBs, setSelectedDBs] = useState(["openalex", "semantic_scholar", "arxiv"]);
    const [maxResults, setMaxResults] = useState(50);
    const [generatedQuery, setGeneratedQuery] = useState<GeneratedQuery | null>(null);
    const [editedQuery, setEditedQuery] = useState("");
    const [searchResults, setSearchResults] = useState<SearchResults | null>(null);
    const [articles, setArticles] = useState<Article[]>([]);
    const [downloadProgress, setDownloadProgress] = useState<DownloadProgress | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [expandedAbstract, setExpandedAbstract] = useState<string | null>(null);

    // ── Step 1: Generate Query ──
    async function handleGenerateQuery() {
        if (!userInput.trim()) return;
        setLoading(true);
        setError(null);
        try {
            const result = await buildQuery({
                user_input: userInput,
                year_from: yearFrom,
                year_to: yearTo,
            });
            setGeneratedQuery(result);
            setEditedQuery(result.boolean_query);
            setStep("review_query");
        } catch (e: any) {
            setError(e.message || "Error al generar la query");
        } finally {
            setLoading(false);
        }
    }

    // ── Step 3: Execute Search ──
    async function handleExecuteSearch() {
        setStep("searching");
        setLoading(true);
        setError(null);
        try {
            const result = await executeSearch({
                project_id: projectId,
                query: editedQuery,
                databases: selectedDBs,
                max_results_per_source: maxResults,
                year_from: yearFrom,
                year_to: yearTo,
            });
            setSearchResults(result);
            setArticles(result.articles);
            setStep("results");
        } catch (e: any) {
            setError(e.message || "Error en la búsqueda");
            setStep("review_query");
        } finally {
            setLoading(false);
        }
    }

    // ── Step 5: Download PDFs ──
    async function handleDownload() {
        setStep("downloading");
        setLoading(true);
        setError(null);
        try {
            const result = await downloadArticles({ project_id: projectId });
            setDownloadProgress(result);
            // Refresh articles
            const updated = await listArticles(projectId, 0, 500);
            setArticles(updated.articles);
        } catch (e: any) {
            setError(e.message || "Error en la descarga");
        } finally {
            setLoading(false);
            setStep("results");
        }
    }

    function toggleDB(id: string) {
        setSelectedDBs((prev) =>
            prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id]
        );
    }

    // Source badge color
    function sourceColor(db: string) {
        switch (db) {
            case "openalex": return "bg-blue-500/20 text-blue-400";
            case "semantic_scholar": return "bg-purple-500/20 text-purple-400";
            case "arxiv": return "bg-orange-500/20 text-orange-400";
            default: return "bg-slate-500/20 text-slate-400";
        }
    }

    function statusBadge(status: string) {
        switch (status) {
            case "success": return "bg-emerald-500/20 text-emerald-400";
            case "failed": return "bg-red-500/20 text-red-400";
            case "paywall": return "bg-yellow-500/20 text-yellow-400";
            default: return "bg-slate-500/20 text-slate-400";
        }
    }

    return (
        <div>
            {/* Breadcrumb */}
            <div className="flex items-center gap-2 text-sm text-slate-500 mb-6">
                <a href="/" className="hover:text-emerald-400 transition-colors">Proyectos</a>
                <span>/</span>
                <span className="text-slate-300">{projectName}</span>
                <span>/</span>
                <span className="text-emerald-400">Búsqueda Sistemática</span>
            </div>

            {/* Step indicator */}
            <div className="flex items-center gap-2 mb-8">
                {[
                    { id: "describe", label: "1. Describir" },
                    { id: "review_query", label: "2. Revisar Query" },
                    { id: "searching", label: "3. Buscando" },
                    { id: "results", label: "4. Resultados" },
                ].map((s, i) => (
                    <div key={s.id} className="flex items-center gap-2">
                        {i > 0 && <div className="w-8 h-px bg-slate-700" />}
                        <div
                            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${step === s.id
                                ? "bg-emerald-500 text-white shadow-lg shadow-emerald-500/25"
                                : ["describe", "review_query", "searching", "results"].indexOf(step) > ["describe", "review_query", "searching", "results"].indexOf(s.id)
                                    ? "bg-emerald-500/20 text-emerald-400"
                                    : "bg-slate-800 text-slate-500"
                                }`}
                        >
                            {s.label}
                        </div>
                    </div>
                ))}
            </div>

            {/* Error Banner */}
            {error && (
                <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-sm flex items-center justify-between">
                    <span>⚠️ {error}</span>
                    <button onClick={() => setError(null)} className="text-red-300 hover:text-white">✕</button>
                </div>
            )}

            {/* ── STEP 1: Describe ── */}
            {step === "describe" && (
                <div className="max-w-3xl">
                    <h2 className="text-2xl font-bold text-white mb-2">¿Qué quieres investigar?</h2>
                    <p className="text-slate-400 mb-6">
                        Describe en lenguaje natural tu tema de investigación agrícola. El LLM generará una query optimizada.
                    </p>

                    <textarea
                        value={userInput}
                        onChange={(e) => setUserInput(e.target.value)}
                        placeholder="Ej: Quiero investigar el control biológico de Telenomus podisi como parasitoide de huevos de chinches (Euschistus heros) en cultivos de soja en Sudamérica, evaluando tasas de parasitismo y eficacia en campo..."
                        rows={5}
                        className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all resize-none mb-4"
                    />

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
                        <label className="block">
                            <span className="text-sm text-slate-400">Año desde</span>
                            <input
                                type="number"
                                value={yearFrom || ""}
                                onChange={(e) => setYearFrom(e.target.value ? parseInt(e.target.value) : undefined)}
                                placeholder="2015"
                                className="mt-1 w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                            />
                        </label>
                        <label className="block">
                            <span className="text-sm text-slate-400">Año hasta</span>
                            <input
                                type="number"
                                value={yearTo || ""}
                                onChange={(e) => setYearTo(e.target.value ? parseInt(e.target.value) : undefined)}
                                placeholder="2025"
                                className="mt-1 w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                            />
                        </label>
                        <label className="block">
                            <span className="text-sm text-slate-400">Máx por fuente</span>
                            <input
                                type="number"
                                value={maxResults}
                                onChange={(e) => setMaxResults(parseInt(e.target.value) || 50)}
                                min={10}
                                max={500}
                                className="mt-1 w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                            />
                        </label>
                    </div>

                    {/* Database Selection */}
                    <div className="mb-6">
                        <span className="text-sm text-slate-400 block mb-2">Bases de datos a consultar</span>
                        <div className="flex gap-3">
                            {DB_OPTIONS.map((db) => (
                                <button
                                    key={db.id}
                                    onClick={() => toggleDB(db.id)}
                                    className={`flex items-center gap-2 px-4 py-2.5 rounded-xl border transition-all duration-200 ${selectedDBs.includes(db.id)
                                        ? "bg-emerald-500/10 border-emerald-500/40 text-emerald-300"
                                        : "bg-slate-800 border-slate-700 text-slate-500 hover:border-slate-600"
                                        }`}
                                >
                                    <span>{db.icon}</span>
                                    <span className="font-medium">{db.label}</span>
                                    <span className="text-xs opacity-60">{db.desc}</span>
                                </button>
                            ))}
                        </div>
                    </div>

                    <button
                        onClick={handleGenerateQuery}
                        disabled={loading || !userInput.trim() || selectedDBs.length === 0}
                        className="px-6 py-3 bg-gradient-to-r from-emerald-500 to-green-600 text-white font-semibold rounded-xl shadow-lg shadow-emerald-500/25 hover:shadow-emerald-500/50 hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 transition-all duration-200 flex items-center gap-2"
                    >
                        {loading ? (
                            <>
                                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                Generando query...
                            </>
                        ) : (
                            "🔍 Generar Query con IA"
                        )}
                    </button>
                </div>
            )}

            {/* ── STEP 2: Review Query ── */}
            {step === "review_query" && generatedQuery && (
                <div className="max-w-3xl">
                    <h2 className="text-2xl font-bold text-white mb-2">Revisa la Query Generada</h2>
                    <p className="text-slate-400 mb-6">Puedes editar la query antes de ejecutar la búsqueda.</p>

                    {/* PICO Breakdown */}
                    {Object.keys(generatedQuery.pico_breakdown).length > 0 && (
                        <div className="grid grid-cols-2 gap-3 mb-6">
                            {Object.entries(generatedQuery.pico_breakdown).map(([key, value]) => (
                                <div key={key} className="p-3 bg-slate-800/50 border border-slate-700/50 rounded-xl">
                                    <span className="text-xs text-emerald-400 font-semibold uppercase">{key}</span>
                                    <p className="text-sm text-slate-300 mt-1">{value}</p>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Suggested Terms */}
                    {generatedQuery.suggested_terms.length > 0 && (
                        <div className="mb-4">
                            <span className="text-sm text-slate-400">Términos sugeridos:</span>
                            <div className="flex flex-wrap gap-2 mt-2">
                                {generatedQuery.suggested_terms.map((term) => (
                                    <span key={term} className="px-2.5 py-1 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-lg text-xs font-medium">
                                        {term}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Editable Query */}
                    <label className="block mb-4">
                        <span className="text-sm text-slate-400 font-medium">Query de búsqueda (editable)</span>
                        <textarea
                            value={editedQuery}
                            onChange={(e) => setEditedQuery(e.target.value)}
                            rows={4}
                            className="mt-1 w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-xl text-white font-mono text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all resize-none"
                        />
                    </label>

                    {/* Explanation */}
                    {generatedQuery.explanation && (
                        <div className="p-4 bg-slate-800/30 border border-slate-700/50 rounded-xl mb-6">
                            <span className="text-xs text-slate-500 uppercase font-semibold">Explicación de la estrategia</span>
                            <p className="text-sm text-slate-300 mt-1">{generatedQuery.explanation}</p>
                        </div>
                    )}

                    <div className="flex gap-3">
                        <button
                            onClick={() => setStep("describe")}
                            className="px-4 py-2.5 text-slate-400 hover:text-white border border-slate-700 rounded-xl transition-colors"
                        >
                            ← Volver
                        </button>
                        <button
                            onClick={handleExecuteSearch}
                            disabled={!editedQuery.trim()}
                            className="px-6 py-2.5 bg-gradient-to-r from-emerald-500 to-green-600 text-white font-semibold rounded-xl shadow-lg shadow-emerald-500/25 hover:shadow-emerald-500/50 hover:scale-[1.02] disabled:opacity-50 transition-all duration-200 flex items-center gap-2"
                        >
                            🚀 Ejecutar Búsqueda
                        </button>
                    </div>
                </div>
            )}

            {/* ── STEP 3: Searching ── */}
            {step === "searching" && (
                <div className="flex flex-col items-center justify-center py-20">
                    <div className="w-16 h-16 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin mb-6" />
                    <h2 className="text-xl text-white font-semibold mb-2">Buscando artículos...</h2>
                    <p className="text-slate-400">Consultando {selectedDBs.length} bases de datos en paralelo</p>
                    <div className="flex gap-3 mt-4">
                        {selectedDBs.map((db) => (
                            <span key={db} className={`px-3 py-1 rounded-lg text-xs font-medium animate-pulse ${sourceColor(db)}`}>
                                {DB_OPTIONS.find((d) => d.id === db)?.label}
                            </span>
                        ))}
                    </div>
                </div>
            )}

            {/* ── STEP 4: Results ── */}
            {step === "results" && searchResults && (
                <div>
                    {/* Stats Bar */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
                        <div className="p-4 bg-slate-800/50 border border-slate-700/50 rounded-xl text-center">
                            <div className="text-2xl font-bold text-emerald-400">{searchResults.total_found}</div>
                            <div className="text-xs text-slate-400 mt-1">Artículos Únicos</div>
                        </div>
                        <div className="p-4 bg-slate-800/50 border border-slate-700/50 rounded-xl text-center">
                            <div className="text-2xl font-bold text-yellow-400">{searchResults.duplicates_removed}</div>
                            <div className="text-xs text-slate-400 mt-1">Duplicados Removidos</div>
                        </div>
                        {Object.entries(searchResults.counts_by_source).map(([source, count]) => (
                            <div key={source} className="p-4 bg-slate-800/50 border border-slate-700/50 rounded-xl text-center">
                                <div className="text-2xl font-bold text-slate-200">{count}</div>
                                <div className="text-xs text-slate-400 mt-1">{source}</div>
                            </div>
                        ))}
                    </div>

                    {/* Download Progress */}
                    {downloadProgress && (
                        <div className="mb-6 p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl">
                            <div className="flex items-center gap-6 text-sm">
                                <span className="text-emerald-400 font-medium">✅ {downloadProgress.downloaded} descargados</span>
                                <span className="text-red-400">❌ {downloadProgress.failed} fallidos</span>
                                <span className="text-yellow-400">🔒 {downloadProgress.paywall} paywall</span>
                            </div>
                        </div>
                    )}

                    {/* Actions */}
                    <div className="flex gap-3 mb-6">
                        <button
                            onClick={() => setStep("describe")}
                            className="px-4 py-2 text-slate-400 hover:text-white border border-slate-700 rounded-xl transition-colors"
                        >
                            + Nueva Búsqueda
                        </button>
                        <button
                            onClick={handleDownload}
                            disabled={loading}
                            className="px-5 py-2 bg-gradient-to-r from-blue-500 to-indigo-600 text-white font-semibold rounded-xl shadow-lg hover:shadow-blue-500/25 hover:scale-[1.02] disabled:opacity-50 transition-all flex items-center gap-2"
                        >
                            {loading ? (
                                <>
                                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                    Descargando...
                                </>
                            ) : (
                                "📥 Descargar PDFs Open Access"
                            )}
                        </button>
                    </div>

                    {/* Articles Table */}
                    <div className="border border-slate-700/50 rounded-2xl overflow-hidden">
                        <table className="w-full text-sm">
                            <thead className="bg-slate-800/80">
                                <tr>
                                    <th className="text-left px-4 py-3 text-slate-400 font-medium">Título</th>
                                    <th className="text-left px-4 py-3 text-slate-400 font-medium w-20">Año</th>
                                    <th className="text-left px-4 py-3 text-slate-400 font-medium w-32">Fuente</th>
                                    <th className="text-left px-4 py-3 text-slate-400 font-medium w-28">Estado</th>
                                    <th className="text-left px-4 py-3 text-slate-400 font-medium w-24">DOI</th>
                                </tr>
                            </thead>
                            <tbody>
                                {articles.map((a) => (
                                    <tr key={a.id} className="border-t border-slate-700/30 hover:bg-slate-800/30 transition-colors">
                                        <td className="px-4 py-3">
                                            <div>
                                                <button
                                                    onClick={() => setExpandedAbstract(expandedAbstract === a.id ? null : a.id)}
                                                    className="text-left text-slate-200 hover:text-emerald-300 transition-colors font-medium line-clamp-2"
                                                >
                                                    {a.title}
                                                </button>
                                                {a.authors && <p className="text-xs text-slate-500 mt-1 line-clamp-1">{a.authors}</p>}
                                                {expandedAbstract === a.id && a.abstract && (
                                                    <p className="text-xs text-slate-400 mt-2 p-3 bg-slate-800/50 rounded-lg leading-relaxed">
                                                        {a.abstract}
                                                    </p>
                                                )}
                                            </div>
                                        </td>
                                        <td className="px-4 py-3 text-slate-400">{a.year || "—"}</td>
                                        <td className="px-4 py-3">
                                            <span className={`px-2 py-1 rounded-lg text-xs font-medium ${sourceColor(a.source_database)}`}>
                                                {a.source_database}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3">
                                            <span className={`px-2 py-1 rounded-lg text-xs font-medium ${statusBadge(a.download_status)}`}>
                                                {a.download_status}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3">
                                            {a.doi ? (
                                                <a
                                                    href={`https://doi.org/${a.doi}`}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="text-emerald-400 hover:text-emerald-300 text-xs underline"
                                                >
                                                    DOI ↗
                                                </a>
                                            ) : (
                                                <span className="text-slate-600 text-xs">—</span>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    );
}
