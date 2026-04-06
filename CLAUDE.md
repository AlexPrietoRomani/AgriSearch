# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Backend (FastAPI)

- **Setup environment**: `cd backend && python -m venv venv && .\venv\Scripts\activate && pip install -r requirements.txt`
- **Run server**: `cd backend && .\venv\Scripts\activate && uvicorn app.main:app --reload`
- **Database migration/init**: `cd backend && .\venv\Scripts\activate && python create_tables.py`
- **Check database schema**: `cd backend && .\venv\Scripts\activate && python dump_schema.py`

### Frontend (Astro + React)

- **Install dependencies**: `cd frontend && npm install`
- **Run development server**: `cd frontend && npm run dev`
- **Build for production**: `cd frontend && npm run build`

## Architecture Overview

AgriSearch is a dual-layered application designed for systematic literature reviews following PRISMA 2020 guidelines.

### Backend Structure (`/backend`)
Built with **FastAPI**, the backend handles complex orchestrations between scientific databases, local LLMs (via Ollama), and vector storage.

- **`app/api/v1/`**: REST API endpoints organized by domain:
    - `projects.py`: Management of research projects and metadata.
    - `search.py`: Query building (via LLM), multi-database execution, and PDF downloading.
    - `screening.py`: PRISMA-compliant screening workflows, decision tracking, and abstract translation.
- **`app/services/`**: Core business logic:
    - `search_service.py`: Orchestrates searches across OpenAlex, Semantic Scholar, ArXiv, etc.
    - `download_service.py`: Manages asynchronous PDF retrieval.
    - `llm_service.py`: Interface for generating search queries and extracting concepts using Ollama/LiteLLM.
    - `mcp_clients/`: Specialized clients for interacting with external scientific data sources.
- **`app/models/`**: SQLAlchemy models for SQLite and Pydantic schemas for API validation.
- **`app/db/`**: Database connection and initialization logic.

### Frontend Structure (`/frontend`)
An **Astro**-based application with a hybrid rendering approach (SSR for speed/SEO, React for interactive components).

- **`src/lib/api.ts`**: Centralized TypeScript client for all backend API interactions.
- **`src/components/`**: React-based interactive components (e.g., PDF viewer, screening cards, search forms).
- **`src/pages/`**: Astro routes defining the application's views (Project list, Search interface, Screening dashboard).
- **Styling**: Uses **Tailwind CSS** for responsive, utility-first styling.

### Data Flow
1. **Search Phase**: User input $\to$ LLM (Ollama) $\to$ Boolean Query $\to$ Multi-source API calls $\to$ SQLite/Qdrant storage.
2. **Screening Phase**: Downloaded PDFs $\to$ Text extraction $\to$ User decision (Include/Exclude) $\to$ Database update.
