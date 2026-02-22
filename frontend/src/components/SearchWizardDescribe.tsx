import React from "react";
import { DB_OPTIONS, type DbOption } from "./SearchWizard";

interface Props {
    userInput: string;
    setUserInput: (val: string) => void;
    yearFrom: number | undefined;
    setYearFrom: (val: number | undefined) => void;
    yearTo: number | undefined;
    setYearTo: (val: number | undefined) => void;
    maxResults: number;
    setMaxResults: (val: number) => void;
    selectedDBs: string[];
    toggleDB: (id: string) => void;
    handleGenerateQuery: () => void;
    loading: boolean;
}

export default function SearchWizardDescribe({
    userInput,
    setUserInput,
    yearFrom,
    setYearFrom,
    yearTo,
    setYearTo,
    maxResults,
    setMaxResults,
    selectedDBs,
    toggleDB,
    handleGenerateQuery,
    loading
}: Props) {
    return (
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
                <div className="flex gap-3 flex-wrap">
                    {DB_OPTIONS.map((db: DbOption) => (
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
                            <span className="text-xs opacity-60 hidden sm:inline">{db.desc}</span>
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
    );
}
