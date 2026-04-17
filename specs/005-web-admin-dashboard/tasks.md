# Tasks: Web Admin Dashboard

**Input**: Design documents from `/specs/005-web-admin-dashboard/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/admin-api.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US4)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize the Next.js frontend project and backend admin scaffold.

- [x] T001 Initialize Next.js 15 app in `frontend/` with TypeScript, Tailwind CSS, and App Router (`npx create-next-app@latest frontend --typescript --tailwind --app`)
- [x] T002 [P] Add shadcn/ui to `frontend/` and install base components: button, input, table, dialog, badge, toast
- [x] T003 [P] Create `frontend/.env.example` with `NEXT_PUBLIC_API_URL=http://localhost:8000`
- [x] T004 [P] Create `frontend/src/lib/api.ts` — typed fetch wrapper with base URL, cookie credentials, and JSON error handling
- [x] T005 [P] Add `ADMIN_JWT_SECRET` and `ADMIN_JWT_EXPIRE_MINUTES` to `.env.example` and `src/config.py` (`Settings` class)
- [x] T006 Create `frontend/src/app/layout.tsx` with global nav shell and Toaster provider
- [x] T007 Update `CLAUDE.md` with frontend commands (`npm run dev`, `npm test`, `npm run build`) and new env vars

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Backend auth system and admin router that all user stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T008 Write Alembic migration `migrations/versions/006_add_admin_users.py` — create `admin_users` table (id UUID PK, username VARCHAR(50) UNIQUE, hashed_password VARCHAR(255), is_active BOOLEAN, created_at, last_login_at)
- [x] T009 Create `src/models/admin_user.py` — SQLAlchemy `AdminUser` ORM model matching migration
- [x] T010 Create `scripts/seed_admin.py` — CLI script to create first admin user with bcrypt-hashed password (cost=12), usage: `python3 scripts/seed_admin.py --username admin --password <secret>`
- [x] T011 Create `src/services/admin_auth_service.py` — `AdminAuthService` with: `verify_password()`, `create_access_token()` (JWT, exp = ADMIN_JWT_EXPIRE_MINUTES), `get_current_admin()` FastAPI dependency that reads HttpOnly cookie and validates JWT
- [x] T012 Create `src/api/admin.py` — FastAPI router with prefix `/admin`, CORS restricted to frontend origin; include auth sub-router (`/admin/auth/login`, `/admin/auth/logout`, `/admin/auth/me`); implement rate limiter (5 failed attempts → 15min lockout, in-memory per IP)
- [x] T013 Register `admin_router` in `src/main.py` (`app.include_router(admin_router)`)
- [ ] T014 Create `frontend/src/lib/auth.ts` — `login()`, `logout()`, `getMe()` functions using `lib/api.ts`; export `useAuth` hook
- [x] T015 Create `frontend/src/app/login/page.tsx` — login form (username + password), calls `auth.login()`, redirects to `/dashboard` on success, shows error toast on failure
- [x] T016 Create `frontend/src/middleware.ts` — Next.js middleware that checks for session cookie; redirects unauthenticated requests to `/login`

**Checkpoint**: `POST /admin/auth/login` returns JWT cookie; frontend redirects to `/dashboard`; unauthenticated requests to `/dashboard/*` redirect to `/login`.

---

## Phase 3: User Story 1 — View Dashboard Overview (Priority: P1) 🎯 MVP

**Goal**: Admin can see all appointments and dentists on the dashboard home page.

**Independent Test**: Open `http://localhost:3000/dashboard` after login → appointments list and dentists list render with real data from the database.

### Implementation

- [x] T017 [US1] Add `GET /admin/appointments` endpoint to `src/api/admin.py` — query with `selectinload` on patient and dentist, support `status` filter and `page`/`page_size` params, return paginated response per contract
- [x] T018 [US1] Add `GET /admin/dentists` endpoint to `src/api/admin.py` — return all dentists ordered by name
- [x] T019 [P] [US1] Create `frontend/src/lib/api.ts` appointments functions: `getAppointments(params?)`, `getAppointment(id)` — typed with response shapes from contract
- [x] T020 [P] [US1] Create `frontend/src/lib/api.ts` dentists functions: `getDentists()` — typed response
- [x] T021 [P] [US1] Create `frontend/src/components/ui/AppointmentsTable.tsx` — table showing patient name, dentist, date/time, reason, status badge; empty state message when no data
- [x] T022 [P] [US1] Create `frontend/src/components/ui/DentistsTable.tsx` — table showing name, calendar ID, active/inactive badge; empty state message
- [x] T023 [US1] Create `frontend/src/app/dashboard/page.tsx` — server component fetching appointments and dentists, renders `AppointmentsTable` and `DentistsTable`, shows error banner if fetch fails
- [x] T024 [US1] Create `frontend/src/app/dashboard/layout.tsx` — sidebar nav with links: Dashboard, Appointments, Dentists, Patients

**Checkpoint**: Dashboard home page shows real data. User Story 1 fully functional and independently testable.

---

## Phase 4: User Story 2 — Manage Appointments (Priority: P2)

**Goal**: Admin can view appointment detail, cancel confirmed appointments, and delete records.

**Independent Test**: Navigate to `/dashboard/appointments`, click an appointment → see detail; cancel a confirmed one → status changes to "cancelled"; delete → disappears from list.

### Implementation

- [x] T025 [US2] Add `GET /admin/appointments/{id}` endpoint to `src/api/admin.py` — return single appointment with full patient and dentist detail
- [x] T026 [US2] Add `PATCH /admin/appointments/{id}/cancel` endpoint to `src/api/admin.py` — set `status = cancelled`, return 409 if already cancelled, audit log the action
- [x] T027 [US2] Add `DELETE /admin/appointments/{id}` endpoint to `src/api/admin.py` — delete record, audit log the action, return 404 if not found
- [x] T028 [US2] Add `cancelAppointment(id)` and `deleteAppointment(id)` functions to `frontend/src/lib/api.ts`
- [x] T029 [US2] Create `frontend/src/app/dashboard/appointments/page.tsx` — paginated appointments list with status filter; links to detail page
- [x] T030 [US2] Create `frontend/src/app/dashboard/appointments/[id]/page.tsx` — detail view with "Cancel" button (shown only if status=confirmed) and "Delete" button; each triggers a confirmation dialog before calling API; shows success/error toast

**Checkpoint**: Full appointment CRUD (cancel + delete) works end-to-end with confirmation dialogs.

---

## Phase 5: User Story 3 — Manage Dentists (Priority: P3)

**Goal**: Admin can add, edit, deactivate, and reactivate dentists from the web.

**Independent Test**: Navigate to `/dashboard/dentists` → add a new dentist → it appears in the list; edit name → name updates; deactivate → active_status=false in DB.

### Implementation

- [x] T031 [US3] Add `POST /admin/dentists` endpoint to `src/api/admin.py` — create dentist, validate unique name and calendar_id, audit log
- [x] T032 [US3] Add `PATCH /admin/dentists/{id}` endpoint to `src/api/admin.py` — partial update (name, calendar_id, active_status), audit log
- [x] T033 [US3] Add `createDentist(data)` and `updateDentist(id, data)` functions to `frontend/src/lib/api.ts`
- [x] T034 [US3] Create `frontend/src/components/ui/DentistForm.tsx` — controlled form for name + calendar_id fields with inline validation (non-empty, max lengths)
- [x] T035 [US3] Create `frontend/src/app/dashboard/dentists/page.tsx` — dentists list with "Add Dentist" button that opens `DentistForm` in a dialog; shows success toast on create
- [x] T036 [US3] Create `frontend/src/app/dashboard/dentists/[id]/page.tsx` — edit view using `DentistForm` pre-populated; separate "Deactivate"/"Reactivate" toggle button with confirmation dialog

**Checkpoint**: Full dentist CRUD works. Adding a new dentist makes them immediately available to the bot.

---

## Phase 6: User Story 4 — View Patients (Priority: P4)

**Goal**: Admin can browse all patients and view their linked appointments.

**Independent Test**: Navigate to `/dashboard/patients` → see all registered patients; click one → see their appointments.

### Implementation

- [x] T037 [US4] Add `GET /admin/patients` endpoint to `src/api/admin.py` — paginated list of `telegram_users`, ordered by last interaction descending
- [x] T038 [US4] Add `GET /admin/patients/{id}` endpoint to `src/api/admin.py` — patient detail with `selectinload` on appointments (with dentist)
- [x] T039 [US4] Add `getPatients(params?)` and `getPatient(id)` functions to `frontend/src/lib/api.ts`
- [x] T040 [US4] Create `frontend/src/app/dashboard/patients/page.tsx` — paginated patients list (name, Telegram ID, last interaction); links to detail
- [x] T041 [US4] Create `frontend/src/app/dashboard/patients/[id]/page.tsx` — patient detail with embedded appointments table (read-only)

**Checkpoint**: All four user stories are complete and independently functional.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Hardening, UX consistency, and documentation.

- [x] T042 [P] Add loading skeletons to all data tables in `frontend/src/components/ui/` (show skeleton while fetching)
- [x] T043 [P] Standardize error banner component `frontend/src/components/ui/ErrorBanner.tsx` — used by all pages when API is unreachable
- [ ] T044 SKIPPED: Tests not created per user request
- [ ] T045 SKIPPED: Tests not created per user request
- [ ] T046 SKIPPED: Tests not created per user request
- [x] T047 Update `quickstart.md` with any steps that changed during implementation
- [ ] T048 Run `ruff check src/` and `npm run lint` in `frontend/`; fix all warnings
- [x] T049 Verify constitution compliance: no secrets in code, bcrypt cost=12 confirmed, JWT expiry ≤ 60min, audit log entries present for cancel/delete/create/update

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS all user story phases
- **Phase 3–6 (User Stories)**: All depend on Phase 2; can proceed in priority order or in parallel if staffed
- **Phase 7 (Polish)**: Depends on all desired user story phases complete

### User Story Dependencies

- **US1 (P1)**: Only depends on Foundational — no story dependencies
- **US2 (P2)**: Only depends on Foundational — no story dependencies (appointments endpoints are independent)
- **US3 (P3)**: Only depends on Foundational — no story dependencies
- **US4 (P4)**: Only depends on Foundational — no story dependencies

### Within Each User Story

- Backend endpoints before frontend pages
- `lib/api.ts` functions before components that call them
- Shared components before pages that use them

---

## Parallel Example: User Story 1

```bash
# Run in parallel once T008–T016 (Phase 2) are complete:
Task T017: "Add GET /admin/appointments endpoint in src/api/admin.py"
Task T018: "Add GET /admin/dentists endpoint in src/api/admin.py"

# Then in parallel:
Task T019: "appointments functions in frontend/src/lib/api.ts"
Task T020: "dentists functions in frontend/src/lib/api.ts"
Task T021: "AppointmentsTable component in frontend/src/components/ui/"
Task T022: "DentistsTable component in frontend/src/components/ui/"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (auth + admin router)
3. Complete Phase 3: User Story 1 (dashboard overview)
4. **STOP and VALIDATE**: Log in, see real data on `/dashboard`
5. Demo to stakeholders if ready

### Incremental Delivery

1. Setup + Foundational → auth works, `/dashboard` protected
2. US1 → data visible → **MVP demo**
3. US2 → appointments manageable
4. US3 → dentists manageable without scripts
5. US4 → patient lookup available
6. Polish → tests, cleanup

---

## Notes

- [P] tasks = different files, no blocking dependencies between them
- [USn] label maps task to user story for traceability
- All backend write operations must write to `audit_log` (action prefix `ADMIN_`)
- Run `alembic upgrade head` before starting Phase 2 work
- Frontend dev server proxies `/admin/*` to backend via `NEXT_PUBLIC_API_URL`
- Commit after each checkpoint to keep git history clean
