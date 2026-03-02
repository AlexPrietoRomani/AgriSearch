/**
 * AgriSearch - Dashboard Component.
 *
 * Main page showing all research projects with create/delete capabilities.
 */

import { useState, useEffect } from "react";
import type { Project } from "../lib/api";
import { listProjects, createProject, deleteProject } from "../lib/api";

const AGRI_AREAS = [
    { value: "general", label: "General" },
    { value: "entomology", label: "Entomología" },
    { value: "phytopathology", label: "Fitopatología" },
    { value: "breeding", label: "Mejoramiento Genético" },
    { value: "biotechnology", label: "Biotecnología" },
    { value: "precision_agriculture", label: "Agricultura de Precisión" },
    { value: "soil_science", label: "Ciencias del Suelo" },
    { value: "agronomy", label: "Agronomía" },
    { value: "weed_science", label: "Malherbología" },
    { value: "other", label: "Otro" },
];

export default function Dashboard() {
    const [projects, setProjects] = useState<Project[]>([]);
    const [loading, setLoading] = useState(true);
    const [showCreate, setShowCreate] = useState(false);
    const [newProject, setNewProject] = useState({ name: "", description: "", language: "es" });
    const [selectedAreas, setSelectedAreas] = useState<string[]>(["general"]);
    const [customArea, setCustomArea] = useState("");
    const [creating, setCreating] = useState(false);

    useEffect(() => {
        loadProjects();
    }, []);

    async function loadProjects() {
        try {
            const data = await listProjects();
            setProjects(data.projects);
        } catch (e) {
            console.error("Failed to load projects:", e);
        } finally {
            setLoading(false);
        }
    }

    async function handleCreate() {
        if (!newProject.name.trim()) return;
        setCreating(true);
        try {
            // Combine selected areas and custom area
            let finalAreas = selectedAreas.filter(a => a !== "other").map(a =>
                AGRI_AREAS.find(ref => ref.value === a)?.label || a
            );
            if (selectedAreas.includes("other") && customArea.trim()) {
                finalAreas.push(customArea.trim());
            }

            const agriAreaStr = finalAreas.length > 0 ? finalAreas.join(", ") : "General";

            await createProject({
                ...newProject,
                agri_area: agriAreaStr
            });
            setShowCreate(false);
            setNewProject({ name: "", description: "", language: "es" });
            setSelectedAreas(["general"]);
            setCustomArea("");
            await loadProjects();
        } catch (e) {
            console.error("Failed to create project:", e);
        } finally {
            setCreating(false);
        }
    }

    const toggleArea = (val: string) => {
        if (selectedAreas.includes(val)) {
            setSelectedAreas(selectedAreas.filter(a => a !== val));
        } else {
            setSelectedAreas([...selectedAreas, val]);
        }
    };

    async function handleDelete(id: string, name: string) {
        if (!confirm(`¿Eliminar el proyecto "${name}" y todos sus datos?`)) return;
        try {
            await deleteProject(id);
            await loadProjects();
        } catch (e) {
            console.error("Failed to delete project:", e);
        }
    }

    return (
        <div>
            {/* Premium Hero / Info Section */}
            <div className="mb-10 p-10 rounded-[2rem] bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 border border-slate-700/50 shadow-[0_20px_50px_rgba(0,0,0,0.5)] relative overflow-hidden group">
                <div className="absolute top-0 right-0 w-1/2 h-full bg-emerald-500/5 skew-x-[-20deg] translate-x-32 group-hover:bg-emerald-500/10 transition-all duration-700 pointer-events-none" />

                <div className="relative z-10 grid lg:grid-cols-12 gap-12 items-center">
                    <div className="lg:col-span-7">
                        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px] font-bold uppercase tracking-[0.2em] mb-6">
                            <span className="relative flex h-2 w-2">
                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                            </span>
                            Research Assistant Pro
                        </div>

                        <h1 className="text-4xl md:text-6xl font-black text-white leading-[1.1] mb-6">
                            Ciencia de Datos <br />
                            <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-cyan-400">Para la Agricultura.</span>
                        </h1>

                        <p className="text-slate-400 text-lg leading-relaxed mb-8 max-w-2xl">
                            AgriSearch es su centro de comando para revisiones sistemáticas avanzadas.
                            Utilizamos LLMs de última generación para orquestar búsquedas complejas,
                            eliminar el sesgo de selección y automatizar el flujo de trabajo <span className="text-white font-medium underline underline-offset-4 decoration-emerald-500">PRISMA 2020</span>.
                        </p>

                        <div className="flex flex-wrap gap-4">
                            <button
                                onClick={() => setShowCreate(true)}
                                className="px-8 py-4 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-black rounded-2xl shadow-[0_0_30px_rgba(16,185,129,0.3)] hover:shadow-[0_0_50px_rgba(16,185,129,0.5)] hover:-translate-y-1 transition-all duration-300 flex items-center gap-3"
                            >
                                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M12 4v16m8-8H4"></path></svg>
                                NUEVO PROYECTO
                            </button>
                            <a
                                href="https://www.eshackathon.org/software/PRISMA2020.html"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="px-6 py-4 backdrop-blur-xl bg-white/5 border border-white/10 hover:bg-white/10 text-white font-semibold rounded-2xl transition-all flex items-center gap-3"
                            >
                                <svg className="w-5 h-5 text-emerald-400" fill="currentColor" viewBox="0 0 20 20"><path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z" /><path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" /></svg>
                                Software PRISMA 2020
                            </a>
                            <a
                                href="https://www.prisma-statement.org/prisma-2020"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="px-6 py-4 backdrop-blur-xl bg-white/5 border border-white/10 hover:bg-white/10 text-white font-semibold rounded-2xl transition-all flex items-center gap-3"
                            >
                                <svg className="w-5 h-5 text-emerald-400" fill="currentColor" viewBox="0 0 20 20"><path d="M9 2a2 2 0 00-2 2v8a2 2 0 002 2h6a2 2 0 002-2V6.414A2 2 0 0016.414 5L14 2.586A2 2 0 0012.586 2H9z" /><path d="M3 8a2 2 0 012-2v10h8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z" /></svg>
                                Archivos PRISMA 2020
                            </a>
                        </div>
                    </div>

                    <div className="lg:col-span-5 grid grid-cols-2 gap-4">
                        {[
                            { label: "Búsqueda Multi-Fuente", desc: "API OpenAlex, ArXiv y Semantic Scholar.", icon: "🔍", color: "blue" },
                            { label: "Deduplicación IA", desc: "Algoritmos de similitud avanzados.", icon: "⚡", color: "emerald" },
                            { label: "RAG Local", desc: "Búsqueda vectorial en tus PDFs.", icon: "🧠", color: "purple" },
                            { label: "Exportación PRO", desc: "BibTeX y CSV listos para publicar.", icon: "📊", color: "amber" }
                        ].map((stat, i) => (
                            <div key={i} className="p-5 bg-slate-950/40 border border-slate-700/30 rounded-2xl hover:border-white/20 transition-all group/item">
                                <div className="text-3xl mb-3 group-hover/item:scale-125 transition-transform duration-300">{stat.icon}</div>
                                <div className="text-white font-bold text-sm mb-1">{stat.label}</div>
                                <div className="text-slate-500 text-xs leading-snug">{stat.desc}</div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Workflow Steps */}
            <div className="mb-12">
                <h3 className="text-slate-400 text-xs font-bold uppercase tracking-[0.3em] mb-8 text-center">Protocolo de Trabajo Sistematizado</h3>
                <div className="flex flex-col md:flex-row justify-between items-start gap-8 relative">
                    <div className="absolute top-10 left-0 w-full h-px bg-slate-800 hidden md:block" />
                    {[
                        { step: "Identificación", text: "Extracción masiva de registros candidatos desde APIs científicas." },
                        { step: "Cribado", text: "Remoción de duplicados y filtrado por metadatos/abstracts." },
                        { step: "Elegibilidad", text: "Evaluación de textos completos y descarga automatizada." },
                        { step: "Inclusión", text: "Indexación en base de datos vectorial para asistencia LLM." }
                    ].map((s, i) => (
                        <div key={i} className="flex-1 relative z-10 group/step">
                            <div className="w-10 h-10 rounded-full bg-slate-800 border-4 border-slate-950 text-emerald-400 flex items-center justify-center font-black mb-4 group-hover/step:bg-emerald-500 group-hover/step:text-slate-950 transition-colors duration-300">
                                {i + 1}
                            </div>
                            <h4 className="text-white font-bold mb-2">{s.step}</h4>
                            <p className="text-slate-500 text-sm leading-relaxed">{s.text}</p>
                        </div>
                    ))}
                </div>
            </div>

            {/* Project List Header */}
            <div className="flex items-center justify-between mb-8 pb-4 border-b border-slate-800">
                <div>
                    <h2 className="text-2xl font-bold text-white flex items-center gap-3">
                        <span className="w-2 h-8 bg-emerald-500 rounded-full" />
                        Biblioteca de Proyectos
                    </h2>
                    <p className="text-slate-400 mt-1 text-sm">Gestiona tus investigaciones activas.</p>
                </div>
            </div>

            {/* Create Project Modal */}
            {showCreate && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={() => setShowCreate(false)}>
                    <div
                        className="bg-slate-800 border border-slate-700 rounded-2xl p-6 w-full max-w-lg shadow-2xl"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <h2 className="text-xl font-bold text-white mb-4">Crear Nuevo Proyecto</h2>

                        <label className="block mb-3">
                            <span className="text-sm text-slate-400 font-medium">Nombre del Proyecto *</span>
                            <input
                                type="text"
                                value={newProject.name}
                                onChange={(e) => setNewProject({ ...newProject, name: e.target.value })}
                                placeholder="Ej: Control biológico en soja"
                                className="mt-1 w-full px-4 py-2.5 bg-slate-900 border border-slate-600 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
                            />
                        </label>

                        <label className="block mb-3">
                            <span className="text-sm text-slate-400 font-medium">Descripción</span>
                            <textarea
                                value={newProject.description}
                                onChange={(e) => setNewProject({ ...newProject, description: e.target.value })}
                                placeholder="Descripción breve del alcance de la revisión..."
                                rows={3}
                                className="mt-1 w-full px-4 py-2.5 bg-slate-900 border border-slate-600 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all resize-none"
                            />
                        </label>

                        <label className="block mb-4">
                            <span className="text-sm text-slate-400 font-medium mb-2 block">Áreas Agrícolas (Puedes elegir varias)</span>
                            <div className="flex flex-wrap gap-2 mb-2">
                                {AGRI_AREAS.map((a) => (
                                    <button
                                        key={a.value}
                                        type="button"
                                        onClick={() => toggleArea(a.value)}
                                        className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all border ${selectedAreas.includes(a.value)
                                            ? "bg-emerald-500 border-emerald-500 text-slate-950 shadow-lg shadow-emerald-500/20"
                                            : "bg-slate-900 border-slate-700 text-slate-400 hover:border-slate-500"
                                            }`}
                                    >
                                        {a.label}
                                    </button>
                                ))}
                            </div>
                            {selectedAreas.includes("other") && (
                                <input
                                    type="text"
                                    value={customArea}
                                    onChange={(e) => setCustomArea(e.target.value)}
                                    placeholder="Especifica tu área..."
                                    className="mt-2 w-full px-4 py-2 bg-slate-900 border border-slate-600 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all text-sm"
                                />
                            )}
                        </label>

                        <div className="grid grid-cols-1 gap-4 mb-6">
                            <label className="block">
                                <span className="text-sm text-slate-400 font-medium">Idioma Principal</span>
                                <select
                                    value={newProject.language}
                                    onChange={(e) => setNewProject({ ...newProject, language: e.target.value })}
                                    className="mt-1 w-full px-4 py-2.5 bg-slate-900 border border-slate-600 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all"
                                >
                                    <option value="es">Español</option>
                                    <option value="en">English</option>
                                </select>
                            </label>
                        </div>

                        <div className="flex justify-end gap-3">
                            <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-slate-400 hover:text-white transition-colors">
                                Cancelar
                            </button>
                            <button
                                onClick={handleCreate}
                                disabled={creating || !newProject.name.trim()}
                                className="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-all"
                            >
                                {creating ? "Creando..." : "Crear Proyecto"}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Project Grid */}
            {loading ? (
                <div className="flex items-center justify-center py-20">
                    <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
                </div>
            ) : projects.length === 0 ? (
                <div className="text-center py-20">
                    <div className="text-6xl mb-4">🌾</div>
                    <h2 className="text-xl text-slate-300 font-medium mb-2">No hay proyectos aún</h2>
                    <p className="text-slate-500">Crea tu primer proyecto de revisión sistemática para comenzar.</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                    {projects.map((p) => (
                        <a
                            key={p.id}
                            href={`/project?id=${p.id}`}
                            className="group flex flex-col p-5 bg-slate-800/60 border border-slate-700/60 rounded-2xl hover:border-emerald-500/50 hover:bg-slate-800 hover:shadow-xl hover:shadow-emerald-500/10 transition-all duration-300 relative overflow-hidden"
                        >
                            <div className="absolute top-0 left-0 w-2 h-full bg-emerald-500/20 group-hover:bg-emerald-500/50 transition-colors" />
                            <div className="flex items-start justify-between mb-2 pl-2">
                                <h3 className="text-xl font-bold text-white group-hover:text-emerald-400 transition-colors pr-6">
                                    {p.name}
                                </h3>
                                <button
                                    onClick={(e) => { e.preventDefault(); e.stopPropagation(); handleDelete(p.id, p.name); }}
                                    className="text-slate-500 hover:text-red-400 focus:outline-none transition-colors p-1"
                                    title="Eliminar proyecto"
                                >
                                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                    </svg>
                                </button>
                            </div>
                            {p.description ? (
                                <p className="text-slate-400 mb-4 pl-2 flex-grow text-sm">
                                    {p.description}
                                </p>
                            ) : (
                                <p className="text-slate-600 italic mb-4 pl-2 flex-grow text-sm">
                                    Sin descripción...
                                </p>
                            )}
                            <div className="flex items-center gap-3 text-xs font-semibold pl-2 mt-auto pt-4 border-t border-slate-700/50">
                                <span className="px-2.5 py-1 rounded-md bg-emerald-500/10 text-emerald-400 tracking-wide">
                                    {AGRI_AREAS.find((a) => a.value === p.agri_area)?.label || p.agri_area}
                                </span>
                                <div className="flex items-center gap-3 text-slate-400">
                                    <span className="flex items-center gap-1">
                                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                        </svg>
                                        {p.article_count} artículos
                                    </span>
                                    {p.reviewed_count > 0 && (
                                        <span className="flex items-center gap-1 text-emerald-400">
                                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                            </svg>
                                            {p.reviewed_count} revisados
                                        </span>
                                    )}
                                </div>
                            </div>
                        </a>
                    ))}
                </div>
            )}
        </div>
    );
}
