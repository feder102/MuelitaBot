# Phase 0 Research: Appointment Booking with Google Calendar

**Date**: 2026-04-04  
**Feature**: [Appointment Booking with Google Calendar](spec.md)  
**Status**: COMPLETE - All technical decisions documented

---

## Research Questions & Decisions

### 1. Google Calendar Authentication Strategy

**Question**: How should the system authenticate with Google Calendar API - service account or OAuth2?

**Context**: The feature requires reading available calendar slots from a Google Calendar managed by the medical center. Credentials must be loaded from environment variables per security requirements.

**Decision**: **Service Account Authentication**

**Rationale**:
- Medical center controls a single shared calendar (non-user-specific)
- No user consent flow needed (not delegating user's calendar)
- Service account credentials (JSON key) stored in `.env` as base64-encoded string
- Simpler to test and deploy (no OAuth2 redirect flow)
- Direct calendar access with fixed permissions
- Cost-effective: single long-lived service account

**Alternatives Considered**:
- OAuth2 with user consent: Would allow per-doctor calendars, but adds complexity (refresh tokens, user consent, redirect handling). Suitable for v2+ when multi-doctor support needed.
- API key (public): Cannot write appointments, only read. Missing authorization control.

**Implementation**:
- Store Google service account JSON as base64 string in `.env`: `GOOGLE_CALENDAR_CREDENTIALS_B64`
- Decode in `src/config.py` and load via `google.oauth2.service_account.Credentials.from_service_account_info()`
- Authenticate calls to `google.auth.transport.requests.Request` (already imported in requirements via `google-auth`)

**Testing Approach**:
- Unit tests: Mock Google API client with `unittest.mock`
- Integration tests: Use Google Calendar test account with actual API calls (opt-in via env var)

---

### 2. Calendar Slot Caching Strategy

**Question**: Should calendar slots be cached in-memory, database, or fetched fresh each time?

**Context**: Performance goal is <3 seconds to display slots. Google Calendar API has rate limits (500 requests/user/100 seconds). Slots don't change frequently (doctor manually updates calendar).

**Decision**: **Two-tier Caching with TTL-based Invalidation**

**Strategy**:
1. **Database Cache** (primary): Store fetched slots in PostgreSQL with TTL
   - Table: `cached_calendar_slots` (date, start_time, end_time, is_booked, cached_at, expires_at)
   - TTL: 1 hour (slots refresh hourly, acceptable lag for medical appointments)
   - Invalidation: Delete expired entries on read, or via background job (optional v2)
   
2. **In-Memory Cache** (optional, future): Redis/Memcached for frequently accessed time ranges
   - First check: Redis → Database → Google Calendar API
   - Cache-aside pattern: Load from DB, store in Redis if hit from API
   - Trade-off for v1: Skip Redis (add in v2 if performance bottleneck)

3. **Eager Refresh**: When user books appointment
   - Mark corresponding slot as `is_booked = true` in cache immediately
   - Next calendar fetch (after TTL) will refresh from Google Calendar
   - Prevents double-booking by respecting DB record before API

**Rationale**:
- <3 second goal easily met by database query (nanoseconds to <100ms)
- 1-hour TTL acceptable for medical clinic (appointments scheduled hours/days in advance)
- Graceful degradation: If Google Calendar unavailable, show cached slots (safe, doctor manages availability)
- Cost: Minimal API usage (<240 calls/day if checked hourly)

**Alternatives Considered**:
- No caching (fetch fresh every time): 3 second goal becomes risky if API latency spikes
- Memory cache only: Loss on restart, no persistence for audit
- Immediate sync after booking: Over-complex, Google API eventual consistency issues

**Implementation**:
- Create `CachedCalendarSlot` model in `src/models/appointment.py`
- Add `fetch_and_cache_slots()` method to `GoogleCalendarClient` that handles DB write
- Add TTL check before API call in `appointment_service.py`

---

### 3. Timezone Handling

**Question**: How should times be stored and displayed - UTC, local, or variable?

**Context**: Spec requires "consistent timezone" (UTC storage assumed). Medical center is in single timezone. Users in Telegram may be distributed.

**Decision**: **UTC Storage, User Timezone Display (v1: UTC only)**

**Strategy for v1**:
- Store all appointment times in UTC in PostgreSQL
- Configure server to UTC: Set `TIMEZONE='UTC'` environment variable
- Display times to user in a fixed timezone (server's local timezone, typically UTC or clinic's timezone)
- Assume all users in same timezone as clinic (common for local medical practices)

**Example**:
- Clinic operates Mon-Fri 08:00-13:00 Argentine Time (ART = UTC-3)
- Store in DB: 11:00-12:00 UTC
- Display to user: "Lunes 08:00-09:00" (after offset conversion for display)

**Strategy for v2** (extensibility):
- Add `user_timezone` field to `TelegramUser` model (optional)
- Use `pytz` or `zoneinfo` to convert UTC times to user's timezone for display
- Allow clinic admin to set clinic timezone in environment: `CLINIC_TIMEZONE=America/Argentina/Buenos_Aires`

**Rationale**:
- UTC storage is database standard (avoids DST bugs, portable across servers)
- v1 assumes clinic serves local area (single timezone, common case)
- v2 supports global expansion without schema changes
- Prevents double-booking bugs from timezone confusion (all comparisons in UTC)

**Alternatives Considered**:
- Store in local timezone: Database becomes ambiguous during DST transitions
- Store with timezone info: More complex, overkill for v1 single-timezone clinic

**Implementation**:
- Add to `src/config.py`: `CLINIC_TIMEZONE = "America/Argentina/Buenos_Aires"` (configurable)
- Slot generation uses clinic timezone for business hours (08:00-13:00 interpreted in clinic time)
- Before storing: Convert clinic times to UTC via `pytz.timezone().localize()`
- On retrieval: Convert UTC back to clinic timezone for display
- Use `datetime.timezone.utc` for all DB timestamps

---

### 4. Concurrency & Double-Booking Prevention

**Question**: How to prevent two users from booking the same slot simultaneously (race condition)?

**Context**: Performance target: handle 100+ concurrent requests. Spec requires 100% double-booking prevention (SC-005).

**Decision**: **Pessimistic Locking + Unique Constraint**

**Strategy**:
1. **Database Constraints** (primary defense):
   - Add UNIQUE constraint: `(date, start_time, doctor_id)`  on `appointments` table
   - ANY duplicate attempt → database error (concurrent-safe)
   - Enforced by PostgreSQL ACID transactions

2. **Booking Workflow**:
   - Step 1: User selects slot (doesn't reserve yet)
   - Step 2: User provides reason
   - Step 3: System attempts INSERT into `appointments` table
   - Step 4a: If unique constraint violation → slot already booked, show "Turno no disponible, intenta otro"
   - Step 4b: If success → confirm appointment

3. **Validation Before Conflict**:
   - Query available slots: `SELECT * FROM cached_calendar_slots WHERE is_booked = false AND date = ... AND start_time = ...`
   - Re-check at insertion time (DB constraint catches race)
   - Optional: SELECT ... FOR UPDATE (row-level lock) to reserve before user enters reason (extra safety)

4. **Retry Logic** (for user experience):
   - If slot booking fails due to conflict, automatically refresh available slots
   - Show updated list to user: "Turno ya booked. Elige otro"

**Rationale**:
- Pessimistic locking (SELECT FOR UPDATE) prevents concurrent inserts but slows booking
- Optimistic + unique constraint: Simpler, faster, conflicts rare (100+ concurrent users ≠ 100 same-slot attempts)
- PostgreSQL ACID guarantees enforce constraint across all concurrent clients
- Scales to 100+ concurrent appointments (different slots, no conflicts)
- Meets performance (<3 sec) AND consistency requirements

**Alternatives Considered**:
- SELECT ... FOR UPDATE: Safer but slower (lock held during user reason input = 30+ seconds)
- Distributed consensus (raft, etc.): Over-engineered for single-doctor system
- Application-level mutex: Doesn't work across multiple app instances

**Implementation**:
- In `migrations/versions/002_add_appointments.py`: Add UNIQUE constraint
- In `appointment_service.py`: Wrap INSERT in try-except for `IntegrityError`
- In webhook.py: Catch and return user-friendly error if booking fails

---

### 5. Google Calendar API Rate Limiting & Error Handling

**Question**: How to handle Google Calendar API rate limits (quota exceeded) and transient failures?

**Context**: Google Calendar API: 500 requests per 100 seconds per user. Medical center books ~20-30 appointments/day, but multiple users viewing slots could spike requests.

**Decision**: **Graceful Degradation with Exponential Backoff & Cache Fallback**

**Strategy**:
1. **Rate Limit Handling**:
   - Catch `googleapiclient.errors.HttpError` with status 429 (Too Many Requests)
   - Return cached slots if available (even if expired) with warning: "Disponibilidad no actualizada. Intenta en unos minutos."
   - Log incident for monitoring
   - User still able to book from cached data (safe: doctor controls calendar)

2. **Transient Failures** (network timeout, 500s):
   - Exponential backoff: retry after 1s, 2s, 4s (max 3 attempts)
   - After 3 failures: Fall back to cached slots
   - Generic error to user: "Error al conectar con calendario. Intentando de nuevo..."

3. **Permanent Failures** (invalid credentials, 403):
   - Log error with credentials check (base64 decode valid?)
   - Return to user: "Sistema de turnos no disponible. Contacta a la secretaria."
   - Alert operator (optional: send admin notification)

4. **Monitoring** (optional v1, essential v2):
   - Track API call success rate, quota usage
   - Alert if success rate <95% for consecutive hours

**Rationale**:
- Cached slots are safe fallback (doctor-controlled, not stale user data)
- Rate limits unlikely at <240 calls/day, but graceful handling future-proof
- Exponential backoff reduces cascading failures
- Transient outages recover without user intervention

**Alternatives Considered**:
- Fail hard (HTTP 503): Bad UX, no appointment bookings during API hiccup
- No retry logic: Same problem as above
- Custom rate limiter: Adds complexity, doesn't solve Google's limits

**Implementation**:
- In `google_calendar_client.py`: Add error handling with retry decorator
- In `slot_generator.py`: Wrap API calls with try-except
- In `appointment_service.py`: Use cached slots on fallback
- Error messages in Spanish per spec

---

## Summary of Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Authentication** | Service Account (base64-encoded JSON in .env) | Simpler than OAuth, suitable for single shared calendar |
| **Slot Caching** | Database + 1-hour TTL (Redis optional v2) | <3s query time, low API usage, graceful degradation |
| **Timezone** | UTC storage + clinic timezone display (v2: user tz) | ACID safety, simple, extensible |
| **Concurrency** | UNIQUE constraint + optimistic retry | Fast, scalable, PostgreSQL-enforced consistency |
| **API Resilience** | Exponential backoff + cache fallback + graceful errors | Handles rate limits, transient failures, maintains availability |

---

## Dependencies Added (if not already present)

- `google-auth` ✅ (already in requirements.txt)
- `google-api-python-client` ✅ (already in requirements.txt)
- `pytz` (for timezone handling) - to be added if v1 needs display conversion
- `sqlalchemy >= 2.0` ✅ (already present, supports UNIQUE constraints)

---

## Next Steps (Phase 1 Design)

1. ✅ Create `data-model.md` with Appointment entity schema (UNIQUE constraint documented)
2. ✅ Create `contracts/appointment_booking.md` with API specifications
3. ✅ Create `quickstart.md` with Google Calendar setup instructions
4. ✅ Update agent context with Google Calendar patterns

