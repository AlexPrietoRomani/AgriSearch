---
description: How to add a new API endpoint to the backend following Clean Code conventions
---

# Adding a New Backend Endpoint

## Steps

1. **Define the Pydantic schema** in `backend/app/models/` — create or modify the appropriate model file. Every model MUST:
   - Use `pydantic.BaseModel` for request/response schemas
   - Include type annotations for ALL fields (Mypy strict)
   - Include docstrings describing the model purpose

2. **Create or update the service** in `backend/app/services/` — all business logic goes here, NOT in the endpoint. Services MUST:
   - Be async functions
   - Accept typed parameters, not raw request objects
   - Handle errors with specific exception classes
   - Include logging via `logging_config`

3. **Create the endpoint** in `backend/app/api/v1/` — the endpoint file MUST:
   - Use `APIRouter` with proper prefix and tags
   - Have Pydantic request/response models as type hints
   - Call the service layer, never implement logic inline
   - Return proper HTTP status codes (201 for creation, 204 for deletion, etc.)
   - Include OpenAPI description via `summary` and `description` parameters

4. **Register the router** in `backend/app/main.py`:
   ```python
   from app.api.v1 import new_module
   app.include_router(new_module.router, prefix="/api/v1")
   ```

5. **Write tests** in `tests/unit/` and `tests/integration/`:
   - Unit test the service function in isolation
   - Integration test the endpoint with TestClient

6. **Run quality checks**:
   ```powershell
   ruff check backend/
   mypy backend/
   pytest tests/
   ```

## Naming Conventions
- Endpoint files: `snake_case.py` (e.g., `search.py`, `screening.py`)
- Models: `PascalCase` classes (e.g., `ArticleCreate`, `ArticleResponse`)
- Services: `snake_case` functions (e.g., `execute_search`, `classify_article`)
- All project-scoped data must use `project_id` as foreign key
