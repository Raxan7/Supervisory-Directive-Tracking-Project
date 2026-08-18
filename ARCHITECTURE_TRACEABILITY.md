# Architecture Traceability

Authoritative sources:

1. `Innovation Concept Notes Projects _ UDOM (1).xlsx`, Project No. 2.
2. `Markdown to PDF (1)(2).pdf`, original system architecture and diagram set.

| Original design element | Starter implementation |
|---|---|
| React Frontend | Stable `/api/v1` REST contract and CORS configuration |
| Python Backend / FastAPI | `app/main.py`, `app/api.py`, dependencies and services |
| Authentication & User Management | Signed bearer tokens, PBKDF2 password hashing, Admin-managed users, RBAC |
| Examination Management | Bank and examination endpoints/models |
| Findings & Directives Module | Findings, status transitions, directives, remedial actions |
| Document Import Module | `/imports/findings` plus adapter boundary for CSV/XLSX/DOCX/PDF |
| Document Storage | Attachment entity and controlled upload directory |
| Deadline & Alert Module | Overdue-state service and pending-alert endpoint |
| Dashboard & Reporting | Dashboard aggregate endpoint by system or bank |
| AI / ML Analytics | Replaceable similarity service and `FINDING_MATCH` persistence |
| Audit Logging | `AUDIT_LOG` records for privileged mutations |
| PostgreSQL Database | SQLAlchemy 2 models, Alembic migration, Docker PostgreSQL service |
| Email Service | SMTP settings and alert-service boundary |

## Original lifecycle

The code uses exactly: `OPEN`, `IN_PROGRESS`, `CLOSED`, and `OVERDUE`.

## Original roles

The code uses exactly: `EXAMINER`, `MANAGER`, and `ADMIN`.

## Original ERD contract

All 12 original entities are implemented:

1. USER
2. BANK
3. RISK_OUTCOME
4. EXAMINATION
5. FINDING
6. DIRECTIVE
7. REMEDIAL_ACTION
8. AUDIT_LOG
9. STATUS_HISTORY
10. ATTACHMENT
11. ALERT
12. FINDING_MATCH

The starter adds only operational authentication fields (`password_hash`, `is_active`) required
to make the original Authentication & User Management module executable. It does not remove or
rename the original database attributes.

## Intentional extension boundaries

- XLSX, DOCX, and PDF parsers should be added as adapters under the existing import endpoint;
  they must produce the same validated `FindingCreate` contract.
- The initial similarity algorithm is deterministic and local. A later ML model can replace it
  without changing the `FINDING_MATCH` table or endpoint contract.
- SMTP delivery should be implemented behind the alert service without exposing database data
  directly to the email provider.

