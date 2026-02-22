import React from "react";
import { DB_OPTIONS, type DbOption } from "./SearchWizard";

interface Props {
    selectedDBs: string[];
    sourceColor: (db: string) => string;
}

export default function SearchWizardSearching({ selectedDBs, sourceColor }: Props) {
    return (
        <div className="flex flex-col items-center justify-center py-20">
            <div className="w-16 h-16 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin mb-6" />
            <h2 className="text-xl text-white font-semibold mb-2">Buscando artículos...</h2>
            <p className="text-slate-400">Consultando {selectedDBs.length} bases de datos en paralelo</p>
            <div className="flex gap-3 mt-4">
                {selectedDBs.map((db) => (
                    <span key={db} className={`px-3 py-1 rounded-lg text-xs font-medium animate-pulse ${sourceColor(db)}`}>
                        {DB_OPTIONS.find((d: DbOption) => d.id === db)?.label}
                    </span>
                ))}
            </div>
        </div>
    );
}
