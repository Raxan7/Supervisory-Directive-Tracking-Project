# Local Development Setup

## Prerequisites

- Python 3.12 or newer
- pip

## Quick Start

### 1. Create virtual environment and install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

### 2. Configure environment

Copy `.env.example` and edit for local development:

```bash
cp .env.example .env
```

Key `.env` changes for local (non-Docker) development:

| Variable | Docker Value | Local Value |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://supervisory:supervisory@db:5432/supervisory` | `sqlite:///./supervisory.db` |
| `UPLOAD_DIR` | `/app/uploads` | `./uploads` |

Set a secure `SECRET_KEY` (at least 32 characters) for any environment.

### 3. Run database migrations

```bash
alembic upgrade head
```

### 4. Start the server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Verify

- Health check: http://localhost:8000/health
- API docs (Swagger): http://localhost:8000/docs

## Running with Docker

```bash
cp .env.example .env
# Set SECRET_KEY and BOOTSTRAP_ADMIN_* values in .env
docker compose up --build
```

The Docker setup uses PostgreSQL and auto-applies migrations on startup.

## Running Tests

```bash
pytest -q
```

## Creating an Admin User

If `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD` are set in `.env`, an admin user is created automatically on first startup.

Alternatively, create one manually:

```bash
python scripts/create_admin.py
```

## Finding Import Format

CSV/XLSX/DOCX imports require these column headers:

```
examination_id,bank_id,title,description,risk_category,severity,deadline
```

- `severity`: `low`, `medium`, `high`, or `critical`
- `deadline`: ISO format `YYYY-MM-DD`
