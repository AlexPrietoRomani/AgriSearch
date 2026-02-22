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
    const [newProject, setNewProject] = useState({ name: "", description: "", agri_area: "general", language: "es" });
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
            await createProject(newProject);
            setShowCreate(false);
            setNewProject({ name: "", description: "", agri_area: "general", language: "es" });
            await loadProjects();
        } catch (e) {
            console.error("Failed to create project:", e);
        } finally {
            setCreating(false);
        }
    }

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
            {/* Header */}
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-white">Mis Proyectos de Revisión</h1>
                    <p className="text-slate-400 mt-1">Gestiona tus revisiones sistemáticas agrícolas</p>
                </div>
                <button
                    onClick={() => setShowCreate(true)}
                    className="px-5 py-2.5 bg-gradient-to-r from-emerald-500 to-green-600 text-white font-semibold rounded-xl shadow-lg shadow-emerald-500/25 hover:shadow-emerald-500/50 hover:scale-105 transition-all duration-200"
                >
                    + Nuevo Proyecto
                </button>
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

                        <div className="grid grid-cols-2 gap-3 mb-4">
                            <label className="block">
                                <span className="text-sm text-slate-400 font-medium">Área Agrícola</span>
                                <select
                                    value={newProject.agri_area}
                                    onChange={(e) => setNewProject({ ...newProject, agri_area: e.target.value })}
                                    className="mt-1 w-full px-4 py-2.5 bg-slate-900 border border-slate-600 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all"
                                >
                                    {AGRI_AREAS.map((a) => (
                                        <option key={a.value} value={a.value}>{a.label}</option>
                                    ))}
                                </select>
                            </label>
                            <label className="block">
                                <span className="text-sm text-slate-400 font-medium">Idioma</span>
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
                            className="group block p-5 bg-slate-800/50 border border-slate-700/50 rounded-2xl hover:border-emerald-500/40 hover:bg-slate-800/80 hover:shadow-lg hover:shadow-emerald-500/5 transition-all duration-300"
                        >
                            <div className="flex items-start justify-between mb-3">
                                <h3 className="text-lg font-semibold text-white group-hover:text-emerald-300 transition-colors line-clamp-2">
                                    {p.name}
                                </h3>
                                <button
                                    onClick={(e) => { e.preventDefault(); e.stopPropagation(); handleDelete(p.id, p.name); }}
                                    className="text-slate-600 hover:text-red-400 transition-colors p-1"
                                    title="Eliminar proyecto"
                                >
                                    ✕
                                </button>
                            </div>
                            {p.description && <p className="text-sm text-slate-400 mb-4 line-clamp-2">{p.description}</p>}
                            <div className="flex items-center gap-3 text-xs text-slate-500">
                                <span className="px-2 py-1 rounded-lg bg-emerald-500/10 text-emerald-400 font-medium">
                                    {AGRI_AREAS.find((a) => a.value === p.agri_area)?.label || p.agri_area}
                                </span>
                                <span>📄 {p.article_count} artículos</span>
                            </div>
                        </a>
                    ))}
                </div>
            )}
        </div>
    );
}
