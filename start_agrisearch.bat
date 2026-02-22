@echo off
title AgriSearch Launcher
echo =========================================
echo 🌱 Iniciando AgriSearch - Asistente PRISMA 2020
echo =========================================
echo.
echo ⚠️  NOTA: Asegurate de tener Ollama (o tu proveedor LLM) corriendo en segundo plano.
echo.

REM --- 1. Verificación de Directorios y Entorno Backend ---
echo [1/4] Verificando entorno de Backend (Python)...
cd backend

IF NOT EXIST "venv\Scripts\activate.bat" (
    echo [!] No se encontro un entorno virtual. Creando uno nuevo...
    
    REM Intenta usar uv si esta disponible
    where uv >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        echo [OK] uv detecado. Creando venv e instalando dependencias con uv...
        uv venv venv
        call venv\Scripts\activate.bat
        uv pip install -r requirements.txt
    ) else (
        echo [!] uv no esta instalado. Usando python venv nativo...
        python -m venv venv
        call venv\Scripts\activate.bat
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    )
) ELSE (
    echo [OK] Entorno virtual encontrado.
)

REM Crear directorios base si no existen para evitar errores SQLite/Qdrant
IF NOT EXIST "..\data" mkdir "..\data"
IF NOT EXIST "..\vector_db" mkdir "..\vector_db"

cd ..

REM --- 2. Verificación de Directorios y Entorno Frontend ---
echo.
echo [2/4] Verificando entorno de Frontend (NPM)...
cd frontend

IF NOT EXIST "node_modules\" (
    echo [!] Dependencias de Node no encontradas. Instalando (npm install)...
    npm install
) ELSE (
    echo [OK] Dependencias de Node encontradas.
)

cd ..

REM --- 3. Arrancando Servidores ---
echo.
echo [3/4] Arrancando Servidores en ventanas independientes...
echo Iniciando Backend (FastAPI)...
start "AgriSearch Backend" cmd /k "cd backend && call venv\Scripts\activate && uvicorn app.main:app --port 8000"

echo Esperando 5 segundos para que el backend despierte e inicialice SQLite...
timeout /t 5 /nobreak > nul

echo Iniciando Frontend (Astro)...
start "AgriSearch Frontend" cmd /k "cd frontend && npm run dev"

REM --- 4. Apertura ---
echo.
echo [4/4] Abriendo aplicacion en el navegador...
timeout /t 3 /nobreak > nul
start http://localhost:4321

echo.
echo =========================================
echo ✅ AgriSearch esta corriendo!
echo =========================================
echo Si deseas apagar los servidores, simplemente cierra las dos ventanas de terminal (Backend y Frontend).
pause
