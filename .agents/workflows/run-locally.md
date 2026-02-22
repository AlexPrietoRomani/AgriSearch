---
description: How to run the AgriSearch project locally (frontend + backend + services)
---

# Running AgriSearch Locally

// turbo-all

## Prerequisites
1. Ensure Ollama is installed and running with required models:
```powershell
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

2. Ensure Qdrant is running locally (port 6333):
```powershell
# Option A: Docker
docker run -p 6333:6333 qdrant/qdrant

# Option B: Direct binary (see https://qdrant.tech/documentation/guides/installation/)
```

3. Ensure Node.js ≥ 20 and Python ≥ 3.11 are installed.

## Starting the Backend
1. Navigate to the backend directory and activate the virtual environment:
```powershell
cd C:\Users\ALEX\Github\Chat_busqueda_sistematica\backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Run database migrations:
```powershell
alembic upgrade head
```

3. Start FastAPI dev server:
```powershell
uvicorn app.main:app --reload --port 8000
```

## Starting the Frontend
1. Navigate to the frontend directory and install dependencies:
```powershell
cd C:\Users\ALEX\Github\Chat_busqueda_sistematica\frontend
npm install
```

2. Start Astro dev server:
```powershell
npm run dev
```

3. Open browser at `http://localhost:4321`

## Verifying Everything Works
- Backend health: `GET http://localhost:8000/health`
- Frontend loads: `http://localhost:4321`
- Ollama responds: `curl http://localhost:11434/api/tags`
- Qdrant responds: `curl http://localhost:6333/collections`
