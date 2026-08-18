# Supervisory Findings and Directives Tracking Backend

Working FastAPI backend for UDOM Innovation Concept Note Project No. 2. The implementation preserves the original 12-table database design and exposes the operational services required by the architecture.

## Implemented capabilities

- Signed bearer-token authentication and role-based access for Examiner, Manager, and Admin
- Bank, examination, risk-outcome, finding, directive, and remedial-action workflows
- Finding status transitions, status history, and immutable audit events
- CSV, XLSX, DOCX, and table-based PDF finding imports
- Finding attachments with authenticated download
- Automatic repeated/chronic-finding similarity detection
- Deadline/overdue processing, persisted alerts, and optional SMTP delivery
- Dashboard summary, finding-to-risk-outcome analytics, and CSV reporting
- PostgreSQL production configuration, Alembic migration, Docker startup, and SQLite test support

## Quick start with Docker

```bash
cp .env.example .env
# Set SECRET_KEY and the BOOTSTRAP_ADMIN_* values in .env.
docker compose up --build
```

The container applies the Alembic migration before starting. Open:

- API documentation: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

After the first successful start, remove `BOOTSTRAP_ADMIN_PASSWORD` from `.env`. Alternatively, leave the bootstrap values empty and run:

```bash
docker compose exec api python scripts/create_admin.py
```

## Local development

Python 3.12 or newer is recommended.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

The default configuration uses SQLite. Set `DATABASE_URL` to the PostgreSQL URL shown in `.env.example` for the deployed architecture.

## Import columns

Finding imports require these exact headings:

```text
examination_id,bank_id,title,description,risk_category,severity,deadline
```

`severity` accepts `low`, `medium`, `high`, or `critical`; `deadline` uses ISO format `YYYY-MM-DD`. DOCX and PDF imports must contain a table with the headings in its first row.

## Tests

```bash
pytest -q
```

The integration suite verifies login, role enforcement, the full supervisory workflow, document import, attachments, reporting, automatic alerts, audit access, security helpers, and architecture contracts.

See `ARCHITECTURE_TRACEABILITY.md` for the design-to-code mapping.
