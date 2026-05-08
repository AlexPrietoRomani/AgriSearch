"""
Archivo: backup_db.py
Modificación: 2026-05-08
Autor: Alex Prieto

Descripción:
Script de utilidad para la realización de copias de seguridad (backups) de la base
de datos SQLite de AgriSearch. Se recomienda su ejecución antes de realizar
migraciones de esquema o limpiezas masivas de datos.

Acciones Principales:
    - Identifica la ubicación actual de la base de datos operativa.
    - Genera una copia con marca de tiempo (timestamp) en el directorio de backups.
    - Verifica la existencia del archivo origen y reporta el tamaño del backup generado.

Estructura Interna:
    - `backup`: Función principal que ejecuta la copia física del archivo.

Entradas / Dependencias:
    - `shutil`: Para la copia de archivos.
    - `pathlib`: Para la gestión de rutas.

Salidas / Efectos:
    - Crea un nuevo archivo `.db` en `data/backups/`.
    - Imprime mensajes de confirmación y tamaño del archivo en la terminal.

Ejecución:
    python temp/backup_db.py

Ejemplo de Uso:
    python temp/backup_db.py
"""

import shutil
from datetime import datetime
from pathlib import Path


def backup():
    db_path = Path("data/agrisearch.db")
    backup_dir = Path("data/backups")
    backup_dir.mkdir(parents=True, exist_ok=True)

    if not db_path.exists():
        print(f"Error: No se encontró {db_path}")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"agrisearch_{timestamp}.db"
    shutil.copy2(db_path, backup_path)
    size_kb = backup_path.stat().st_size / 1024
    print(f"Backup creado: {backup_path} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    backup()
