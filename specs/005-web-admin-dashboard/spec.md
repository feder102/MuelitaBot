# Feature Specification: Web Admin Dashboard

**Feature Branch**: `005-web-admin-dashboard`  
**Created**: 2026-04-17  
**Status**: Draft  
**Input**: User description: "crear un frontend dentro de la carpeta frontend usando next.js. La idea es poder acceder a los datos de la base de datos que usa el bot para poder visualizarlo en la web, ademas deberias poder escribir editar o eliminar algunos de estos datos"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Dashboard Overview (Priority: P1)

An administrator opens the web dashboard and sees a summary of the clinic's bot data: upcoming appointments and active dentists.

**Why this priority**: This is the entry point of the dashboard. Without visibility into the data, no other management action is meaningful.

**Independent Test**: Can be fully tested by opening the dashboard home page and verifying appointments and dentist records are displayed from the database.

**Acceptance Scenarios**:

1. **Given** the admin navigates to the dashboard, **When** the page loads, **Then** they see a list of all upcoming appointments with patient name, dentist, date, and status.
2. **Given** the admin navigates to the dashboard, **When** the page loads, **Then** they see a list of all registered dentists with their activity status.
3. **Given** there are no records, **When** the admin opens any section, **Then** they see an empty-state message instead of a blank screen.

---

### User Story 2 - Manage Appointments (Priority: P2)

An administrator can view the full list of appointments, see their details, and cancel or delete specific ones.

**Why this priority**: Appointments are the core operational data. Admins need to intervene when patients cannot cancel via the bot, or when records need correction.

**Independent Test**: Can be fully tested by viewing the appointments list, selecting one, performing a cancellation or deletion, and confirming the record is updated.

**Acceptance Scenarios**:

1. **Given** the admin is on the appointments page, **When** they click on an appointment, **Then** they see full details: patient, dentist, date/time, reason, and status.
2. **Given** the admin views a confirmed appointment, **When** they choose to cancel it, **Then** the appointment status changes to "cancelled" and the change is reflected immediately.
3. **Given** the admin views a cancelled appointment, **When** they choose to delete it, **Then** the record is removed and no longer appears in the list.

---

### User Story 3 - Manage Dentists (Priority: P3)

An administrator can add a new dentist, edit an existing dentist's name or calendar identifier, and deactivate or reactivate dentists.

**Why this priority**: Dentist records change infrequently, but when they do (new hire, calendar change, departure) it must be doable from the web without running scripts manually.

**Independent Test**: Can be fully tested by adding a new dentist with a name and calendar identifier, then verifying they appear in the list and are usable by the bot.

**Acceptance Scenarios**:

1. **Given** the admin is on the dentists page, **When** they fill in the name and calendar identifier and submit, **Then** a new dentist record appears in the list.
2. **Given** the admin selects an existing dentist, **When** they change the name or calendar identifier and save, **Then** the updated values are reflected immediately.
3. **Given** the admin deactivates a dentist, **When** a patient interacts with the Telegram bot, **Then** that dentist no longer appears in the booking options.

---

### User Story 4 - View Patients (Priority: P4)

An administrator can browse the registered patients (Telegram users) and view their linked appointment records.

**Why this priority**: Useful for support and audit purposes. Read-only is sufficient for v1.

**Independent Test**: Can be fully tested by navigating to the patients section and verifying each patient's name, Telegram ID, and linked appointments are displayed.

**Acceptance Scenarios**:

1. **Given** the admin is on the patients page, **When** the page loads, **Then** they see all registered patients with their name and last interaction date.
2. **Given** the admin selects a patient, **When** the detail view opens, **Then** they see all appointments associated with that patient.

---

### Edge Cases

- What happens when the admin tries to delete an appointment that was already deleted? → Show a "record not found" message and refresh the list.
- What happens when the database is unreachable? → Display a clear error banner; do not show stale data as current.
- What happens when an admin enters an invalid calendar identifier for a dentist? → Show an inline validation error before saving.
- What happens when two admins edit the same record simultaneously? → Last write wins; no locking required for v1.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The dashboard MUST display all appointments with patient name, dentist, date/time, reason, and status.
- **FR-002**: The dashboard MUST allow administrators to cancel a confirmed appointment, with explicit confirmation before executing.
- **FR-003**: The dashboard MUST allow administrators to permanently delete an appointment record, with explicit confirmation before executing.
- **FR-004**: The dashboard MUST display all dentists with their name, calendar identifier, and active/inactive status.
- **FR-005**: The dashboard MUST allow administrators to add a new dentist with a name and calendar identifier.
- **FR-006**: The dashboard MUST allow administrators to edit a dentist's name or calendar identifier.
- **FR-007**: The dashboard MUST allow administrators to deactivate or reactivate a dentist.
- **FR-008**: The dashboard MUST display all registered patients with their name and last interaction date.
- **FR-009**: The dashboard MUST allow administrators to view all appointments linked to a given patient.
- **FR-010**: The dashboard MUST require authentication via username/password stored in the system before granting access to any data. Unauthenticated requests MUST be redirected to a login page.
- **FR-011**: All data changes MUST produce immediate visible feedback (success or error message) without requiring a manual page refresh.

### Key Entities

- **Appointment**: A booking record linking a patient to a dentist at a specific date/time, with a consultation reason and a status (confirmed, cancelled).
- **Dentist**: A clinic staff record with a name, a calendar identifier used by the bot, and an active/inactive flag.
- **Patient (Telegram User)**: A person registered via the Telegram bot, identified by their Telegram ID, with a display name and last interaction timestamp.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An administrator can view the full list of appointments within 2 seconds of opening the dashboard on a standard internet connection.
- **SC-002**: An administrator can cancel or delete an appointment in under 30 seconds from opening the record.
- **SC-003**: An administrator can add or update a dentist record in under 1 minute.
- **SC-004**: 100% of write operations (cancel, delete, create, edit) produce immediate visible feedback without a manual page refresh.
- **SC-005**: Unauthorized users are redirected to the login page and cannot access any data.

## Assumptions

- The dashboard is an internal tool used only by clinic staff; it does not need to be publicly discoverable.
- A single admin role is sufficient for v1; no per-user permission levels are required.
- The dashboard communicates with the existing database through new API endpoints added to the existing backend, not via direct database access from the browser.
- Cancelling an appointment from the dashboard does NOT automatically notify the patient via Telegram in v1.
- The dashboard is desktop-first; mobile responsiveness is a nice-to-have but not required for v1.
- Audit logging of admin actions will reuse the existing audit log infrastructure.
