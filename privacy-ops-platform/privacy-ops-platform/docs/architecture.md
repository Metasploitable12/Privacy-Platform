# Privacy Operations Platform — Phase 0 Architecture Package

**Status:** Pre-implementation. Nothing in Phase 1 begins until this package is reviewed and approved.
**Scope of this document:** Architecture, stack, ERD, RBAC, API design, security architecture, threat model, MVP scope, Phase 1 plan, backlog, deployment, migration strategy, and known risks/limitations — as requested in the master prompt's "Starting Instruction."

This is an independent, functionally-inspired design. No OneTrust source, UI, text, templates, or branding is referenced or reused anywhere in this document.

---

## 1. Proposed Architecture (System Context)

```
                         ┌──────────────────────┐
                         │   Entra ID / OIDC     │  ← SSO + MFA (delegated to IdP)
                         └──────────┬────────────┘
                                    │ OIDC/OAuth2
                                    ▼
┌───────────────────────────────────────────────────────────────────┐
│                        PRIVACY PORTAL (SPA)                        │
│  Dashboard │ Data Map │ ROPA │ Assessments │ DPIA │ Risks          │
│  Vendors │ Transfers │ Retention │ Incidents │ DSR │ Notices       │
│  Policies & Controls │ Evidence │ Reports │ Administration        │
└───────────────────────────────┬───────────────────────────────────┘
                                 │ HTTPS / REST (JSON) + WebSocket (notifications)
                                 ▼
                      ┌────────────────────┐
                      │   Nginx (reverse    │
                      │   proxy, TLS term)  │
                      └──────────┬──────────┘
                                 ▼
                      ┌────────────────────┐
                      │  API Gateway Layer  │  (authn, authz, rate limit, audit hook)
                      └──────────┬──────────┘
                                 ▼
                      ┌────────────────────┐
                      │  FastAPI Backend    │
                      │  (modular monolith, │
                      │   service-oriented  │
                      │   internally)       │
                      └──────────┬──────────┘
             ┌───────────────────┼────────────────────┐
             ▼                   ▼                    ▼
      PostgreSQL           Redis (cache,        S3-compatible
      (system of record,   queues, sessions)    object storage
      tenant-scoped)                            (evidence, exports)
             │
             ▼
   ┌─────────────────────────────┐
   │   Privacy Rules Engine       │  (config-driven, not hard-coded)
   │   ROPA / DPIA / Risk /       │
   │   Review / Retention /       │
   │   Transfer rule sets         │
   └──────────────┬───────────────┘
                  ▼
        ┌───────────────────────┐
        │   Workflow Engine      │  (tasks, approvals, reminders, escalation)
        └──────────┬─────────────┘
                    │
      ┌─────────────┼──────────────┐
      ▼             ▼              ▼
   Email (SMTP)   Teams (opt.)   Jira/ServiceNow (opt.)
```

**Design notes**

- The backend is built as a **modular monolith** for Phase 1–3 (one deployable, internally decomposed into service modules with clear boundaries — ROPA, Assessments, Risk, Workflow, Vendor, Transfer, Retention, Incident, DSR, Evidence, Audit, Notification, Admin). This keeps operational overhead low while preserving a clean seam to split into separate services later if scale demands it (e.g., Data Discovery in Phase 5 is a natural first candidate for extraction, since it's connector-heavy and bursty).
- The **Rules Engine** and **Workflow Engine** are intentionally separated from the CRUD modules — they read configuration (risk factors, thresholds, review periods, workflow stage definitions) rather than embedding legal or business logic in code. This is what lets the platform support multiple regulations without redeploying.
- All external integrations (Teams, Jira, ServiceNow, AWS/Azure discovery connectors) are **optional adapters** behind interfaces; the core platform has zero hard dependency on any of them.

---

## 2. Technology Stack

| Layer | Choice | Rationale |
|---|---|---|
| Frontend | React + Next.js + TypeScript | Matches existing org tooling; SSR not required for an internal tool but Next.js gives good file-based routing/DX even in SPA-mode |
| Backend | Python FastAPI | Async, strong typing via Pydantic, fast to build a large modular API surface with OpenAPI generated for free |
| Database | PostgreSQL 16 | Relational integrity for a compliance system is non-negotiable; JSONB for configurable/dynamic assessment schemas |
| Cache/Queue | Redis | Session cache, rate-limit counters, background job queue (Celery or Arq) for notifications/reviews |
| Object storage | S3-compatible (internal MinIO or cloud S3 bucket, company-controlled) | Evidence files, exports, attachments — never stored in the DB as blobs |
| Auth | Microsoft Entra ID via OIDC | SSO + MFA delegated to IdP; app never handles raw passwords |
| Reverse proxy | Nginx | TLS termination, security headers, request size limits |
| Containerization | Docker | Standard, portable |
| Orchestration | Docker Compose (Phase 1), Kubernetes-ready (later) | Compose is enough for a single-tenant internal deployment initially; services are designed stateless-where-possible so a later Helm chart is straightforward |
| Background jobs | Celery (or Arq) + Redis broker | Reviews, notifications, scheduled escalations |
| IaC | Terraform (for the surrounding infra — object storage, DNS, secrets) | Optional but recommended once beyond a single VM |

---

## 3. Module Architecture

Each module below is a bounded context with its own service layer, repository layer, and API router, sharing the common Postgres database (schema-per-module tables, not separate databases, to keep transactional integrity across linked records like ROPA↔DPIA↔Risk).

```
core/
  auth/              — OIDC integration, session, RBAC enforcement
  audit/              — append-only audit log writer + query API
  tenancy/            — tenant context middleware, tenant_id enforcement
  config/             — configurable taxonomies (countries, regs, categories, roles...)
  workflow/           — generic workflow engine (stages, tasks, approvals, escalation)
  notification/       — email/Teams/in-app dispatch, template engine

modules/
  ropa/               — Processing Activities (central record)
  data_inventory/      — assets, systems, applications, data map graph
  assessments/         — template engine, questions, conditional logic, responses
  dpia/                — DPIA/PIA register, built on assessments + risk
  risk/                — configurable risk engine
  incidents/           — incident intake → closure workflow
  dsr/                 — data subject rights request workflow
  vendors/             — vendor/processor inventory + assessment + DPA tracking
  transfers/            — international transfer register + mechanism tracking
  retention/            — retention matrix, gap reporting
  notices/              — privacy notice inventory + versioning
  policies_controls/    — regulation → requirement → control → evidence mapping
  evidence/              — centralized evidence repository
  reporting/             — report generation (CSV/Excel/PDF/JSON)
  discovery/             — (Phase 5) connector framework for asset/data discovery
  ai_assistant/           — (Phase 5) internal AI assistant, human-in-the-loop only

api/
  v1/                  — versioned REST routers, one per module, mounted under /api/v1
```

**Dependency direction:** `modules/*` depend on `core/*`, never the reverse. Modules may depend on each other only through well-defined service interfaces (e.g., `dpia` calls `risk.calculate()`, not `risk`'s repository directly) — this keeps the eventual service-extraction path open.

---

## 4. Database ERD (Core Entities)

Simplified ERD focused on the central spine — full DDL comes in Phase 1 module design docs.

```
organizations ──< departments ──< users >── roles >── permissions
      │                                │
      │                                └──< user_roles
      │
      ├──< processing_activities (ROPA) ─────────────────────────┐
      │        │  │  │  │  │  │  │  │                            │
      │        │  │  │  │  │  │  │  └──< record_versions          │
      │        │  │  │  │  │  │  └──< evidence_links               │
      │        │  │  │  │  │  └──< retention_rules                 │
      │        │  │  │  │  └──< transfers                          │
      │        │  │  │  └──< dpias                                 │
      │        │  │  └──< risks ──< risk_actions                    │
      │        │  └──< recipients (internal/external/processors)     │
      │        └──< data_categories (M:N via activity_data_category) │
      │                                                              │
      ├──< data_assets (apps/db/storage/systems) ──< asset_processing_activity (M:N with ROPA)
      │
      ├──< vendors ──< subprocessors
      │        └──< vendor_assessments
      │        └──< dpa_contracts
      │
      ├──< incidents ──< incident_actions
      │
      ├──< dsr_requests ──< dsr_tasks
      │
      ├──< privacy_notices
      │
      ├──< policies ──< controls ──< requirements ──< regulations
      │
      ├──< assessment_templates ──< assessment_questions
      │        └──< assessments (instances) ──< assessment_responses
      │
      ├──< workflow_definitions ──< workflow_instances ──< tasks
      │
      ├──< notifications
      │
      └──< audit_logs (append-only, references any object_type/object_id)
```

**Cross-cutting columns on every major table:** `id (uuid)`, `tenant_id`, `organization_id`, `created_at`, `created_by`, `updated_at`, `updated_by`, `status`, `version`.

---

## 5. Entity Relationship Model (Key Tables & Fields)

| Table | Key Fields (beyond audit/tenant columns) |
|---|---|
| `processing_activities` | name, description, business_function, department_id, business_owner_id, processing_owner_id, privacy_owner_id, status, next_review_date, review_frequency, controller_type, purpose, secondary_purpose |
| `data_subject_categories` | name (configurable: customers, employees, applicants...) |
| `data_categories` | name, is_special_category, sensitivity_level |
| `activity_data_subject` / `activity_data_category` | M:N join tables |
| `legal_bases` | name, jurisdiction, description |
| `activity_legal_basis` | processing_activity_id, legal_basis_id, reference_document_id |
| `data_assets` | name, type (app/db/storage/saas/cloud), owner_id, classification |
| `asset_processing_activity` | M:N join |
| `transfers` | processing_activity_id, origin_country_id, destination_country_id, mechanism, scc_reference, adequacy_decision, tia_reference, risk_level, approval_status |
| `retention_rules` | processing_activity_id, data_category_id, retention_period, trigger, deletion_method, owner_id, review_date |
| `assessment_templates` | name, type (DPIA/PIA/TIA/LIA/Vendor/Custom), version |
| `assessment_questions` | template_id, section, question_type, is_required, conditional_logic (JSONB) |
| `assessments` | template_id, processing_activity_id (nullable), status, assignee_id, reviewer_id, approver_id, due_date |
| `assessment_responses` | assessment_id, question_id, value (JSONB), evidence_id |
| `risks` | source_type (activity/dpia/vendor/incident), source_id, likelihood, impact, severity, status |
| `risk_actions` | risk_id, action, owner_id, due_date, status |
| `incidents` | discovered_at, occurred_at, reporter_id, owner_id, systems_involved (M:N), data_subjects_affected_estimate, countries_affected (M:N), notification_assessment_status, status |
| `dsr_requests` | request_type, jurisdiction, identity_verified, deadline, extension_reason, status |
| `vendors` | name, role (processor/controller/joint), risk_rating, dpa_status, next_review_date |
| `evidence` | type, owner_id, classification, expiry_date, storage_key (object storage pointer), linked_object_type, linked_object_id |
| `audit_logs` | user_id, timestamp, action, object_type, object_id, previous_value (JSONB), new_value (JSONB), ip_address, reason |
| `record_versions` | object_type, object_id, version_number, snapshot (JSONB), diff_summary |
| `workflow_definitions` | name, stages (JSONB ordered list), applies_to_object_type |
| `workflow_instances` | definition_id, object_type, object_id, current_stage, status |
| `tasks` | workflow_instance_id, assignee_id, due_date, status, action_taken |

Full DDL with constraints, indexes, and check constraints is a Phase 1 deliverable per module (per the Definition of Done in the master prompt).

---

## 6. RBAC Matrix (Representative Slice)

Enforcement is **server-side only** — the frontend uses permission flags purely to hide/disable UI, never as the authorization boundary.

| Permission | SUPER_ADMIN | PRIVACY_ADMIN | DPO | PRIVACY_ANALYST | BUSINESS_OWNER | PROCESSING_OWNER | SECURITY_REVIEWER | LEGAL_REVIEWER | VENDOR_MANAGER | AUDITOR | READ_ONLY |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| ROPA_VIEW | ✓ | ✓ | ✓ | ✓ | own dept | own | — | — | — | ✓ | ✓ |
| ROPA_CREATE | ✓ | ✓ | ✓ | ✓ | own dept | — | — | — | — | — | — |
| ROPA_EDIT | ✓ | ✓ | ✓ | ✓ | own dept | own (draft) | — | — | — | — | — |
| ROPA_APPROVE | ✓ | ✓ | ✓ | — | — | — | — | — | — | — | — |
| ROPA_DELETE | ✓ | ✓ | — | — | — | — | — | — | — | — | — |
| ROPA_EXPORT | ✓ | ✓ | ✓ | ✓ | — | — | — | — | — | ✓ | — |
| DPIA_CREATE | ✓ | ✓ | ✓ | ✓ | — | own trigger | — | — | — | — | — |
| DPIA_REVIEW | ✓ | ✓ | ✓ | — | — | — | ✓ | ✓ | — | — | — |
| DPIA_APPROVE | ✓ | ✓ | ✓ | — | — | — | — | — | — | — | — |
| INCIDENT_CREATE | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — | — |
| INCIDENT_ASSIGN | ✓ | ✓ | ✓ | — | — | — | — | — | — | — | — |
| INCIDENT_CLOSE | ✓ | ✓ | ✓ | — | — | — | — | — | — | — | — |
| VENDOR_CREATE | ✓ | ✓ | — | — | — | — | — | — | ✓ | — | — |
| VENDOR_ASSESS | ✓ | ✓ | ✓ | ✓ | — | — | ✓ | — | ✓ | — | — |
| ADMIN_CONFIGURE | ✓ | ✓ | — | — | — | — | — | — | — | — | — |
| AUDIT_LOG_VIEW | ✓ | ✓ | ✓ | — | — | — | — | — | — | ✓ | — |
| REPORT_EXPORT | ✓ | ✓ | ✓ | ✓ | — | — | — | — | — | ✓ | — |

Full matrix (all ~30+ permissions × 11 roles) is delivered as a machine-readable seed file (`rbac_matrix.yaml`) in Phase 1, so it's configuration, not code.

---

## 7. API Architecture

- **Style:** REST, versioned under `/api/v1/`, JSON, OpenAPI 3 auto-generated by FastAPI.
- **AuthN:** Bearer token (JWT issued after OIDC login exchange), short-lived access token + refresh via secure httpOnly cookie for the SPA; separate API keys/service accounts for machine-to-machine integration use.
- **AuthZ:** Middleware resolves `user → roles → permissions` and `tenant_id` on every request; every route declares required permission(s) via a decorator, checked before the handler runs (never trusted from the client).
- **Core resource routers:** `/ropa`, `/assets`, `/vendors`, `/assessments`, `/dpia`, `/risks`, `/incidents`, `/dsr`, `/transfers`, `/retention`, `/evidence`, `/users`, `/audit-logs`, `/config/*` (countries, regulations, risk-factors, workflow-definitions, etc.)
- **Pagination:** cursor-based for large collections (ROPA, audit logs).
- **Filtering:** consistent query-param convention (`?status=&owner_id=&department_id=&risk_level=&updated_after=`).
- **Rate limiting:** per-user and per-API-key, enforced at the gateway layer (Nginx + Redis token bucket).
- **Idempotency:** `Idempotency-Key` header supported on POST for import/bulk endpoints.
- **Errors:** RFC 7807 problem-details JSON shape, no stack traces or internal details leaked to clients.
- **Audit hook:** every mutating endpoint (POST/PUT/PATCH/DELETE) writes to `audit_logs` inside the same DB transaction as the mutation — never as a best-effort side call.

---

## 8. Security Architecture

| Control | Approach |
|---|---|
| Identity | Entra ID / OIDC, MFA enforced at IdP, no local password store |
| Session | Short-lived JWT + httpOnly, secure, SameSite cookies; server-side session revocation list in Redis |
| Transport | TLS 1.2+ everywhere, HSTS, no plaintext internal traffic between containers on shared hosts |
| At rest | Postgres encryption at rest (disk/volume level), object storage server-side encryption, secrets never in DB |
| Secrets | External secrets manager (e.g., Azure Key Vault / HashiCorp Vault) — never in source, never in `.env` committed to VCS |
| Input handling | Pydantic schema validation on every request body; parameterized queries only (ORM), no raw string SQL concatenation |
| File uploads | Extension + content-type + magic-byte validation, antivirus scan hook before evidence file is accepted, stored outside web root in object storage |
| Headers | CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy set at Nginx |
| CSRF | SameSite cookies + double-submit token for state-changing form-style requests |
| XSS | React's default escaping + CSP; no `dangerouslySetInnerHTML` on user-supplied content |
| Rate limiting | Per-IP and per-account, tighter limits on auth and export endpoints |
| Audit | Append-only `audit_logs`; DB role for the app user has no UPDATE/DELETE grant on that table, enforced at the Postgres role level, not just app logic |
| Backups | Automated encrypted Postgres backups + object storage versioning; documented RPO/RTO |
| Monitoring | Centralized logging (no PII in log lines beyond IDs), alerting on repeated auth failures, privilege escalation attempts, bulk export events |

---

## 9. Threat Model (STRIDE Summary)

| Threat category | Key risks in this system | Primary mitigations |
|---|---|---|
| **Spoofing** | Stolen session token; fake service account | Short-lived tokens, MFA at IdP, API key rotation, IP allow-listing for service accounts |
| **Tampering** | Modifying audit logs; altering approved ROPA without version trail | Append-only audit table with DB-level grant restriction; `record_versions` snapshot on every state change; approved records require new version, not in-place edit |
| **Repudiation** | User denies making an approval/deletion | Full audit trail with user + timestamp + IP on every mutating action; approvals require explicit action, not implicit |
| **Information Disclosure** | Cross-tenant data leakage; evidence file exposed via predictable URL | `tenant_id` enforced in every query at the repository layer (not just the controller), object storage uses signed, time-limited URLs, never public buckets |
| **Denial of Service** | Bulk export/report abuse; large file upload flood | Rate limiting, file size caps, async job queue for heavy reports rather than blocking request threads |
| **Elevation of Privilege** | Role/permission tampering client-side; privilege escalation via admin misconfiguration | Server-side enforcement only, permission checks unit-tested per route, admin role changes themselves are audited and require a second admin (four-eyes) for `ADMIN_CONFIGURE`-level changes in Phase 2+ |

**Explicitly out of scope for Phase 0/1 threat coverage** (flagged, not solved): supply-chain compromise of third-party npm/pip packages (mitigate via SCA scanning in CI, not architecture); insider threat with legitimate DPO/Admin credentials (mitigated partially by audit trail, not prevented); AI assistant prompt injection via ingested documents (addressed specifically in Phase 5 design, not before).

---

## 10. MVP Scope (Phase 1)

Deliberately narrow, matching the master prompt's phasing:

- Authentication (Entra ID/OIDC) + session management
- RBAC engine (roles, permissions, server-side enforcement) — full matrix, even if only a subset of modules exist yet
- ROPA module (create/edit/review/approve/version, all core fields from Section 3 of the master prompt)
- Data inventory (assets/systems, linked to ROPA)
- Owners (business/processing/privacy owner assignment)
- Evidence (upload, link to ROPA, basic metadata)
- Version history (record_versions on ROPA)
- Audit log (append-only, viewable by PRIVACY_ADMIN/DPO/AUDITOR)
- Import/export (CSV/Excel for ROPA, with validate → preview → map → confirm flow; no silent overwrite)
- Basic dashboard (ROPA counts by status, completeness %, overdue reviews)

**Explicitly deferred to later phases:** assessments/DPIA, risk engine, workflow engine, notifications, vendors, transfers, retention, notices, controls, incidents, DSR, advanced dashboards, integrations, discovery, AI assistant — exactly per the master prompt's Phase 2–5 breakdown.

---

## 11. Phase 1 Implementation Plan

| Step | Deliverable |
|---|---|
| 1.1 | Repo scaffold: FastAPI backend, Next.js frontend, Docker Compose (Postgres, Redis, MinIO, Nginx) |
| 1.2 | Entra ID OIDC integration end-to-end (login, token refresh, logout) |
| 1.3 | `core/tenancy` + `core/auth` (roles, permissions, RBAC seed data, enforcement middleware) |
| 1.4 | `core/audit` (append-only log table + DB grants + write helper used by all mutating endpoints) |
| 1.5 | `modules/ropa` data model + migrations (Alembic) |
| 1.6 | ROPA API (CRUD + status transitions: draft/review/approval/rejection/revision/retirement) with RBAC + audit wired in |
| 1.7 | `record_versions` snapshotting on every ROPA state change; version diff endpoint |
| 1.8 | `modules/data_inventory` (assets/systems) + link to ROPA |
| 1.9 | `modules/evidence` (upload to object storage, metadata, link to ROPA) |
| 1.10 | Import/export (CSV/Excel) with validation/preview/mapping/duplicate-detection flow |
| 1.11 | Frontend: auth flow, ROPA list/detail/edit, data map (basic list view, graph view deferred), evidence upload UI, basic dashboard |
| 1.12 | Test suites: unit (RBAC, audit, versioning), integration (API), authorization tests (cross-tenant, privilege escalation attempts) |
| 1.13 | Documentation: architecture doc (this document, finalized), API docs (auto + narrative), admin guide, RBAC matrix doc, deployment guide |

---

## 12. Development Backlog (Phase 1, Ticket-Level Sample)

- `AUTH-1` Integrate Entra ID OIDC login/logout
- `AUTH-2` JWT issuance + refresh + revocation list in Redis
- `RBAC-1` Seed roles/permissions tables from `rbac_matrix.yaml`
- `RBAC-2` Permission-check decorator + unit tests per route
- `AUDIT-1` Append-only audit table + Postgres grant restrictions
- `AUDIT-2` Audit write helper, wired into ROPA mutations
- `ROPA-1..N` One ticket per field group (identity, controller info, purpose, data subjects, personal data, legal basis, recipients, systems, transfers, retention, security, documentation, compliance) — data model + API + UI + tests
- `ROPA-VER-1` Version snapshot on state transition
- `ROPA-VER-2` Version diff endpoint + UI
- `INV-1` Data asset model + API
- `INV-2` Asset↔ROPA linking
- `EVID-1` Object storage integration (upload/download, signed URLs)
- `EVID-2` Evidence↔ROPA linking + metadata
- `IMPEXP-1` CSV/Excel import pipeline (validate/preview/map/confirm/log)
- `IMPEXP-2` CSV/Excel/JSON export
- `DASH-1` Dashboard metrics endpoint (counts, completeness %, overdue)
- `SEC-1` Security headers + CSP at Nginx
- `SEC-2` File upload validation + AV scan hook
- `TEST-1` Cross-tenant access test suite
- `TEST-2` Privilege escalation test suite
- `DOC-1..7` Docs listed in Section 39 of the master prompt, Phase-1-relevant subset

---

## 13. Deployment Architecture

**Phase 1 (single-tenant, on company infrastructure):**

```
┌─────────────────────────── Company Network ───────────────────────────┐
│                                                                        │
│   ┌──────────┐   ┌───────────┐   ┌──────────┐   ┌──────────────────┐ │
│   │  Nginx   │──▶│  Backend  │──▶│ Postgres │   │  Object Storage   │ │
│   │ (TLS,    │   │ (FastAPI, │   │ (primary │   │  (S3-compatible,  │ │
│   │ compose) │   │ compose)  │   │  + WAL   │   │  internal MinIO   │ │
│   └────┬─────┘   └─────┬─────┘   │  backup) │   │  or cloud bucket) │ │
│        │               │         └──────────┘   └──────────────────┘ │
│        │               ▼                                             │
│        │         ┌──────────┐                                        │
│        │         │  Redis   │                                        │
│        │         └──────────┘                                        │
│        ▼                                                             │
│   ┌──────────┐                                                       │
│   │ Frontend │                                                       │
│   │ (static, │                                                       │
│   │  Next.js │                                                       │
│   │  export) │                                                       │
│   └──────────┘                                                       │
└────────────────────────────────────────────────────────────────────────┘
```

- All containers deployed via a single `docker-compose.yml` initially, environment-specific `.env` values pulled from the secrets manager at deploy time (never committed).
- Postgres runs with WAL archiving to object storage for point-in-time recovery.
- Nginx is the only container exposed to the network; everything else is on an internal Docker network.
- **Kubernetes readiness:** each service is stateless except Postgres/Redis (which would move to managed or StatefulSet equivalents); config is already externalized via environment variables, so a Helm chart translation is mechanical, not a redesign.

---

## 14. Data Migration Strategy (From an Existing ROPA/OneTrust Export)

1. **Extract:** obtain the existing platform's export in its native format (typically CSV/Excel per record type — Inventory, Assessments, Vendors, etc.). No proprietary UI, templates, or code is touched — only the organization's own data export.
2. **Field mapping:** build an explicit mapping table (`source_field → target_field`) reviewed by the privacy team before any import; unmapped source fields are surfaced, not silently dropped.
3. **Staging import:** load into a staging schema first, not directly into production tables.
4. **Validation pass:** required-field checks, referential integrity checks (owners/departments/vendors must resolve to existing or newly-created records), duplicate detection against existing records.
5. **Human review:** privacy team reviews a preview/diff before confirming — this reuses the same import UI flow required generally (Section 24 of the master prompt: validate → preview → map → confirm → log).
6. **Commit:** on confirmation, records are inserted with `version = 1` and an audit log entry noting the migration source and operator.
7. **Reconciliation report:** post-migration report listing imported, skipped, and flagged-for-manual-review records, retained as evidence of the migration itself.
8. **No dual-write period:** the legacy system is treated as read-only/archival once migration is confirmed complete, to avoid two systems of record diverging.

---

## 15. Risks and Limitations

- **This is a large, multi-year scope if built to the full 43-section spec.** The phasing in Section 11 of the master prompt is essential — attempting parallel construction of all modules risks an unmaintainable half-finished system. This package assumes strict phase gating.
- **Regulatory logic is configuration, not legal advice.** The platform can flag "this activity triggered a DPIA per configured rules" — it cannot and must not assert legal compliance. This needs to be reinforced in UI copy, not just backend logic, or users will over-trust the tool.
- **A modular monolith is a deliberate trade-off.** It's right for Phase 1–3 team size and operational simplicity, but if the org later needs independent scaling/deployment of, say, the discovery connectors (Phase 5) or the AI assistant, those will need to be split out — the module boundaries above are designed to make that possible, not to prevent it from ever being necessary.
- **RBAC granularity vs. usability.** An 11-role, 30+ permission matrix is powerful but can become hard for admins to reason about. Recommend a "role templates + overrides" UI in Phase 2 rather than raw permission checkboxes, to keep this usable at scale.
- **Data discovery (Phase 5) is the least certain part of this design.** Automated classification of "personal data" across arbitrary systems is a hard, imprecise problem; the architecture treats it strictly as **decision support with mandatory human review and override**, never as authoritative labeling — but the connector framework itself (auth to AWS/Azure/SaaS APis, handling of discovered metadata) is nontrivial engineering that should get its own dedicated design pass when Phase 5 starts, not be designed prematurely now.
- **AI assistant (Phase 5) requires its own data-handling review** before implementation — specifically whether any external LLM API is used at all, and if so, what data is permitted to leave the environment. The architecture above defaults to **no external AI calls without explicit, per-deployment configuration and approval**, per the master prompt.
- **Self-hosted ≠ zero ongoing security burden.** Choosing to self-host (vs. SaaS) shifts patching, backup testing, and infrastructure hardening onto the internal team; this should be explicitly resourced, not assumed to be "free" compared to a SaaS alternative.
- **This document is an engineering artifact, not a compliance certification.** Final regulatory applicability, DPIA thresholds, and jurisdiction-specific rules must be configured and reviewed by qualified privacy/legal professionals before the rules engine is relied upon operationally — consistent with Section 33 of the master prompt.

---

### Next Step

Per the master prompt's starting instruction: **this package is for review, not implementation.** Once approved (in full or with requested changes), Phase 1 begins per Section 11 above, following the per-feature process in Section 41 of the master prompt (purpose → data model → API → authorization → UI → audit → tests → implement → test → document) for each ticket in the Phase 1 backlog.
