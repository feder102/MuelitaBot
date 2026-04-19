# Research: Web Admin Dashboard (005)

## 1. Next.js App Router vs Pages Router

**Decision**: Use Next.js 15 with App Router.  
**Rationale**: App Router is the current recommended approach, supports React Server Components (faster initial loads), and has better built-in layout nesting suited for a multi-section dashboard.  
**Alternatives considered**: Pages Router — stable but legacy; not the direction Next.js is investing in.

## 2. Admin Authentication Strategy

**Decision**: Custom username/password with bcrypt + JWT session tokens stored in HttpOnly cookies.  
**Rationale**:
- No external identity provider needed (single clinic, internal tool).
- HttpOnly cookies prevent XSS token theft.
- JWTs are stateless — fits the existing stateless backend principle.
- Constitution requires bcrypt cost ≥ 12 and session tokens ≤ 1 hour.
- Refresh tokens (longer-lived, stored in DB) allow silent renewal without re-login.

**Implementation**:
- `POST /admin/auth/login` → verifies password, returns JWT in HttpOnly cookie.
- `POST /admin/auth/logout` → clears cookie.
- `GET /admin/auth/me` → validates token, returns admin identity.
- All `/admin/*` routes protected by a FastAPI dependency that reads and validates the JWT.

**Alternatives considered**: Basic Auth — simpler but poor UX and harder to invalidate; Google OAuth — rejected by user.

## 3. Frontend API Communication

**Decision**: Typed fetch client (`lib/api.ts`) calling the FastAPI backend at `NEXT_PUBLIC_API_URL`. No GraphQL.  
**Rationale**: The backend already exposes REST endpoints. A thin typed client keeps things simple and matches constitution Principle I (simplicity). Server Components can fetch directly from backend; client components use the same client from the browser.  
**Alternatives considered**: tRPC — overkill given the small surface; React Query — add if caching/refetch complexity grows, not needed for v1.

## 4. UI Component Library

**Decision**: Tailwind CSS + shadcn/ui (headless, copy-paste components).  
**Rationale**: shadcn/ui components are unstyled primitives that give good accessibility out of the box without locking into a design system. No external dependency at runtime — components are copied into the project.  
**Alternatives considered**: MUI / Ant Design — heavier bundles, opinionated styling; plain Tailwind — more boilerplate for tables, dialogs, forms.

## 5. Admin Credential Storage

**Decision**: New `admin_users` table (id, username, hashed_password, created_at). Single row seeded via a CLI script.  
**Rationale**: Minimal new schema; reuses existing SQLAlchemy async infrastructure. Constitution requires bcrypt ≥ 12.  
**Migration**: Alembic migration `006_add_admin_users.py`.

## 6. CSRF Protection

**Decision**: SameSite=Strict on session cookie + custom request header check (`X-Requested-With: XMLHttpRequest`) for state-mutating endpoints.  
**Rationale**: SameSite=Strict prevents cross-origin cookie submission. Double-submit pattern adds defense-in-depth without requiring a token store. Constitution explicitly requires CSRF prevention.

## 7. Rate Limiting on Login

**Decision**: In-memory counter per IP with 5 failed attempts → 15-minute lockout, implemented as a FastAPI middleware.  
**Rationale**: Constitution mandates this. In-memory is fine for a single-process deployment; can be moved to Redis if horizontally scaled later.

## 8. Audit Logging

**Decision**: Reuse the existing `audit_log` table. Admin write operations log with action type `ADMIN_*` and include the admin username in `error_detail` field (or a new `actor` field if preferred).  
**Rationale**: Constitution requires immutable audit trail for all data modifications. Reusing the existing table avoids new infrastructure.

## 9. No N+1 Queries

**Decision**: All list endpoints use SQLAlchemy `selectinload` or explicit JOINs to eager-load related data.  
**Rationale**: Constitution Principle III prohibits N+1 queries. Appointments list must join dentist and patient in a single query.
