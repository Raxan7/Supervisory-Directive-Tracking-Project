# AGENTS.md

## Project overview

FastAPI backend for the Supervisory Findings and Directives Tracking & Analytics System (UDOM Innovation Project No. 2). Single package, no monorepo.

## Key commands

```bash
# Dev setup
pip install -e '.[dev]'        # install with dev deps (pytest, httpx, ruff)
alembic upgrade head           # apply DB migrations (SQLite locally, PostgreSQL in Docker)
uvicorn app.main:app --reload  # run dev server on :8000

# Tests (SQLite, no external services needed)
pytest -q

# Lint
ruff check .                   # line-length = 100
```

There is no typecheck command configured; the project does not use mypy or pyright.

## Test quirks

- `conftest.py` sets `DATABASE_URL` to a local SQLite file (`test-supervisory.db`) and disables bootstrap admin before importing the app. Tests always use SQLite regardless of `.env`.
- Database is reset (`drop_all` / `create_all`) before every test via an autouse fixture. Three users are seeded: admin, examiner, manager.
- All integration tests are in `tests/test_integration.py`. Architecture contract tests parse AST and check that specific models/routes/states exist — these are enforced by convention.
- No fixtures require external services (no Docker, no PostgreSQL, no MinIO). `conftest.py` monkeypatches `app.api.upload_file`, `app.api.download_file`, and `app.main.ensure_bucket` with local temp-dir implementations so tests stay hermetic.

## Architecture

- **Entry point**: `app/main.py` — FastAPI app with lifespan, CORS, bootstrap admin, and background alert scheduler.
- **Routes**: `app/api.py` — single `APIRouter` with prefix `/api/v1`. All endpoints are in one file.
- **Models**: `app/models.py` — 12 SQLAlchemy 2 mapped classes. The exact set is enforced by `test_architecture_contract.py`.
- **Config**: `app/core/config.py` — pydantic-settings, reads `.env` via `get_settings()` (lru_cached).
- **DB engine**: `app/db.py` — engine is created at module import time from `get_settings().database_url`. The `get_db` dependency yields a session.
- **Storage**: `app/storage.py` — MinIO client and helpers (`upload_file`, `download_file`, `ensure_bucket`). Object keys stored in `Attachment.file_path` (e.g., `examinations/1/abc_report.docx`).
- **Finding states**: exactly `OPEN`, `IN_PROGRESS`, `CLOSED`, `OVERDUE` (enforced by tests).
- **Roles**: exactly `EXAMINER`, `MANAGER`, `ADMIN` (enforced by tests).

## Gotchas

- `BOOTSTRAP_ADMIN_PASSWORD` requires >= 10 characters or the app raises `RuntimeError` at startup.
- `app/db.py` creates the engine at import time. If you change `DATABASE_URL` after import, it has no effect. The conftest overrides `get_db` to work around this.
- Docker entrypoint runs `alembic upgrade head` before starting uvicorn.
- Docker Compose includes a MinIO service (`minio:9000` for API, `localhost:9001` for web console). Files are stored in the `supervisory-uploads` bucket. Object keys are stored in `Attachment.file_path` (not local paths).
- The `severity` column in import files accepts exactly `low`, `medium`, `high`, or `critical`.
- `pyproject.toml` does not include ruff rules beyond line-length; there is no formatter config beyond ruff.

## Important files

- `ARCHITECTURE_TRACEABILITY.md` — design-to-code mapping; read if you need to understand which original requirement maps to which file.
- `docs/LOCAL_SETUP.md` — extended local dev instructions (overlaps with README).
- `.env.example` — canonical list of all environment variables.
