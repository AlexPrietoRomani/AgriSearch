import { useState, useEffect } from "react";
import { getProject, getProjectSearches } from "../lib/api";
import type { SearchQuery } from "../lib/api";

export default function ProjectDashboard() {
    const [projectId, setProjectId] = useState("");
    const [projectName, setProjectName] = useState("Cargando...");
    const [searches, setSearches] = useState<SearchQuery[]>([]);

    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        const id = params.get("id");
        if (!id) { window.location.href = "/"; return; }
        setProjectId(id);

        getProject(id).then(async (p) => {
            setProjectName(p.name);
            try {
                const projectSearches = await getProjectSearches(id);
                setSearches(projectSearches);
            } catch (e) {
                console.error("No historical searches loaded", e);
            }
        }).catch(() => window.location.href = "/");
    }, []);

    return (
        <div>
            {/* Breadcrumb */}
            <div className="flex items-center gap-2 text-sm text-slate-500 mb-6">
                <a href="/" className="hover:text-emerald-400 transition-colors">Proyectos</a>
                <span>/</span>
                <span className="text-emerald-400">{projectName}</span>
            </div>

            <div className="max-w-5xl">
                <div className="flex items-center justify-between mb-8">
                    <div>
                        <h1 className="text-3xl font-bold text-white mb-2">Búsquedas del Proyecto</h1>
                        <p className="text-slate-400">Selecciona una búsqueda anterior o inicia una nueva para extraer artículos.</p>
                    </div>
                    <a
                        href={`/search?id=${projectId}`}
                        className="px-5 py-2.5 bg-emerald-500 hover:bg-emerald-600 text-white font-medium rounded-xl shadow-lg shadow-emerald-500/25 transition-all flex items-center gap-2"
                    >
                        <span className="text-lg">+</span> Nueva Búsqueda
                    </a>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {searches.map((s, idx) => (
                        <a
                            key={s.id}
                            href={`/search?id=${projectId}&query_id=${s.id}`}
                            className="block p-6 bg-slate-800/80 border border-slate-700/50 hover:border-emerald-500/50 rounded-2xl cursor-pointer transition-all hover:-translate-y-1 group"
                        >
                            <div className="flex justify-between items-start mb-4">
                                <h3 className="text-lg font-bold text-white group-hover:text-emerald-400 transition-colors">
                                    Búsqueda {idx + 1}
                                </h3>
                                <span className="text-xs font-medium text-slate-500 px-2 py-1 bg-slate-800 rounded-md">
                                    {new Date(s.created_at).toLocaleDateString()}
                                </span>
                            </div>

                            <p className="text-sm text-slate-400 mb-6 line-clamp-3">
                                {s.raw_input || "Sin descripción proporcionada."}
                            </p>

                            <div className="flex items-center justify-between mt-auto">
                                <span className="text-xs font-semibold px-2.5 py-1 bg-emerald-500/10 text-emerald-400 rounded-lg">
                                    {s.total_results} Artículos
                                </span>
                                <span className="text-xs text-slate-500">
                                    {s.databases_used ? s.databases_used.split(',').length : 0} Fuentes
                                </span>
                            </div>
                        </a>
                    ))}

                    {searches.length === 0 && (
                        <div className="col-span-full text-center py-16 border border-dashed border-slate-700 rounded-2xl">
                            <h2 className="text-xl text-slate-300 font-medium mb-2">No tienes búsquedas</h2>
                            <p className="text-slate-500 mb-6">Realiza tu primera búsqueda sistemática para extraer y centralizar artículos de investigación.</p>
                            <a
                                href={`/search?id=${projectId}`}
                                className="inline-flex px-5 py-2.5 bg-emerald-500 hover:bg-emerald-600 text-white font-medium rounded-xl transition-all items-center gap-2"
                            >
                                Iniciar Búsqueda
                            </a>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
