<!-- Sync Impact Report
Version: 1.0.0 → 1.0.0 (initial constitution)
Ratified: 2026-04-04
Sections created: Core Principles (5), Security & Compliance, Architecture & Design, Governance
This is the first constitution for turnoHector project.
-->

# turnoHector Constitution

Medical appointment management backend: simple, clean code; fast and efficient; extensible to multiple doctors and calendars; meeting highest security standards.

## Core Principles

### I. Clean Code & Simplicity

Code must prioritize clarity over cleverness. Each module should have a single, well-defined responsibility. No premature optimization or over-engineering. Complexity must be justified and documented. YAGNI principle enforced: add only what is needed now, not speculative future requirements.

**Non-negotiable**: If code is not immediately understandable to a new team member without deep investigation, it must be refactored before merge.

### II. Security-First Design

This is a medical system handling sensitive patient data. Security is not an afterthought—it is foundational.

- All patient-related data must be encrypted at rest and in transit (TLS 1.3+)
- Authentication required for all endpoints; authorization verified on every request
- No hardcoded credentials, API keys, or secrets in code or git history
- Input validation on all external data before processing
- Audit logging for all sensitive operations (appointment creation, access, modifications)
- SQL injection, XSS, CSRF, and OWASP Top 10 vulnerabilities must be actively prevented
- Dependencies vetted for known vulnerabilities (regular scanning)

### III. Performance & Scalability

The system must handle concurrent requests efficiently. Response times must remain sub-second for core operations even under load.

- Database queries optimized; no N+1 queries permitted
- Caching strategy defined for frequently accessed data (doctor availability, calendar slots)
- Horizontal scalability must be possible without code refactoring
- API endpoints document expected latency targets
- Load testing required before release to production

### IV. Test-First & Reliability

Tests are contracts between intent and implementation. TDD discipline is mandatory.

- Unit tests must cover all business logic (>80% coverage minimum)
- Integration tests required for appointment booking flows, calendar operations, multi-doctor scenarios
- Database migrations tested; rollback procedures verified
- Failing tests must block merges
- Each feature includes its test suite; they ship together

### V. Extensibility & Data Integrity

The system must cleanly support multiple doctors, calendars, and scheduling rules without code duplication or architectural strain.

- Database schema allows new doctor profiles, calendar systems, and slot definitions without migration pain
- APIs versioned; changes tracked; backward compatibility maintained or deprecation planned
- Configuration separate from code (no magic numbers or hardcoded business rules)
- Data integrity constraints enforced at database layer (foreign keys, not null, unique constraints)

## Security & Compliance

This system handles Protected Health Information (PHI) and must meet medical data protection standards.

- Passwords hashed with bcrypt or equivalent (cost ≥ 12)
- Rate limiting enforced on authentication endpoints (max 5 failed attempts → 15min lockout)
- Session tokens time-limited (1 hour max); refresh tokens separate, longer-lived
- Audit trail immutable: all data modifications logged with timestamp, user, operation type
- PII retention policy: patient data deleted when appointment expires unless legal hold
- Error messages must not leak system details to clients; log detailed errors server-side
- Regular security reviews and penetration testing recommended annually

## Architecture & Design

Medical appointment management is inherently about temporal coordination. The architecture must reflect this clearly.

- **Stateless backend**: Each request contains sufficient context; no per-request session state in memory
- **Database-as-source-of-truth**: Appointments, availability, calendars all persisted; no in-memory-only data
- **Event-driven optional**: Consider event logging for appointment lifecycle (created, modified, cancelled) to enable audit, reconciliation, future analytics
- **Doctor/Calendar abstraction**: Core entities (Doctor, Calendar, Slot, Appointment) cleanly separated; business logic not coupled to storage
- **Time zone handling**: Explicit; all datetimes stored in UTC; time zone conversions handled at API boundaries

## Development Workflow & Quality Gates

Code quality and security are not optional. Every merge must adhere to constitution.

- **Code Review**: All PRs require at least one review before merge; reviewer must verify security checklist (no secrets, no injection risks, encryption present where needed)
- **Testing Gate**: All tests must pass; coverage must not decrease; integration tests must run against real database (not mocks)
- **Security Scan**: Automated scanning for known vulnerabilities in dependencies; manual review of sensitive code paths
- **Documentation**: Every API endpoint documented (parameters, response, error codes); security assumptions documented in README or ARCHITECTURE.md
- **Commit Discipline**: Meaningful commit messages; each commit represents a logical unit; no "WIP" commits to main

## Governance

**Constitution Authority**: This constitution supersedes all other practices and guidelines. When practices conflict, constitution wins. Any deviation requires amendment.

**Amendment Process**:
1. Proposed change documented with rationale
2. Discussion & team consensus (security & architecture leads review)
3. Constitution updated; version bumped (semantic versioning)
4. Existing codebase assessed for migration plan (breaking changes require time-bound deadline)
5. All affected templates and documentation updated

**Versioning Policy**:
- MAJOR: Principle removal or redefinition; breaking change to development workflow
- MINOR: New principle added; security requirement added; existing principle clarified
- PATCH: Typo, wording clarification, example updates

**Compliance Review**: Monthly check that recent merged code aligns with constitution; flag violations in review; remediate within sprint.

**Version**: 1.0.0 | **Ratified**: 2026-04-04 | **Last Amended**: 2026-04-04
