/**
 * AgriSearch - Search Wizard Component.
 *
 * Multi-step wizard for: 1) Describe topic → 2) Review generated query → 3) Execute search → 4) View results → 5) Download PDFs
 */

import { useState, useEffect } from "react";
import type { GeneratedQuery, Article, SearchResults, DownloadProgress, SearchQuery } from "../lib/api";
import { buildQuery, executeSearch, downloadArticles, listArticles, getProject, openProjectFolder, getProjectSearches } from "../lib/api";

export type Step = "describe" | "review_query" | "searching" | "results" | "downloading";

export interface DbOption {
    id: string;
    label: string;
    icon: string;
    desc: string;
}

export const DB_OPTIONS: DbOption[] = [
    { id: "openalex", label: "OpenAlex", icon: "📚", desc: ">200M works" },
    { id: "semantic_scholar", label: "Semantic Scholar", icon: "🔬", desc: "AI-powered" },
    { id: "arxiv", label: "ArXiv", icon: "📄", desc: "Preprints" },
    { id: "crossref", label: "Crossref", icon: "🔗", desc: ">150M DOIs" },
    { id: "core", label: "CORE", icon: "🌐", desc: "Open Access" },
    { id: "scielo", label: "SciELO", icon: "🌎", desc: "Latinoamérica" },
    { id: "redalyc", label: "Redalyc", icon: "📖", desc: "Iberoamérica" },
    { id: "agecon", label: "AgEcon Search", icon: "🌾", desc: "Agro-economics" },
    { id: "organic_eprints", label: "Organic Eprints", icon: "🌱", desc: "Organic agri" },
];

import SearchWizardDescribe from "./SearchWizardDescribe";
import SearchWizardReview from "./SearchWizardReview";
import SearchWizardSearching from "./SearchWizardSearching";
import SearchWizardResults from "./SearchWizardResults";

export default function SearchWizard() {
    // Project info (loaded from URL param)
    const [projectId, setProjectId] = useState("");
    const [projectName, setProjectName] = useState("Cargando...");
    const [projectAgriArea, setProjectAgriArea] = useState("");
    const [projectLlmModel, setProjectLlmModel] = useState<string | undefined>();
    const [selectedLlmModel, setSelectedLlmModel] = useState<string>("deepseek-r1:14b"); // Default to a GPU recommended model

    // Check initial search params
    const initialQueryId = typeof window !== 'undefined' ? new URLSearchParams(window.location.search).get("query_id") : null;
    const [step, setStep] = useState<Step>(initialQueryId ? "results" : "describe");
    const [userInput, setUserInput] = useState("");

    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        const id = params.get("id");
        if (!id) { window.location.href = "/"; return; }
        setProjectId(id);

        getProject(id)
            .then(p => {
                setProjectName(p.name);
                setProjectAgriArea(p.agri_area);
                if (p.llm_model) {
                    setProjectLlmModel(p.llm_model);
                    setSelectedLlmModel(p.llm_model);
                }
            })
            .catch(() => window.location.href = "/");

        const queryId = params.get("query_id");
        if (queryId) {
            handleSelectHistoricalSearch(queryId, id);
        }
    }, []);

    const [yearFrom, setYearFrom] = useState<number | undefined>();
    const [yearTo, setYearTo] = useState<number | undefined>();
    const [selectedDBs, setSelectedDBs] = useState(["openalex", "semantic_scholar", "arxiv", "crossref", "core", "scielo", "redalyc", "agecon", "organic_eprints"]);
    const [maxResults, setMaxResults] = useState(50);
    const [generatedQuery, setGeneratedQuery] = useState<GeneratedQuery | null>(null);
    const [editedQuery, setEditedQuery] = useState("");
    const [searchResults, setSearchResults] = useState<SearchResults | null>(null);
    const [articles, setArticles] = useState<Article[]>([]);
    const [downloadProgress, setDownloadProgress] = useState<DownloadProgress | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    async function handleSelectHistoricalSearch(queryId: string, projId: string) {
        setLoading(true);
        setError(null);
        try {
            // First load the actual search query to get the adapted_queries info
            let searchQueryInfo = null;
            try {
                const searches = await getProjectSearches(projId);
                searchQueryInfo = searches.find(s => s.id === queryId);
            } catch (e) {
                console.warn("Could not load search query details", e);
            }

            const { articles, total } = await listArticles(projId, 0, 1000, undefined, queryId);
            setArticles(articles);
            const counts: Record<string, number> = {};
            articles.forEach(a => {
                counts[a.source_database] = (counts[a.source_database] || 0) + 1;
            });

            // Reconstruct the search results context
            setSearchResults({
                project_id: projId,
                query_id: queryId,
                total_found: total,
                duplicates_removed: searchQueryInfo?.duplicates_removed || 0,
                articles: articles,
                counts_by_source: counts,
                adapted_queries: searchQueryInfo?.adapted_queries_json ? JSON.parse(searchQueryInfo.adapted_queries_json) : undefined,
                prompt_used: searchQueryInfo?.raw_input,
                master_query: searchQueryInfo?.generated_query
            });
            setStep("results");
        } catch (e: any) {
            setError(e.message || "Error al cargar los artículos de esta búsqueda");
        } finally {
            setLoading(false);
        }
    }

    // ── Step 1: Generate Query ──
    async function handleGenerateQuery() {
        if (!userInput.trim()) return;
        setLoading(true);
        setError(null);
        try {
            const effectiveLlmModel = selectedLlmModel || projectLlmModel || "qwen2.5:7b";
            console.debug("[SearchWizard] build-query model", {
                selectedLlmModel,
                projectLlmModel,
                effectiveLlmModel,
            });

            const result = await buildQuery({
                user_input: userInput,
                year_from: yearFrom,
                year_to: yearTo,
                agri_area: projectAgriArea,
                llm_model: effectiveLlmModel,
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
                raw_prompt: userInput,
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
            const articleIds = articles.map(a => a.id);
            const result = await downloadArticles({ project_id: projectId, article_ids: articleIds });
            setDownloadProgress(result);
            // Refresh articles for current search
            const queryId = searchResults?.query_id && searchResults.query_id !== "historical" ? searchResults.query_id : undefined;
            const updated = await listArticles(projectId, 0, 1000, undefined, queryId);
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
            case "crossref": return "bg-teal-500/20 text-teal-400";
            case "core": return "bg-green-500/20 text-green-400";
            case "scielo": return "bg-yellow-500/20 text-yellow-400";
            case "redalyc": return "bg-red-500/20 text-red-400";
            case "agecon": return "bg-amber-500/20 text-amber-400";
            case "organic_eprints": return "bg-lime-500/20 text-lime-400";
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
            <div className="flex items-center gap-2 text-sm text-slate-500 mb-6">
                <a href="/" className="hover:text-emerald-400 transition-colors">Proyectos</a>
                <span>/</span>
                <a
                    href={`/project?id=${projectId}`}
                    className="text-slate-300 hover:text-emerald-400 transition-colors cursor-pointer"
                >
                    {projectName}
                </a>
                <span>/</span>
                <span className="text-emerald-400">Búsqueda Sistemática</span>
            </div>

            {/* Step indicator */}
            {searchResults?.query_id !== "historical" && step !== "results" && (
                <div className="flex items-center gap-2 mb-8 flex-wrap">
                    {[
                        { id: "describe", label: "1. Describir" },
                        { id: "review_query", label: "2. Revisar Query" },
                        { id: "searching", label: "3. Buscando" },
                        { id: "results", label: "4. Resultados" },
                    ].map((s, i) => (
                        <div key={s.id} className="flex items-center gap-2">
                            {i > 0 && <div className="w-8 h-px bg-slate-700 hidden sm:block" />}
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
            )}
            {/* Title for historical / specific search results */}
            {step === "results" && searchResults && (
                <div className="flex items-center justify-between mb-8">
                    <div>
                        <h2 className="text-2xl font-bold text-white mb-2">
                            {searchResults.query_id && searchResults.query_id !== "historical"
                                ? `Resultados de Búsqueda`
                                : "Historial de Búsqueda Acumulado"}
                        </h2>
                        <p className="text-slate-400">
                            {searchResults.query_id && searchResults.query_id !== "historical"
                                ? "Artículos obtenidos para esta consulta específica."
                                : "Estos son los resultados de la última búsqueda sistemática guardada."}
                        </p>
                    </div>
                    <a
                        href={`/project?id=${projectId}`}
                        className="px-4 py-2 text-slate-400 hover:text-white border border-slate-700 rounded-xl transition-colors"
                    >
                        Volver a Búsquedas
                    </a>
                </div>
            )}
            {/* Error Banner */}
            {error && (
                <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-sm flex items-center justify-between">
                    <span>⚠️ {error}</span>
                    <button onClick={() => setError(null)} className="text-red-300 hover:text-white">✕</button>
                </div>
            )}

            {/* ── STEP 1: Describe ── */}
            {step === "describe" && (
                <SearchWizardDescribe
                    userInput={userInput}
                    setUserInput={setUserInput}
                    yearFrom={yearFrom}
                    setYearFrom={setYearFrom}
                    yearTo={yearTo}
                    setYearTo={setYearTo}
                    maxResults={maxResults}
                    setMaxResults={setMaxResults}
                    selectedDBs={selectedDBs}
                    toggleDB={toggleDB}
                    handleGenerateQuery={handleGenerateQuery}
                    loading={loading}
                    agriArea={projectAgriArea}
                    selectedLlmModel={selectedLlmModel}
                    setSelectedLlmModel={setSelectedLlmModel}
                />
            )}

            {/* ── STEP 2: Review Query ── */}
            {step === "review_query" && generatedQuery && (
                <SearchWizardReview
                    generatedQuery={generatedQuery}
                    editedQuery={editedQuery}
                    setEditedQuery={setEditedQuery}
                    setStep={setStep}
                    handleExecuteSearch={handleExecuteSearch}
                />
            )}

            {/* ── STEP 3: Searching ── */}
            {step === "searching" && (
                <SearchWizardSearching
                    selectedDBs={selectedDBs}
                    sourceColor={sourceColor}
                />
            )}

            {/* ── STEP 4: Results ── */}
            {step === "results" && searchResults && (
                <SearchWizardResults
                    searchResults={searchResults}
                    articles={articles}
                    loading={loading}
                    downloadProgress={downloadProgress}
                    projectId={projectId}
                    handleDownload={handleDownload}
                    openProjectFolder={openProjectFolder}
                    sourceColor={sourceColor}
                    statusBadge={statusBadge}
                    onArticleUpdated={(updated) => {
                        setArticles(prev => prev.map(a => a.id === updated.id ? updated : a));
                    }}
                />
            )}
        </div>
    );
}
