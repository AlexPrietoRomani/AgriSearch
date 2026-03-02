import { useState, useEffect } from "react";
import {
    getProject, getProjectSearches, updateProject, deleteSearch, listProjectScreeningSessions, deleteScreeningSession,
    type SearchQuery, type Project, type ScreeningSession, checkScreeningEligibility
} from "../lib/api";

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

export default function ProjectDashboard() {
    const [projectId, setProjectId] = useState("");
    const [project, setProject] = useState<Project | null>(null);
    const [searches, setSearches] = useState<SearchQuery[]>([]);
    const [screenings, setScreenings] = useState<ScreeningSession[]>([]);
    const [isEditing, setIsEditing] = useState(false);
    const [editData, setEditData] = useState({ name: "", description: "", agri_area: "", language: "es", llm_model: "" });
    const [selectedAreas, setSelectedAreas] = useState<string[]>([]);
    const [customArea, setCustomArea] = useState("");
    const [saving, setSaving] = useState(false);
    const [searchToDelete, setSearchToDelete] = useState<SearchQuery | null>(null);
    const [isDeletingSearch, setIsDeletingSearch] = useState(false);
    const [screeningToDelete, setScreeningToDelete] = useState<ScreeningSession | null>(null);
    const [isDeletingScreening, setIsDeletingScreening] = useState(false);
    const [isCheckingEligibility, setIsCheckingEligibility] = useState(false);
    const [notification, setNotification] = useState<{ message: string, type: 'success' | 'error' } | null>(null);

    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        const id = params.get("id");
        if (!id) { window.location.href = "/"; return; }
        setProjectId(id);

        loadProject(id);
    }, []);

    const showNotification = (message: string, type: 'success' | 'error' = 'success') => {
        setNotification({ message, type });
        setTimeout(() => setNotification(null), 4000);
    };

    async function loadProject(id: string) {
        try {
            const p = await getProject(id);
            setProject(p);
            setEditData({
                name: p.name,
                description: p.description || "",
                agri_area: p.agri_area,
                language: p.language,
                llm_model: p.llm_model || "llama3.1:8b"
            });
            // Try to map back areas for editing if possible, or just set as custom if not in list
            // For now, let's keep it simple

            const projectSearches = await getProjectSearches(id);
            setSearches(projectSearches);

            try {
                const projectScreenings = await listProjectScreeningSessions(id);
                setScreenings(projectScreenings);
            } catch (e) {
                console.error("Failed to load screenings", e);
            }
        } catch (e) {
            console.error("Failed to load project", e);
            window.location.href = "/";
        }
    }

    const handleSave = async () => {
        setSaving(true);
        try {
            const finalAreas = selectedAreas.filter(a => a !== "other").map(a =>
                AGRI_AREAS.find(ref => ref.value === a)?.label || a
            );
            if (selectedAreas.includes("other") && customArea.trim()) {
                finalAreas.push(customArea.trim());
            }
            const agriAreaStr = finalAreas.length > 0 ? finalAreas.join(", ") : "General";

            await updateProject(projectId, {
                ...editData,
                agri_area: agriAreaStr
            });
            setIsEditing(false);
            showNotification("Proyecto actualizado correctamente");
            await loadProject(projectId);
        } catch (e: any) {
            console.error("Failed to save project", e);
            showNotification(e.message || "Error al guardar el proyecto", 'error');
        } finally {
            setSaving(false);
        }
    };

    const confirmDeleteSearch = async () => {
        if (!searchToDelete) return;
        setIsDeletingSearch(true);
        try {
            await deleteSearch(projectId, searchToDelete.id);
            setSearches(searches.filter(s => s.id !== searchToDelete.id));
            showNotification("Búsqueda eliminada correctamente");
        } catch (e: any) {
            console.error("Failed to delete search", e);
            showNotification(e.message || "Error al eliminar la búsqueda", 'error');
        } finally {
            setIsDeletingSearch(false);
            setSearchToDelete(null);
        }
    };

    const confirmDeleteScreening = async () => {
        if (!screeningToDelete) return;
        setIsDeletingScreening(true);
        try {
            await deleteScreeningSession(screeningToDelete.id);
            setScreenings(screenings.filter(s => s.id !== screeningToDelete.id));
            showNotification("Revisión eliminada correctamente");
        } catch (e: any) {
            console.error("Failed to delete screening", e);
            showNotification(e.message || "Error al eliminar la revisión", 'error');
        } finally {
            setIsDeletingScreening(false);
            setScreeningToDelete(null);
        }
    };

    const toggleArea = (val: string) => {
        if (selectedAreas.includes(val)) {
            setSelectedAreas(selectedAreas.filter(a => a !== val));
        } else {
            setSelectedAreas([...selectedAreas, val]);
        }
    };

    const startEditing = () => {
        if (!project) return;
        setEditData({
            name: project.name,
            description: project.description || "",
            agri_area: project.agri_area,
            language: project.language,
            llm_model: project.llm_model || "llama3.1:8b"
        });

        // Parse current agri_area back to selectedAreas / customArea
        const currentAreas = project.agri_area.split(", ").map(a => a.trim());
        const mapped = currentAreas.filter(a => AGRI_AREAS.some(ref => ref.label === a)).map(a => AGRI_AREAS.find(ref => ref.label === a)!.value);
        const others = currentAreas.filter(a => !AGRI_AREAS.some(ref => ref.label === a));

        setSelectedAreas(others.length > 0 ? [...mapped, "other"] : mapped);
        setCustomArea(others.join(", "));
        setIsEditing(true);
    };

    const handleNewScreening = async () => {
        setIsCheckingEligibility(true);
        try {
            const eligibility = await checkScreeningEligibility(projectId);
            if (eligibility.total_downloaded === 0) {
                alert(`Debes realizar al menos una búsqueda y tener artículos descargados con éxito antes de iniciar una revisión.`);
                setIsCheckingEligibility(false);
                return;
            }
            if (eligibility.eligible_articles === 0) {
                alert(`Todos tus ${eligibility.total_downloaded} artículos descargados ya fueron asignados en las revisiones: ${eligibility.screening_names.join(', ')}.\n\nHaz nuevas búsquedas para extraer más artículos antes de crear otra revisión.`);
                setIsCheckingEligibility(false);
                return;
            }

            // Allow creating new screening
            window.location.href = `/screening?id=${projectId}&new=true`;
        } catch (e: any) {
            showNotification(e.message || "Error al verificar artículos disponibles", 'error');
        } finally {
            setIsCheckingEligibility(false);
        }
    };

    if (!project) return (
        <div className="flex items-center justify-center h-40">
            <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
        </div>
    );

    return (
        <div className="relative">
            {/* Notification Toast */}
            {notification && (
                <div className={`fixed top-8 right-8 z-[100] flex items-center gap-3 px-6 py-4 rounded-2xl shadow-2xl border backdrop-blur-xl animate-in fade-in slide-in-from-top-4 duration-300 ${notification.type === 'success'
                    ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                    : 'bg-red-500/10 border-red-500/20 text-red-400'
                    }`}>
                    {notification.type === 'success' ? (
                        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                    ) : (
                        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                    )}
                    <span className="font-bold">{notification.message}</span>
                </div>
            )}

            {/* Delete Search Modal */}
            {searchToDelete && (
                <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
                    <div className="bg-slate-900 border border-slate-700 p-8 rounded-3xl max-w-lg w-full shadow-2xl animate-in zoom-in-95 duration-200">
                        <div className="flex items-center gap-4 text-rose-500 mb-4">
                            <div className="p-3 bg-rose-500/10 rounded-full">
                                <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                            </div>
                            <h3 className="text-2xl font-black">Eliminar Búsqueda</h3>
                        </div>
                        <p className="text-slate-300 mb-6 leading-relaxed">
                            ¿Estás seguro que deseas eliminar esta búsqueda de <strong>{searchToDelete.total_results}</strong> artículos?
                            Esta acción <strong>borrará todos los PDFs locales</strong> descargados asociados a  esta búsqueda y no podrá restablecerse.
                        </p>
                        <div className="flex gap-4">
                            <button
                                onClick={confirmDeleteSearch}
                                disabled={isDeletingSearch}
                                className="flex-1 px-6 py-3 bg-rose-500 hover:bg-rose-600 text-white font-bold rounded-xl transition-colors disabled:opacity-50 flex items-center justify-center"
                            >
                                {isDeletingSearch ? (
                                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                ) : "Sí, Eliminar Definitivamente"}
                            </button>
                            <button
                                onClick={() => setSearchToDelete(null)}
                                disabled={isDeletingSearch}
                                className="px-6 py-3 bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium rounded-xl transition-colors disabled:opacity-50"
                            >
                                Cancelar
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Delete Screening Modal */}
            {screeningToDelete && (
                <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
                    <div className="bg-slate-900 border border-slate-700 p-8 rounded-3xl max-w-lg w-full shadow-2xl animate-in zoom-in-95 duration-200">
                        <div className="flex items-center gap-4 text-rose-500 mb-4">
                            <div className="p-3 bg-rose-500/10 rounded-full">
                                <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                            </div>
                            <h3 className="text-2xl font-black">Eliminar Revisión</h3>
                        </div>
                        <p className="text-slate-300 mb-6 leading-relaxed">
                            ¿Estás seguro que deseas eliminar la revisión <strong>{screeningToDelete.name || 'Sin Nombre'}</strong>?
                            Se borrarán todas las justificaciones y decisiones de este cribado. (Los artículos extraídos no se borrarán de las búsquedas base).
                        </p>
                        <div className="flex gap-4">
                            <button
                                onClick={confirmDeleteScreening}
                                disabled={isDeletingScreening}
                                className="flex-1 px-6 py-3 bg-rose-500 hover:bg-rose-600 text-white font-bold rounded-xl transition-colors disabled:opacity-50 flex items-center justify-center"
                            >
                                {isDeletingScreening ? (
                                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                ) : "Sí, Eliminar Definitivamente"}
                            </button>
                            <button
                                onClick={() => setScreeningToDelete(null)}
                                disabled={isDeletingScreening}
                                className="px-6 py-3 bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium rounded-xl transition-colors disabled:opacity-50"
                            >
                                Cancelar
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Breadcrumb */}
            <div className="flex items-center gap-2 text-sm text-slate-500 mb-6">
                <a href="/" className="hover:text-emerald-400 transition-colors">Proyectos</a>
                <span>/</span>
                <span className="text-emerald-400">{project.name}</span>
            </div>

            <div className="max-w-5xl">
                {!isEditing ? (
                    <div className="flex items-start justify-between mb-8 bg-slate-900/40 p-8 rounded-3xl border border-slate-800 shadow-xl">
                        <div className="flex-grow">
                            <div className="flex items-center gap-4 mb-4">
                                <h1 className="text-3xl font-black text-white">{project.name}</h1>
                                <button
                                    onClick={startEditing}
                                    className="p-2 text-slate-500 hover:text-emerald-400 transition-colors"
                                    title="Editar proyecto"
                                >
                                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                    </svg>
                                </button>
                            </div>

                            <p className="text-slate-400 whitespace-pre-wrap mb-6 leading-relaxed">
                                {project.description || <span className="italic text-slate-600">Sin descripción proporcionada.</span>}
                            </p>

                            <div className="flex flex-wrap gap-4 mt-6 pt-6 border-t border-slate-800">
                                <div className="flex flex-col gap-1">
                                    <span className="text-[10px] uppercase tracking-[0.2em] text-slate-500 font-bold">Áreas Agrícolas</span>
                                    <div className="flex flex-wrap gap-2 mt-1">
                                        {project.agri_area.split(", ").map(area => (
                                            <span key={area} className="px-3 py-1 bg-emerald-500/10 text-emerald-400 rounded-full text-xs font-semibold border border-emerald-500/20">
                                                {area}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                                <div className="flex flex-col gap-1 ml-auto">
                                    <span className="text-[10px] uppercase tracking-[0.2em] text-slate-500 font-bold">Idioma</span>
                                    <span className="text-white font-medium flex items-center gap-2 mt-1">
                                        <span className="w-5 h-5 rounded bg-slate-800 flex items-center justify-center text-[10px]">
                                            {project.language.toUpperCase()}
                                        </span>
                                        {project.language === "es" ? "Español" : "English"}
                                    </span>
                                </div>
                            </div>
                        </div>

                        <div className="flex flex-col gap-3 flex-shrink-0 ml-8">
                            <a
                                href={`/search?id=${projectId}`}
                                className="px-6 py-4 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-black rounded-2xl shadow-lg shadow-emerald-500/20 transition-all flex items-center gap-3 hover:-translate-y-1"
                            >
                                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                                </svg>
                                BÚSQUEDA IA
                            </a>
                            {searches.length > 0 && (
                                <button
                                    onClick={handleNewScreening}
                                    disabled={isCheckingEligibility}
                                    className="px-6 py-4 bg-purple-500 hover:bg-purple-400 text-white font-black rounded-2xl shadow-lg shadow-purple-500/20 transition-all flex items-center justify-center gap-3 hover:-translate-y-1 disabled:opacity-50"
                                >
                                    {isCheckingEligibility ? (
                                        <div className="w-6 h-6 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                    ) : (
                                        <>
                                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                                            </svg>
                                            REVISIONES
                                        </>
                                    )}
                                </button>
                            )}
                        </div>
                    </div>
                ) : (
                    <div className="mb-8 bg-slate-900/60 p-8 rounded-3xl border border-emerald-500/30 shadow-2xl shadow-emerald-500/5">
                        <h2 className="text-xl font-black text-white mb-6 flex items-center gap-2">
                            <svg className="w-6 h-6 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                            Editar Proyecto
                        </h2>

                        <div className="grid gap-6">
                            <label className="block">
                                <span className="text-xs font-bold uppercase tracking-widest text-slate-500 mb-2 block">Nombre del Proyecto</span>
                                <input
                                    type="text"
                                    value={editData.name}
                                    onChange={(e) => setEditData({ ...editData, name: e.target.value })}
                                    className="w-full px-4 py-3 bg-slate-950 border border-slate-800 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all"
                                />
                            </label>

                            <label className="block">
                                <span className="text-xs font-bold uppercase tracking-widest text-slate-500 mb-2 block">Descripción Detallada</span>
                                <textarea
                                    value={editData.description}
                                    onChange={(e) => setEditData({ ...editData, description: e.target.value })}
                                    rows={4}
                                    className="w-full px-4 py-3 bg-slate-950 border border-slate-800 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all resize-none"
                                />
                            </label>

                            <div>
                                <span className="text-xs font-bold uppercase tracking-widest text-slate-500 mb-3 block">Áreas de Enfoque</span>
                                <div className="flex flex-wrap gap-2 mb-3">
                                    {AGRI_AREAS.map((a) => (
                                        <button
                                            key={a.value}
                                            onClick={() => toggleArea(a.value)}
                                            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all border ${selectedAreas.includes(a.value)
                                                ? "bg-emerald-500 border-emerald-500 text-slate-950"
                                                : "bg-slate-950 border-slate-800 text-slate-500 hover:border-slate-600"
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
                                        placeholder="Especificar otras áreas..."
                                        className="w-full px-4 py-2 bg-slate-950 border border-slate-800 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all text-sm mb-4"
                                    />
                                )}
                            </div>

                            <label className="block">
                                <span className="text-xs font-bold uppercase tracking-widest text-slate-500 mb-2 block">Idioma de la Revisión</span>
                                <select
                                    value={editData.language}
                                    onChange={(e) => setEditData({ ...editData, language: e.target.value })}
                                    className="w-full px-4 py-3 bg-slate-950 border border-slate-800 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all"
                                >
                                    <option value="es">Español</option>
                                    <option value="en">English</option>
                                </select>
                            </label>

                            <label className="block">
                                <span className="text-xs font-bold uppercase tracking-widest text-slate-500 mb-2 block">Modelo LLM Predeterminado</span>
                                <select
                                    value={editData.llm_model}
                                    onChange={(e) => setEditData({ ...editData, llm_model: e.target.value })}
                                    className="w-full px-4 py-3 bg-slate-950 border border-slate-800 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all"
                                >
                                    <optgroup label="Recomendados para GPU">
                                        <option value="llama3.1:8b">Llama 3.1 8B (Recomendado)</option>
                                        <option value="qwen2.5:7b">Qwen 2.5 7B</option>
                                        <option value="mistral-nemo:12b">Mistral Nemo 12B</option>
                                        <option value="gpt-oss20b">GPT-OSS 20B (High-VRAM)</option>
                                    </optgroup>
                                    <optgroup label="Recomendados para CPU">
                                        <option value="phi3:3.8b">Phi-3 Mini</option>
                                        <option value="gemma2:2b">Gemma 2 2B</option>
                                    </optgroup>
                                </select>
                            </label>

                            <div className="flex gap-4 mt-4">
                                <button
                                    onClick={handleSave}
                                    disabled={saving}
                                    className="flex-grow py-4 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-black rounded-2xl transition-all shadow-lg shadow-emerald-500/20 disabled:opacity-50"
                                >
                                    {saving ? "GUARDANDO..." : "GUARDAR CAMBIOS"}
                                </button>
                                <button
                                    onClick={() => setIsEditing(false)}
                                    className="px-8 py-4 bg-slate-800 hover:bg-slate-700 text-white font-bold rounded-2xl transition-all"
                                >
                                    CANCELAR
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                <div className="mb-6 border-b border-slate-700/50 pb-4">
                    <h2 className="text-xl font-bold text-slate-200">Historial de Búsquedas</h2>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {searches.map((s, idx) => (
                        <div
                            key={s.id}
                            className="block p-6 bg-slate-800/80 border border-slate-700/50 hover:border-emerald-500/50 rounded-2xl transition-all hover:-translate-y-1 group relative"
                        >
                            <div className="flex justify-between items-start mb-4">
                                <h3 className="text-lg font-bold text-white group-hover:text-emerald-400 transition-colors">
                                    Búsqueda {idx + 1}
                                </h3>
                                <div className="flex items-center gap-2">
                                    <span className="text-xs font-medium text-slate-500 px-2 py-1 bg-slate-800 rounded-md">
                                        {new Date(s.created_at).toLocaleDateString()}
                                    </span>
                                    <button
                                        onClick={(e) => { e.preventDefault(); e.stopPropagation(); setSearchToDelete(s); }}
                                        className="p-1.5 text-slate-500 hover:text-white hover:bg-rose-500 rounded-md transition-colors relative z-20 cursor-pointer"
                                        title="Eliminar esta búsqueda"
                                    >
                                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                        </svg>
                                    </button>
                                </div>
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

                            {/* Make entire card clickable except for the delete button */}
                            <a href={`/search?id=${projectId}&query_id=${s.id}`} className="absolute inset-0 z-0"></a>
                            <div className="relative z-10 flex items-center justify-between mt-auto pointer-events-none pb-0"></div>
                        </div>
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

                <div className="mt-12 mb-6 border-b border-slate-700/50 pb-4">
                    <h2 className="text-xl font-bold text-slate-200">Historial de Revisiones (Screening)</h2>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {screenings.map((s, idx) => (
                        <div
                            key={s.id}
                            className="block p-6 bg-slate-800/80 border border-slate-700/50 hover:border-violet-500/50 rounded-2xl transition-all hover:-translate-y-1 group relative"
                        >
                            <div className="flex justify-between items-start mb-4">
                                <h3 className="text-lg font-bold text-white group-hover:text-violet-400 transition-colors">
                                    {s.name || `Sesión de Screening ${idx + 1}`}
                                </h3>
                                <div className="flex items-center gap-2">
                                    <span className="text-xs font-medium text-slate-500 px-2 py-1 bg-slate-800 rounded-md">
                                        {new Date(s.created_at).toLocaleDateString()}
                                    </span>
                                    <button
                                        onClick={(e) => { e.preventDefault(); e.stopPropagation(); setScreeningToDelete(s); }}
                                        className="p-1.5 text-slate-500 hover:text-white hover:bg-rose-500 rounded-md transition-colors relative z-20 cursor-pointer"
                                        title="Eliminar esta revisión"
                                    >
                                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                        </svg>
                                    </button>
                                </div>
                            </div>

                            <p className="text-sm text-slate-400 mb-6 line-clamp-3">
                                {s.goal || "Sesión de filtrado de resultados."}
                            </p>

                            <div className="flex items-center justify-between mt-auto">
                                <span className="text-xs font-semibold px-2.5 py-1 bg-violet-500/10 text-violet-400 rounded-lg">
                                    {s.reviewed_count} / {s.total_articles} Revisados
                                </span>
                                <div className="flex gap-2">
                                    {s.included_count > 0 && <span className="text-xs text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded">{s.included_count} In</span>}
                                    {s.excluded_count > 0 && <span className="text-xs text-rose-400 bg-rose-500/10 px-1.5 py-0.5 rounded">{s.excluded_count} Ex</span>}
                                </div>
                            </div>

                            {/* Make entire card clickable except for the delete button */}
                            <a href={`/screening?id=${projectId}&setup_session=${s.id}`} className="absolute inset-0 z-0"></a>
                            <div className="relative z-10 flex items-center justify-between mt-auto pointer-events-none pb-0"></div>
                        </div>
                    ))}

                    {screenings.length === 0 && (
                        <div className="col-span-full text-center py-10 border border-dashed border-slate-700 rounded-2xl">
                            <p className="text-slate-500">Aún no se ha iniciado el proceso de Screening (Revisión) para estas búsquedas.</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
