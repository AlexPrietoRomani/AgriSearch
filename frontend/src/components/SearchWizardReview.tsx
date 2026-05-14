import React, { useState, useEffect } from "react";
import { type GeneratedQuery, previewQueries } from "../lib/api";

type Step = "describe" | "review_query" | "searching" | "results" | "downloading";

interface Props {
    generatedQuery: GeneratedQuery;
    editedQuery: string;
    setEditedQuery: (val: string) => void;
    setStep: (val: Step) => void;
    handleExecuteSearch: () => void;
    selectedDBs: string[];
}

const DB_LABEL: Record<string, string> = {
    openalex: "OpenAlex",
    semantic_scholar: "Semantic Scholar",
    arxiv: "ArXiv",
    crossref: "Crossref",
    core: "CORE",
    scielo: "SciELO",
    redalyc: "Redalyc",
    agecon: "AgEcon Search",
    organic_eprints: "Organic Eprints",
};

const DB_COLOR: Record<string, string> = {
    openalex: "text-blue-400 border-blue-500/30 bg-blue-500/5",
    semantic_scholar: "text-purple-400 border-purple-500/30 bg-purple-500/5",
    arxiv: "text-orange-400 border-orange-500/30 bg-orange-500/5",
    crossref: "text-teal-400 border-teal-500/30 bg-teal-500/5",
    core: "text-green-400 border-green-500/30 bg-green-500/5",
    scielo: "text-yellow-400 border-yellow-500/30 bg-yellow-500/5",
    redalyc: "text-red-400 border-red-500/30 bg-red-500/5",
    agecon: "text-amber-400 border-amber-500/30 bg-amber-500/5",
    organic_eprints: "text-lime-400 border-lime-500/30 bg-lime-500/5",
};

export default function SearchWizardReview({
    generatedQuery,
    editedQuery,
    setEditedQuery,
    setStep,
    handleExecuteSearch,
    selectedDBs,
}: Props) {
    const [adaptedQueries, setAdaptedQueries] = useState<Record<string, string>>({});
    const [loadingPreview, setLoadingPreview] = useState(false);
    const [showPreview, setShowPreview] = useState(true);

    const fetchPreview = async () => {
        if (!editedQuery.trim() || selectedDBs.length === 0) return;

        setLoadingPreview(true);
        try {
            const data = await previewQueries({
                boolean_query: editedQuery,
                databases: selectedDBs,
            });
            setAdaptedQueries(data.adapted_queries || {});
        } catch (e) {
            console.error("Error fetching preview:", e);
        } finally {
            setLoadingPreview(false);
        }
    };

    // Cargar la preview inicialmente cuando se detectan bases de datos seleccionadas
    useEffect(() => {
        if (selectedDBs.length > 0 && Object.keys(adaptedQueries).length === 0) {
            fetchPreview();
        }
    }, [selectedDBs]);

    return (
        <div className="max-w-4xl">
            <h2 className="text-2xl font-bold text-white mb-2">Revisa la Query Generada</h2>
            <p className="text-slate-400 mb-6">Puedes editar la query antes de ejecutar la búsqueda.</p>

            {/* PICO Breakdown */}
            {Object.keys(generatedQuery.pico_breakdown).length > 0 && (
                <div className="grid grid-cols-2 gap-3 mb-6">
                    {Object.entries(generatedQuery.pico_breakdown).map(([key, value]) => (
                        <div key={key} className="p-3 bg-slate-800/50 border border-slate-700/50 rounded-xl">
                            <span className="text-xs text-emerald-400 font-semibold uppercase">{key}</span>
                            <p className="text-sm text-slate-300 mt-1">{value as React.ReactNode}</p>
                        </div>
                    ))}
                </div>
            )}

            {/* Suggested Terms */}
            {generatedQuery.suggested_terms?.length > 0 && (
                <div className="mb-4">
                    <span className="text-sm text-slate-400">Términos sugeridos:</span>
                    <div className="flex flex-wrap gap-2 mt-2">
                        {generatedQuery.suggested_terms.map((term: string) => (
                            <span key={term} className="px-2.5 py-1 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-lg text-xs font-medium">
                                {term}
                            </span>
                        ))}
                    </div>
                </div>
            )}

            {/* Editable Query */}
            <label className="block mb-4">
                <span className="text-sm text-slate-400 font-medium">Query maestra booleana (editable)</span>
                <textarea
                    value={editedQuery}
                    onChange={(e) => setEditedQuery(e.target.value)}
                    rows={4}
                    className="mt-1 w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-xl text-white font-mono text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all resize-none"
                />
            </label>

            {/* Preview de queries adaptadas por BD */}
            <div className="mb-6 bg-slate-900/60 border border-slate-700/50 rounded-xl overflow-hidden">
                <div className="flex items-center justify-between px-5 py-3 border-b border-slate-700/50 bg-slate-800/30">
                    <button
                        onClick={() => setShowPreview(!showPreview)}
                        className="flex items-center gap-2 font-semibold text-sm text-slate-300 hover:text-indigo-400 transition-colors"
                    >
                        <svg className={`w-4 h-4 transition-transform duration-300 ${showPreview ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                        Preview: Queries que se enviarán a cada API
                    </button>
                    <button
                        onClick={fetchPreview}
                        disabled={loadingPreview || !editedQuery.trim()}
                        className="flex items-center gap-2 px-3 py-1.5 bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/30 text-indigo-400 rounded-lg text-xs font-medium transition-colors disabled:opacity-50"
                    >
                        {loadingPreview ? (
                            <div className="w-3.5 h-3.5 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
                        ) : (
                            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                            </svg>
                        )}
                        Actualizar Preview
                    </button>
                </div>

                {showPreview && (
                    <div className="p-4">
                        {Object.keys(adaptedQueries).length === 0 ? (
                            <p className="text-slate-500 text-xs italic text-center py-4">
                                {loadingPreview ? "Calculando queries..." : "Haz clic en 'Actualizar Preview' para ver las queries."}
                            </p>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                {Object.entries(adaptedQueries).map(([db, query]) => (
                                    <div
                                        key={db}
                                        className={`p-3 rounded-xl border ${DB_COLOR[db] || "text-slate-400 border-slate-700/50 bg-slate-800/30"}`}
                                    >
                                        <div className="flex items-center gap-1.5 mb-1.5">
                                            <span className="text-[10px] font-bold uppercase tracking-widest opacity-80">
                                                {DB_LABEL[db] || db}
                                            </span>
                                        </div>
                                        <div className="text-[11px] font-mono break-all leading-relaxed opacity-90">
                                            {query}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                        <p className="text-[10px] text-slate-600 mt-3 text-center">
                            ℹ️ Cada API tiene su propio formato de búsqueda. ArXiv y SciELO usan booleanos; Semantic Scholar usa relevancia semántica.
                        </p>
                    </div>
                )}
            </div>

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
    );
}
