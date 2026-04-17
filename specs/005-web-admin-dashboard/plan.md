# Implementation Plan: Web Admin Dashboard

**Branch**: `005-web-admin-dashboard` | **Date**: 2026-04-17 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/005-web-admin-dashboard/spec.md`

## Summary

Build a web admin dashboard that allows clinic staff to view, create, edit, and delete the core bot data (appointments, dentists, patients) stored in the existing PostgreSQL database. The dashboard exposes new admin API endpoints on the existing FastAPI backend and a Next.js frontend in the `frontend/` directory. Access is protected by username/password authentication with session tokens.

## Technical Context

**Language/Version**: Python 3.11 (backend) / TypeScript + Node.js 20 (frontend)  
**Primary Dependencies**: FastAPI + SQLAlchemy async (backend, existing); Next.js 15 App Router, Tailwind CSS (frontend, new)  
**Storage**: PostgreSQL via asyncpg (existing schema; no new tables required except admin credentials)  
**Testing**: pytest (backend); Jest + React Testing Library (frontend)  
**Target Platform**: Web browser (desktop-first), Linux server  
**Project Type**: Full-stack web application (new frontend + new API layer on existing backend)  
**Performance Goals**: Dashboard pages load in under 2 seconds; write operations respond in under 500ms  
**Constraints**: Authentication required on all admin routes; no direct DB access from browser; audit log all write operations  
**Scale/Scope**: Single clinic, ~2-5 concurrent admin users; small data volumes (hundreds of appointments, <10 dentists, hundreds of patients)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Clean Code & Simplicity | ✅ PASS | Frontend and backend kept separate with clear responsibilities; no over-engineering |
| II. Security-First | ✅ PASS | Auth on all endpoints; bcrypt passwords; session tokens; audit logging; CSRF protection required |
| III. Performance & Scalability | ✅ PASS | Small user base; stateless backend; no N+1 queries |
| IV. Test-First & Reliability | ✅ PASS | Unit + integration tests ship with feature |
| V. Extensibility & Data Integrity | ✅ PASS | Reuses existing schema and models; no duplication |
| Security & Compliance | ✅ PASS | Passwords hashed bcrypt cost≥12; session 1h max; rate limiting on login; audit trail |

**Post-Phase-1 re-check**: See research.md and data-model.md for any new violations.

## Project Structure

### Documentation (this feature)

```text
specs/005-web-admin-dashboard/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── admin-api.md
└── tasks.md
```

### Source Code (repository root)

```text
src/
├── api/
│   ├── webhook.py          # existing
│   └── admin.py            # NEW: admin REST endpoints
├── models/
│   └── admin_user.py       # NEW: AdminUser model
├── services/
│   └── admin_service.py    # NEW: admin business logic
└── ...                     # existing files unchanged

frontend/                   # NEW: Next.js application
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx            # redirect to /dashboard
│   │   ├── login/
│   │   │   └── page.tsx
│   │   └── dashboard/
│   │       ├── page.tsx            # overview
│   │       ├── appointments/
│   │       │   ├── page.tsx        # list
│   │       │   └── [id]/page.tsx   # detail / actions
│   │       ├── dentists/
│   │       │   ├── page.tsx        # list + add
│   │       │   └── [id]/page.tsx   # edit / deactivate
│   │       └── patients/
│   │           ├── page.tsx        # list
│   │           └── [id]/page.tsx   # detail
│   ├── components/
│   │   ├── ui/                 # shared UI components
│   │   └── layout/             # nav, header, sidebar
│   └── lib/
│       ├── api.ts              # typed API client
│       └── auth.ts             # session helpers
├── package.json
└── next.config.ts

tests/
├── unit/                   # existing
├── integration/            # existing
└── admin/                  # NEW: admin API integration tests
```

**Structure Decision**: Web application layout (Option 2). Backend stays in `src/`; frontend goes in `frontend/` per project specification. New admin endpoints added as a separate router `src/api/admin.py` to avoid touching the existing webhook router.

## Complexity Tracking

No constitution violations requiring justification.
