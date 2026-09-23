# Privacy Operations Platform — Phase 1 Scaffold

Self-hosted, enterprise privacy-operations platform (ROPA / data inventory /
RBAC / audit trail as the Phase 1 foundation). This repository is the
**working scaffold** that implements the architecture in
[`docs/architecture.md`](docs/architecture.md).

This is not the full 43-module system from the master product prompt — it is
the **Phase 1 MVP slice**: auth, RBAC, ROPA, data inventory, evidence,
versioning, audit log, import/export, and a basic dashboard endpoint. Later
phases (assessments, DPIA, risk engine, workflow engine, vendors, transfers,
retention, incidents, DSR, discovery, AI assistant) are intentionally not
implemented yet, per the phased build plan.

No OneTrust or any third-party vendor's source code, UI, text, or branding
is used anywhere in this repository — this is an independent implementation
of generic privacy-operations functional requirements.

## Stack

- **Backend:** Python, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2
- **Database:** PostgreSQL 16
- **Cache/queue:** Redis
- **Object storage:** S3-compatible (MinIO locally, or any S3-compatible bucket)
- **Frontend:** Next.js + TypeScript (skeleton only in this scaffold)
- **Auth:** OIDC (Entra ID) — stubbed with a pluggable interface; wire your
  tenant's OIDC settings in `.env` before relying on it for anything real
- **Reverse proxy:** Nginx (see `docker-compose.yml`)

## Repository layout

```
privacy-ops-platform/
├── backend/
│   ├── app/
│   │   ├── core/          # config, db session, security/OIDC, tenancy, RBAC, audit
│   │   ├── models/         # SQLAlchemy models (users, roles, ROPA, assets, evidence, audit)
│   │   ├── schemas/        # Pydantic request/response schemas
│   │   ├── api/v1/         # versioned FastAPI routers
│   │   ├── services/       # business logic layer (ROPA versioning, RBAC checks, audit writes)
│   │   ├── tests/          # pytest suite: RBAC enforcement, audit, ROPA lifecycle
│   │   └── main.py         # FastAPI app entrypoint
│   ├── alembic/             # DB migrations
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                # Next.js skeleton (dashboard/ROPA list pages stubbed)
├── rbac_matrix.yaml          # source-of-truth permission matrix (seeded into DB on startup)
├── docker-compose.yml
├── .env.example
└── docs/
    └── architecture.md       # full architecture package (from Phase 0)
```

## Getting started (local dev)

```bash
cp .env.example .env          # fill in real values before anything beyond local dev
docker compose up --build
```

This brings up: Postgres, Redis, MinIO (S3-compatible), the FastAPI backend
(with hot reload), and Nginx in front of it. On first boot, the backend runs
Alembic migrations automatically and seeds `rbac_matrix.yaml` into the
`roles`/`permissions` tables.

Backend API docs (OpenAPI): `http://localhost:8000/docs` once running.

To run the backend test suite:

```bash
cd backend
pip install -r requirements.txt
pytest
```

## What's implemented vs. stubbed in this scaffold

| Area | Status |
|---|---|
| Postgres models: users, roles, permissions, tenants, ROPA, data assets, evidence, audit_logs, record_versions | ✅ implemented |
| RBAC enforcement (server-side, per-route) | ✅ implemented |
| Audit log (append-only, DB-grant restricted) | ✅ implemented |
| ROPA CRUD + status transitions + versioning | ✅ implemented |
| Data asset inventory + linking to ROPA | ✅ implemented |
| Evidence upload metadata (S3-compatible storage) | ✅ implemented |
| CSV import/export for ROPA | ✅ implemented (basic validate → preview → confirm flow) |
| Basic dashboard metrics endpoint | ✅ implemented |
| OIDC / Entra ID login | ⚠️ stubbed — interface + config in place, wire your tenant's app registration to make it real |
| Frontend | ⚠️ skeleton only — pages exist and call the API, styling/UX is minimal |
| Assessments, DPIA, risk engine, workflow engine, vendors, transfers, retention, notices, controls, incidents, DSR, discovery, AI assistant | ❌ not built (Phase 2+, per the phased plan) |

## Pushing this to your own Git remote

```bash
cd privacy-ops-platform
git init
git add .
git commit -m "Phase 1 scaffold: auth stub, RBAC, ROPA, audit, versioning, evidence, import/export"
git branch -M main
git remote add origin <your-remote-url>
git push -u origin main
```

A `.gitignore` is included so `.env`, `__pycache__`, `node_modules`, and
local volumes are not committed. **Do not commit a filled-in `.env`** —
secrets belong in your secrets manager, per the security architecture in
`docs/architecture.md`.
