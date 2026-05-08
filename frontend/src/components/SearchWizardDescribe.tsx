import React from "react";
import { DB_OPTIONS, type DbOption } from "./SearchWizard";
import { useOllamaModels } from "../hooks/useOllamaModels";
import type { DBStatus } from "../lib/api";

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
    agriArea?: string;
    selectedLlmModel: string;
    setSelectedLlmModel: (val: string) => void;
    dbStatus?: Record<string, DBStatus>;
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
    loading,
    agriArea,
    selectedLlmModel,
    setSelectedLlmModel,
    dbStatus
}: Props) {
    const { models, recommendedModel, loading: modelsLoading, error: modelsError } = useOllamaModels();
    const [isCustomModel, setIsCustomModel] = React.useState(false);
    const [customModelName, setCustomModelName] = React.useState("");

    React.useEffect(() => {
        // Auto-select recommended model if no model is selected yet
        if (!selectedLlmModel && recommendedModel) {
            setSelectedLlmModel(recommendedModel);
        }
    }, [recommendedModel, selectedLlmModel, setSelectedLlmModel]);

    React.useEffect(() => {
        // If the initial selected model isn't in the dynamic list, it must be custom
        if (selectedLlmModel && models.length > 0) {
            const isAvailable = models.some(m => m.name === selectedLlmModel);
            if (!isAvailable) {
                setIsCustomModel(true);
                setCustomModelName(selectedLlmModel);
            }
        }
    }, [models, selectedLlmModel]);

    const handleModelChange = (val: string) => {
        if (val === "custom") {
            setIsCustomModel(true);
        } else {
            setIsCustomModel(false);
            setSelectedLlmModel(val);
        }
    };

    const handleCustomSubmit = () => {
        if (customModelName.trim()) {
            setSelectedLlmModel(customModelName.trim());
        }
    };
    return (
        <div className="max-w-3xl">
            <h2 className="text-2xl font-bold text-white mb-2">¿Qué quieres investigar?</h2>
            <p className="text-slate-400 mb-6">
                Describe en lenguaje natural tu tema de investigación agrícola. El LLM generará una query optimizada.
            </p>

            {agriArea && (
                <div className="mb-6 flex items-center gap-2 px-4 py-2 bg-emerald-500/5 border border-emerald-500/20 rounded-xl">
                    <span className="text-emerald-500 font-bold text-xs uppercase tracking-wider">Contexto del Proyecto:</span>
                    <span className="px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 text-xs font-semibold">
                        {agriArea === "general" ? "Agricultura General" : agriArea}
                    </span>
                    <span className="text-[10px] text-slate-500 ml-auto flex items-center gap-1">
                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                        El sistema filtrará automáticamente para excluir medicina humana y otras áreas.
                    </span>
                </div>
            )}

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
                    {DB_OPTIONS.map((db: DbOption) => {
                        const status = dbStatus?.[db.id];
                        const isDisabled = status?.requires_key && !status?.key_configured;
                        const needsKey = status?.requires_key && status?.key_configured;
                        const notDownloadable = status && !status.downloadable;

                        return (
                            <button
                                key={db.id}
                                onClick={() => toggleDB(db.id)}
                                title={status?.note || db.desc}
                                className={`flex items-center gap-2 px-4 py-2.5 rounded-xl border transition-all duration-200 ${
                                    isDisabled
                                        ? "bg-red-500/5 border-red-500/20 text-red-400/50 cursor-not-allowed opacity-50"
                                        : selectedDBs.includes(db.id)
                                            ? "bg-emerald-500/10 border-emerald-500/40 text-emerald-300"
                                            : "bg-slate-800 border-slate-700 text-slate-500 hover:border-slate-600"
                                }`}
                            >
                                <span>{db.icon}</span>
                                <span className="font-medium">{db.label}</span>
                                <span className="text-xs opacity-60 hidden sm:inline">{db.desc}</span>
                                {/* Status indicators */}
                                {isDisabled && <span className="text-[10px]" title="Requiere API key">🔴</span>}
                                {needsKey && !isDisabled && <span className="text-[10px]" title="API key configurada">🟢</span>}
                                {notDownloadable && <span className="text-[10px]" title="Solo DOIs, sin descarga directa">🟡</span>}
                            </button>
                        );
                    })}
                </div>
                {(selectedDBs.includes("core") || selectedDBs.includes("redalyc")) && (
                    <div className="mt-4 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg text-yellow-400 text-sm flex items-start gap-3">
                        <span className="text-lg">⚠️</span>
                        <div>
                            <strong>Aviso importante:</strong> Para buscar en <strong>CORE</strong> o <strong>Redalyc</strong>, debes configurar sus credenciales (gratuitas) en el archivo <code>backend/.env</code> (puedes crear uno copiando <code>.env.example</code>). Si no configuras la API Key o Token, esa base devolverá 0 resultados.
                        </div>
                    </div>
                )}
            </div>

            {/* Model Selection */}
            <div className="mb-6 bg-slate-900/40 p-5 rounded-2xl border border-slate-800 shadow-inner">
                <div className="flex items-center gap-2 mb-4">
                    <span className="text-sm font-bold text-slate-300 uppercase tracking-tighter">🤖 Cerebro IA (Modelo LLM)</span>
                    <div className="group relative">
                        <svg className="w-4 h-4 text-slate-500 cursor-help" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-3 bg-slate-950 border border-slate-700 rounded-xl text-xs text-slate-300 shadow-2xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50 leading-relaxed">
                            <p className="font-bold text-emerald-400 mb-1">Configuración de Ollama:</p>
                            Si usas un modelo personalizado, asegúrate de haberlo descargado antes con: <code className="bg-slate-800 px-1 rounded text-white">ollama run nombre_del_modelo</code>.
                            Usa el formato exacto de Ollama (ej: <code className="bg-slate-800 px-1 rounded text-white">llama3:70b</code>).
                        </div>
                    </div>
                </div>

                <div className="flex flex-col sm:flex-row gap-4">
                    <div className="flex-grow">
                        {modelsError && (
                            <div className="mb-2 p-2 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-xs">
                                ⚠ No se pudieron cargar modelos de Ollama. ¿Está corriendo? (<code>ollama serve</code>)
                            </div>
                        )}
                        <select
                            value={isCustomModel ? "custom" : selectedLlmModel}
                            onChange={(e) => handleModelChange(e.target.value)}
                            disabled={modelsLoading}
                            className="w-full px-4 py-2.5 bg-slate-800 border border-slate-700 rounded-xl text-white focus:ring-2 focus:ring-emerald-500 focus:outline-none text-sm transition-all"
                        >
                            <option value="">
                                {modelsLoading ? "Cargando modelos..." : "Seleccionar modelo..."}
                            </option>
                            {models.map(m => (
                                <option key={m.name} value={m.name}>
                                    {m.name} {m.is_multimodal ? '📸' : '📝'} ({m.size.toFixed(1)} GB)
                                </option>
                            ))}
                            <option value="custom">✍️ Otro modelo (Manual)</option>
                        </select>
                        <p className="mt-2 text-[10px] text-slate-500 italic px-1">
                            {isCustomModel
                                ? "Ingresa el nombre del modelo tal cual aparece en Ollama."
                                : (models.find(m => m.name === selectedLlmModel)
                                    ? `${selectedLlmModel} — ${models.find(m => m.name === selectedLlmModel)!.is_multimodal ? 'Multimodal (soporta imágenes)' : 'Solo texto'}`
                                    : "Selecciona un modelo de la lista o escribe uno manualmente.")
                            }
                        </p>
                    </div>

                    {isCustomModel && (
                        <div className="flex gap-2">
                            <input
                                type="text"
                                value={customModelName}
                                onChange={(e) => {
                                    setCustomModelName(e.target.value);
                                    setSelectedLlmModel(e.target.value);
                                }}
                                placeholder="ej: llama3:70b"
                                className="px-4 py-2 bg-slate-950 border border-emerald-500/30 rounded-xl text-white text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none min-w-[150px]"
                            />
                        </div>
                    )}
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
