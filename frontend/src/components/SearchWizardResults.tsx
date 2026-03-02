import React, { useState } from "react";
import { uploadPdf, type Article, type SearchResults, type DownloadProgress } from "../lib/api";
import 'katex/dist/katex.min.css';
import Latex from 'react-latex-next';

interface Props {
    searchResults: SearchResults | null;
    articles: Article[];
    loading: boolean;
    downloadProgress: DownloadProgress | null;
    projectId: string;
    handleDownload: () => void;
    openProjectFolder: (id: string) => Promise<{ status: string; path: string }>;
    sourceColor: (db: string) => string;
    statusBadge: (status: string) => string;
    onArticleUpdated: (updatedArticle: Article) => void;
}

export default function SearchWizardResults({
    searchResults,
    articles,
    loading,
    downloadProgress,
    projectId,
    handleDownload,
    openProjectFolder,
    sourceColor,
    statusBadge,
    onArticleUpdated
}: Props) {
    const [sortField, setSortField] = useState<keyof Article>("authors");
    const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");
    const [expandedAbstract, setExpandedAbstract] = useState<string | null>(null);
    const [uploadingId, setUploadingId] = useState<string | null>(null);
    const [showQueries, setShowQueries] = useState(false);

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>, articleId: string) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setUploadingId(articleId);
        try {
            const updated = await uploadPdf(articleId, file);
            onArticleUpdated(updated);
            alert("PDF subido y vinculado con éxito");
        } catch (error: any) {
            alert(error.message || "Error al subir el archivo");
        } finally {
            setUploadingId(null);
            // reset file input
            e.target.value = "";
        }
    };

    const sortedArticles = [...articles].sort((a, b) => {
        let valA = a[sortField];
        let valB = b[sortField];

        if (typeof valA === "string") valA = valA.toLowerCase();
        if (typeof valB === "string") valB = valB.toLowerCase();

        if (valA === valB) return 0;
        if (valA === undefined || valA === null) return 1;
        if (valB === undefined || valB === null) return -1;

        const comparison = valA < valB ? -1 : 1;
        return sortDirection === "asc" ? comparison : -comparison;
    });

    const handleSort = (field: keyof Article) => {
        if (sortField === field) {
            setSortDirection(sortDirection === "asc" ? "desc" : "asc");
        } else {
            setSortField(field);
            setSortDirection("asc");
        }
    };

    const formatAuthors = (authorsStr: string | null | undefined) => {
        if (!authorsStr) return "Desconocido";
        const authorsList = authorsStr.split(",").map(a => a.trim()).filter(a => a);
        if (authorsList.length <= 2) return authorsList.join(", ");
        return `${authorsList[0]}, ${authorsList[1]} et al.`;
    };

    const getFilename = (path: string | null) => {
        if (!path) return "—";
        const parts = path.split(/[/\\]/);
        return parts[parts.length - 1];
    };

    if (!searchResults) return null;

    return (
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
                        <div className="text-2xl font-bold text-slate-200">{count as React.ReactNode}</div>
                        <div className="text-xs text-slate-400 mt-1">{source}</div>
                    </div>
                ))}
            </div>

            {/* Queries Debug Section */}
            {(searchResults.prompt_used || (searchResults.adapted_queries && Object.keys(searchResults.adapted_queries).length > 0)) && (
                <div className="mb-6 bg-slate-900/50 border border-slate-700/50 rounded-xl overflow-hidden">
                    <button
                        onClick={() => setShowQueries(!showQueries)}
                        className="w-full px-5 py-3 flex items-center justify-between text-slate-300 hover:text-emerald-400 hover:bg-slate-800/50 transition-colors"
                    >
                        <div className="flex items-center gap-2 font-semibold">
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                            </svg>
                            Ver Detalles de la Consulta (Prompt y Queries API)
                        </div>
                        <svg className={`w-5 h-5 transition-transform duration-300 ${showQueries ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                    </button>

                    {showQueries && (
                        <div className="px-5 pb-5 pt-2 border-t border-slate-700/50">
                            {searchResults.prompt_used && (
                                <div className="mb-4">
                                    <h4 className="text-xs font-bold text-emerald-500 uppercase tracking-widest mb-2">Prompt de Usuario</h4>
                                    <div className="p-3 bg-slate-950 rounded-lg text-sm text-slate-300 border border-slate-800 font-mono">
                                        {searchResults.prompt_used}
                                    </div>
                                </div>
                            )}

                            {searchResults.adapted_queries && Object.keys(searchResults.adapted_queries).length > 0 && (
                                <div>
                                    <h4 className="text-xs font-bold text-indigo-500 uppercase tracking-widest mb-2">Queries Adaptadas Transmitidas (Por Base de Datos)</h4>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                        {Object.entries(searchResults.adapted_queries).map(([db, query]) => (
                                            <div key={db} className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                                                <div className="text-[10px] font-bold text-slate-500 uppercase mb-1">{db}</div>
                                                <div className="text-xs text-slate-300 font-mono break-all">{query}</div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}

            {/* Download Progress */}
            {downloadProgress && (
                <div className="mb-6 p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl">
                    <div className="flex items-center gap-6 text-sm flex-wrap">
                        <span className="text-emerald-400 font-medium">✅ {downloadProgress.downloaded} descargados</span>
                        <span className="text-red-400">❌ {downloadProgress.failed} fallidos</span>
                        <span className="text-yellow-400">🔒 {downloadProgress.paywall} paywall</span>
                        {downloadProgress.not_found !== undefined && (
                            <span className="text-slate-400">ℹ️ {downloadProgress.not_found} sin enlace abierto</span>
                        )}
                    </div>
                </div>
            )}

            {/* Actions */}
            <div className="flex flex-wrap gap-3 mb-6">
                <a
                    href={`/project?id=${projectId}`}
                    className="px-4 py-2 text-slate-400 hover:text-white border border-slate-700 rounded-xl transition-colors"
                >
                    ← Volver
                </a>
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
                <button
                    onClick={async () => {
                        try {
                            await openProjectFolder(projectId);
                        } catch (e) {
                            console.error(e);
                            alert("No se pudo abrir la carpeta o aún no existe.");
                        }
                    }}
                    className="px-5 py-2 bg-slate-800 text-emerald-400 font-medium rounded-xl border border-emerald-500/30 hover:bg-slate-700 hover:text-emerald-300 transition-all flex items-center gap-2 ml-auto"
                >
                    📂 Abrir Carpeta Local
                </button>
            </div>

            {/* Articles Table */}
            <div className="border border-slate-700/50 rounded-2xl overflow-hidden mt-6 overflow-x-auto bg-slate-900/40 backdrop-blur-xl">
                <table className="w-full text-sm">
                    <thead className="bg-slate-800/80 border-b border-slate-700/50">
                        <tr>
                            <th
                                className="text-left px-6 py-4 text-slate-400 font-semibold uppercase tracking-wider cursor-pointer hover:text-emerald-400 transition-colors"
                                onClick={() => handleSort("title")}
                            >
                                Título {sortField === "title" && (sortDirection === "asc" ? "↑" : "↓")}
                            </th>
                            <th
                                className="text-left px-4 py-4 text-slate-400 font-semibold uppercase tracking-wider cursor-pointer hover:text-emerald-400 transition-colors max-w-[200px]"
                                onClick={() => handleSort("authors")}
                            >
                                Autor {sortField === "authors" && (sortDirection === "asc" ? "↑" : "↓")}
                            </th>
                            <th
                                className="text-left px-4 py-4 text-slate-400 font-semibold uppercase tracking-wider w-20 cursor-pointer hover:text-emerald-400 transition-colors"
                                onClick={() => handleSort("year")}
                            >
                                Año {sortField === "year" && (sortDirection === "asc" ? "↑" : "↓")}
                            </th>
                            <th
                                className="text-left px-4 py-4 text-slate-400 font-semibold uppercase tracking-wider w-32 cursor-pointer hover:text-emerald-400 transition-colors"
                                onClick={() => handleSort("source_database")}
                            >
                                Fuente {sortField === "source_database" && (sortDirection === "asc" ? "↑" : "↓")}
                            </th>
                            <th
                                className="text-left px-4 py-4 text-slate-400 font-semibold uppercase tracking-wider w-32 cursor-pointer hover:text-emerald-400 transition-colors"
                                onClick={() => handleSort("download_status")}
                            >
                                Estado {sortField === "download_status" && (sortDirection === "asc" ? "↑" : "↓")}
                            </th>
                            <th className="text-left px-4 py-4 text-slate-400 font-semibold uppercase tracking-wider w-40">
                                Archivo Local
                            </th>
                            <th className="text-right px-6 py-4 text-slate-400 font-semibold uppercase tracking-wider w-24">Link</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-700/30">
                        {sortedArticles.map((a) => (
                            <tr key={a.id} className="group hover:bg-slate-800/40 transition-all duration-200">
                                <td className="px-6 py-5">
                                    <div className="flex flex-col gap-1.5">
                                        <button
                                            onClick={() => setExpandedAbstract(expandedAbstract === a.id ? null : a.id)}
                                            className="text-left text-emerald-400 group-hover:text-emerald-300 transition-colors font-bold text-base leading-tight"
                                        >
                                            <Latex>{a.title}</Latex>
                                        </button>
                                        {a.journal && (
                                            <div className="flex items-center gap-2 text-slate-400 text-xs italic">
                                                <span className="text-indigo-400 font-medium">{a.journal}</span>
                                            </div>
                                        )}

                                        {expandedAbstract === a.id && (
                                            <div className="mt-4 p-5 bg-slate-900/60 border border-slate-700/50 rounded-2xl shadow-inner animate-in fade-in slide-in-from-top-2 duration-300">
                                                <div className="flex items-center justify-between mb-3 border-b border-slate-700/50 pb-2">
                                                    <span className="text-xs font-bold text-emerald-500 uppercase tracking-widest">Resumen / Abstract</span>
                                                    <button
                                                        className="text-slate-500 hover:text-white transition-colors"
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            navigator.clipboard.writeText(a.abstract || "");
                                                        }}
                                                        title="Copiar Resumen"
                                                    >
                                                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2" />
                                                        </svg>
                                                    </button>
                                                </div>
                                                <div className="text-sm text-slate-300 leading-relaxed font-normal">
                                                    {a.abstract ? <Latex>{a.abstract}</Latex> : "Resumen no disponible para este artículo."}
                                                </div>
                                                {a.keywords && (
                                                    <div className="mt-4 flex flex-wrap gap-2">
                                                        {a.keywords.split(",").map(kw => (
                                                            <span key={kw} className="px-2 py-0.5 bg-slate-800 text-slate-400 rounded-md text-[10px] uppercase font-bold border border-slate-700">
                                                                {kw.trim()}
                                                            </span>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                </td>
                                <td className="px-4 py-5 align-top max-w-[200px]">
                                    <div className="text-slate-300 font-medium" title={a.authors || "Desconocido"}>
                                        {formatAuthors(a.authors)}
                                    </div>
                                </td>
                                <td className="px-4 py-5 align-top">
                                    <span className="text-slate-300 font-mono">{a.year || "—"}</span>
                                </td>
                                <td className="px-4 py-5 align-top">
                                    <span className={`px-2.5 py-1 rounded-lg text-[10px] uppercase font-bold tracking-wider ${sourceColor(a.source_database)}`}>
                                        {a.source_database}
                                    </span>
                                </td>
                                <td className="px-4 py-5 align-top">
                                    <div className="flex flex-col gap-1.5">
                                        <span className={`px-2.5 py-1 rounded-lg text-[10px] uppercase font-bold tracking-wider text-center ${statusBadge(a.download_status)}`}>
                                            {a.download_status}
                                        </span>
                                    </div>
                                </td>
                                <td className="px-4 py-5 align-top max-w-[150px] truncate text-slate-400 text-xs italic" title={getFilename(a.local_pdf_path) ?? "—"}>
                                    {getFilename(a.local_pdf_path)}
                                </td>
                                <td className="px-6 py-5 align-top text-right">
                                    <div className="flex flex-col items-end gap-2">
                                        {a.doi || a.url ? (
                                            <a
                                                href={a.doi ? (a.doi.startsWith("http") ? a.doi : `https://doi.org/${a.doi}`) : (a.url || undefined)}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500 hover:text-white rounded-lg transition-all duration-200 text-xs font-bold border border-emerald-500/20"
                                            >
                                                {a.doi ? "DOI" : "WEB"}
                                                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                                </svg>
                                            </a>
                                        ) : (
                                            <span className="text-slate-600 text-xs">—</span>
                                        )}
                                        {a.download_status === "success" ? (
                                            <span className="text-[10px] text-emerald-500/60 font-medium whitespace-nowrap">Local PDF ✅</span>
                                        ) : (
                                            <div className="relative">
                                                <input
                                                    type="file"
                                                    accept=".pdf"
                                                    id={`upload-${a.id}`}
                                                    className="hidden"
                                                    onChange={(e) => handleFileUpload(e, a.id)}
                                                    disabled={uploadingId === a.id}
                                                />
                                                <label
                                                    htmlFor={`upload-${a.id}`}
                                                    className={`cursor-pointer flex items-center gap-1.5 px-3 py-1 bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-white rounded-lg transition-all duration-200 text-xs font-medium border border-slate-700 ${uploadingId === a.id ? 'opacity-50 cursor-wait' : ''}`}
                                                    title="Subir PDF manualmente"
                                                >
                                                    {uploadingId === a.id ? (
                                                        <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                                    ) : "⬆️ Subir PDF"}
                                                </label>
                                            </div>
                                        )}
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
