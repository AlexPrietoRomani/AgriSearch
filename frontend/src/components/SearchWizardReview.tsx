import React from "react";
import type { GeneratedQuery } from "../lib/api";

type Step = "describe" | "review_query" | "searching" | "results" | "downloading";

interface Props {
    generatedQuery: GeneratedQuery;
    editedQuery: string;
    setEditedQuery: (val: string) => void;
    setStep: (val: Step) => void;
    handleExecuteSearch: () => void;
}

export default function SearchWizardReview({
    generatedQuery,
    editedQuery,
    setEditedQuery,
    setStep,
    handleExecuteSearch
}: Props) {
    return (
        <div className="max-w-3xl">
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
    );
}
