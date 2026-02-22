@echo off
title AgriSearch Launcher
echo =========================================
echo 🌱 Iniciando AgriSearch
echo =========================================
echo.
echo ⚠️  NOTA: Asegurate de tener Ollama (o tu proveedor LLM) corriendo.
echo.

echo Iniciando Backend (FastAPI)...
start "AgriSearch Backend" cmd /k "cd backend && call venv\Scripts\activate && uvicorn app.main:app --port 8000"

echo Esperando 5 segundos para que el backend despierte...
timeout /t 5 /nobreak > nul

echo Iniciando Frontend (Astro)...
start "AgriSearch Frontend" cmd /k "cd frontend && npm run dev"

echo Abriendo tu navegador web...
timeout /t 3 /nobreak > nul
start http://localhost:4321

echo =========================================
echo ✅ AgriSearch esta corriendo!
echo =========================================
echo Si deseas apagar los servidores, simplemente cierra las dos ventanas de terminal que se abrieron.
pause
