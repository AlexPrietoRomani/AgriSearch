@echo off
setlocal
title AgriSearch Launcher
cd /d "%~dp0"

echo =========================================
echo 🌱 Iniciando AgriSearch - Asistente PRISMA 2020
echo =========================================
echo.
echo [!] NOTA: Asegurate de tener Ollama (o tu proveedor LLM) corriendo en segundo plano.
echo.

REM --- 1. Crear directorios base si no existen ---
IF NOT EXIST "data" mkdir "data"
IF NOT EXIST "vector_db" mkdir "vector_db"

REM --- 2. Verificacion de Entorno Backend (Python) ---
echo [1/4] Verificando entorno de Backend (Python)...
cd backend

IF EXIST "venv\Scripts\activate.bat" GOTO backend_env_exists

echo [!] No se encontro un entorno virtual. Creando uno nuevo...
where uv >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [OK] uv detectado. Creando venv e instalando dependencias con uv...
    call uv venv venv
    call venv\Scripts\activate.bat
    call uv pip install -r requirements.txt
    GOTO backend_env_done
)

echo [!] uv no esta instalado. Usando python nativo...
python -m venv venv
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

:backend_env_done
:backend_env_exists
echo [OK] Entorno virtual configurado.
cd ..

REM --- 3. Verificacion de Entorno Frontend (NPM) ---
echo.
echo [2/4] Verificando entorno de Frontend (NPM)...
cd frontend

IF NOT EXIST "node_modules\" (
    echo [!] Dependencias de Node no encontradas. Instalando (npm install)...
    call npm install
) ELSE (
    echo [OK] Dependencias de Node encontradas.
)

cd ..

REM --- 4. Arrancando Servidores ---
echo.
echo [3/4] Arrancando Servidores en ventanas independientes...
echo Iniciando Backend (FastAPI)...
start "AgriSearch Backend" /D "backend" cmd /k "call venv\Scripts\activate.bat && uvicorn app.main:app --reload --port 8000"

echo Esperando 3 segundos...
timeout /t 3 /nobreak > nul

echo Iniciando Frontend (Astro)...
start "AgriSearch Frontend" /D "frontend" cmd /k "npm run dev"

REM --- 5. Apertura ---
echo.
echo [4/4] Abriendo aplicacion en el navegador...
timeout /t 3 /nobreak > nul
start http://localhost:4321

echo.
echo =========================================
echo ✅ AgriSearch esta corriendo!
echo =========================================
echo Si deseas apagar los servidores, cierra las ventanas de terminal (Backend y Frontend).
pause
