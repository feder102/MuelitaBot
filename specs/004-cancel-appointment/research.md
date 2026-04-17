# Research: Cancel Appointment

**Phase**: 0 — Research  
**Date**: 2026-04-12  
**Feature**: 004-cancel-appointment

---

## Decision 1: Patient Identity for Cancellation Validation

**Decision**: Use `TelegramUser.telegram_user_id` (Telegram's numeric user ID) as the patient identifier.

**Rationale**: This field is already captured at first contact, stored in `telegram_users.telegram_user_id` (BigInteger, UNIQUE), and linked to every appointment via `Appointment.patient_user_id → TelegramUser.id`. The spec mentioned phone number as an option, but no phone number is stored in the current schema. Using the Telegram user ID is sufficient, already enforced, and requires no new data collection.

**Alternatives considered**:
- Phone number: Not stored in current schema; would require a new prompt in the booking flow and a schema migration — out of scope for this feature.
- Separate PIN or passcode: Over-engineered for a Telegram bot where the channel itself authenticates the sender.

---

## Decision 2: Google Calendar Event ID Storage

**Decision**: Add a `google_event_id` (String, nullable, indexed) column to the `Appointment` model and save the calendar event ID at booking time.

**Rationale**: The current `appointment_service.book_appointment()` receives the event ID from Google Calendar after creation but discards it (only logs it). Without storing the event ID, there is no reliable way to delete the corresponding Google Calendar event at cancellation time. Querying the calendar by date/time is fragile and requires extra API calls. Storing the ID at creation is the clean, single-lookup solution.

**Alternatives considered**:
- Query Google Calendar by appointment date/time to find and delete the event: Requires a list + filter round-trip, is error-prone if events were manually moved, and breaks the "no extra API calls" principle.
- Store event ID in `context_data` JSON: Not durable — context is cleared after booking completion.

**Migration impact**: One Alembic migration adding a nullable String column to `appointments`. Existing rows will have `NULL` for this field; cancellation of such appointments will skip the calendar delete step with a logged warning.

---

## Decision 3: New Conversation States

**Decision**: Add two new states to `ConversationStateEnum`:
- `SELECTING_CANCELLATION_APPOINTMENT` — patient is viewing their upcoming appointment list and picking one to cancel.
- `AWAITING_CANCELLATION_CONFIRMATION` — patient has selected an appointment and the system is waiting for yes/no confirmation.

**Rationale**: Mirrors the existing booking flow pattern (`SELECTING_DENTIST` → `AWAITING_SLOT_SELECTION` → `AWAITING_REASON_TEXT`). Each state maps to one distinct user action, keeping the `WebhookHandler` routing table clear and testable. Context data for the flow (list of appointments, selected appointment ID) is stored in `ConversationState.context_data` JSON field, consistent with the booking flow.

**Alternatives considered**:
- Single state for the entire cancellation flow: Collapses two distinct user decisions (select + confirm) into one state, making routing and testing more complex.
- Inline the cancellation flow in `AppointmentRouter`: Violates single-responsibility; cancellation is a different domain operation from booking.

---

## Decision 4: New Service Class — CancellationRouter

**Decision**: Create a new `CancellationRouter` class in `src/services/cancellation_router.py`, following the same pattern as `AppointmentRouter`.

**Rationale**: `AppointmentRouter` handles the booking flow state machine. A symmetric `CancellationRouter` keeps concerns separated, is independently testable, and avoids bloating `AppointmentRouter` with cancellation logic.

**Responsibilities**:
1. `handle_cancellation_request()` — fetch upcoming appointments for the patient, store in context, show numbered list or empty-state message.
2. `validate_appointment_selection()` — validate the patient's numeric selection, update context with selected appointment ID.
3. `confirm_and_cancel_appointment()` — on confirmation: mark appointment as CANCELLED in DB, delete Google Calendar event, log audit entry, return success message.

---

## Decision 5: Google Calendar Delete Method

**Decision**: Add `delete_event(calendar_id: str, event_id: str)` to `GoogleCalendarClient`.

**Rationale**: The client currently has `create_event()` and `get_all_slots()` but no deletion method. Adding it to the same client keeps all Google Calendar interactions in one place, consistent with existing architecture.

**Behavior**:
- Calls `service.events().delete(calendarId=calendar_id, eventId=event_id).execute()`
- Catches `HttpError 404` (event already deleted) and logs a warning without raising.
- Raises on other HTTP errors (let the router handle retry/user messaging).

---

## Decision 6: Menu Option Numbering

**Decision**: Add "3️⃣ Cancelar turno" as option 3 in the main menu.

**Rationale**: Natural extension of the existing 2-option menu. Option 1 = book, Option 2 = secretary, Option 3 = cancel is intuitive and sequential. `MessageParser` already recognizes numeric inputs; extending to "3" is minimal.

**Alternatives considered**:
- Re-use option 2 slot and rename: Would break the secretary flow; not needed since there is no hard limit on menu items.
- Dynamic menu (show cancel only if user has appointments): Adds complexity to the menu-rendering step for marginal UX gain; keep it simple.

---

## Decision 7: Cancellation — DB Status Update

**Decision**: Set `Appointment.status = CANCELLED` (using the existing `AppointmentStatusEnum.CANCELLED`) rather than hard-deleting the row.

**Rationale**: Constitution requires an immutable audit trail. Hard-deleting appointment rows destroys history. The `CANCELLED` status already exists in the enum; no schema change needed for this decision. Audit logging of the cancellation event is added via `AuditLog`.

**Appointments shown in cancellation list**: Only rows with `status = PENDING` and `appointment_date/start_time` in the future are shown. This naturally excludes already-cancelled appointments.

---

## Decision 8: Handling Missing google_event_id (Existing Appointments)

**Decision**: If `appointment.google_event_id` is `NULL` (booked before this migration), skip the Google Calendar delete and log a warning. The DB cancellation still proceeds.

**Rationale**: Existing appointments have no stored event ID. Failing the entire cancellation operation for this reason would be a poor UX. A logged warning is sufficient; the clinic admin can clean the calendar manually for the rare case of a pre-migration cancellation.
