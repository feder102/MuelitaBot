# Feature Specification: Cancel Appointment

**Feature Branch**: `004-cancel-appointment`  
**Created**: 2026-04-12  
**Status**: Draft  
**Input**: User description: "Vamos a crear una nueva opcion en el menu que permita cancelar un turno al paciente, para esto debera mostrarle el turno o los turnos que tiene asociado en el calendario, obviamente que con fecha vigente no de turnos que pasaron, para poder seleccionar el turno que quiere cancelar, para esto deberas comprabar que el paciente que escribe sea el mismo que reservo, podes usar tu numero de telefono su identificador, lo que sea necesario para validar esto"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cancel Single Upcoming Appointment (Priority: P1)

A patient who has one upcoming appointment selects "Cancel Appointment" from the main menu. The system identifies the patient by their unique messaging identifier (phone number), retrieves their upcoming appointment, and asks them to confirm the cancellation. Upon confirmation, the appointment is removed from the calendar.

**Why this priority**: This is the core use case — a patient needs to cancel their own appointment without calling the clinic. It delivers immediate value and covers the most common scenario.

**Independent Test**: Can be fully tested by a patient with exactly one future appointment selecting the cancel option and confirming — delivers full cancellation capability as an MVP.

**Acceptance Scenarios**:

1. **Given** a patient has one upcoming appointment and selects "Cancel Appointment", **When** the system retrieves their identity and fetches their appointments, **Then** the system displays the appointment details (date, time, dentist) and asks for confirmation.
2. **Given** the appointment is displayed and the patient confirms cancellation, **When** the confirmation is received, **Then** the appointment is removed from the calendar and the patient receives a success message.
3. **Given** the patient selects cancel but then chooses not to confirm, **When** the patient declines the confirmation prompt, **Then** the appointment is kept and the patient is returned to the main menu.

---

### User Story 2 - Select and Cancel One of Multiple Appointments (Priority: P2)

A patient who has two or more upcoming appointments selects "Cancel Appointment" from the menu. The system displays a list of all their future appointments, the patient selects the one they want to cancel, and then confirms the cancellation.

**Why this priority**: Patients with multiple appointments need the ability to choose which specific appointment to cancel. Without this, the feature is incomplete for repeat patients.

**Independent Test**: Can be tested by a patient with 2+ future appointments going through the full selection and cancellation flow — verifies list display, selection, and cancellation.

**Acceptance Scenarios**:

1. **Given** a patient has two or more upcoming appointments, **When** they select "Cancel Appointment", **Then** the system shows a numbered or labeled list of all upcoming appointments (date, time, dentist) for the patient to choose from.
2. **Given** the list is shown, **When** the patient selects a specific appointment, **Then** the system displays that appointment's details and asks for confirmation before cancelling.
3. **Given** the patient confirms, **When** the cancellation is processed, **Then** only the selected appointment is removed; all other appointments remain intact.

---

### User Story 3 - No Upcoming Appointments (Priority: P3)

A patient selects "Cancel Appointment" from the menu but has no future appointments associated with their identity.

**Why this priority**: Graceful handling of the empty state prevents confusion and improves user experience.

**Independent Test**: Testable by a patient with no future appointments triggering the cancellation flow — verifies that a clear informational message is shown.

**Acceptance Scenarios**:

1. **Given** a patient has no upcoming appointments, **When** they select "Cancel Appointment", **Then** the system displays a friendly message indicating they have no upcoming appointments to cancel.
2. **Given** the empty-state message is shown, **When** the patient reads it, **Then** they are offered a way to return to the main menu.

---

### Edge Cases

- What happens when a patient's messaging identity does not match any appointment in the system?
- How does the system handle an appointment scheduled for today — can it still be cancelled if the time has not yet passed?
- What happens if the cancellation fails on the calendar side (e.g., connectivity issue)?
- How does the system behave if a patient sends an out-of-sequence message during the cancellation flow (e.g., free text instead of selecting an option)?
- What happens if a patient tries to cancel the same appointment twice (already cancelled)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The main menu MUST include a "Cancel Appointment" option visible to all patients.
- **FR-002**: The system MUST identify each patient uniquely using their messaging identity (phone number or messaging platform user ID) — no additional login required.
- **FR-003**: The system MUST retrieve only future appointments (strictly after the current date and time) for the identified patient; past appointments MUST NOT appear in the list.
- **FR-004**: The system MUST display each upcoming appointment with at minimum: date, time, and dentist name — so the patient can clearly identify which appointment to cancel.
- **FR-005**: When a patient has more than one upcoming appointment, the system MUST present a selection interface allowing the patient to choose exactly one appointment to cancel.
- **FR-006**: The system MUST present a confirmation step before executing any cancellation, clearly stating which appointment will be removed.
- **FR-007**: Upon confirmed cancellation, the system MUST remove the appointment from the relevant calendar entry.
- **FR-008**: The system MUST NOT allow a patient to view or cancel an appointment that belongs to a different patient — identity validation is mandatory before showing any appointment data.
- **FR-009**: The system MUST provide a way to abort the cancellation and return to the main menu at any point in the flow.
- **FR-010**: After successful cancellation, the system MUST confirm the outcome to the patient with a clear success message.
- **FR-011**: If no upcoming appointments exist for the patient, the system MUST display an informational message and NOT show an empty or broken list.

### Key Entities

- **Patient**: The person interacting with the system; uniquely identified by their messaging identity (phone number or platform user ID). Has zero or more appointments.
- **Appointment**: A scheduled visit with a specific dentist at a specific date and time. Belongs to exactly one patient and one dentist. Has a status (active, cancelled).
- **Dentist**: The professional associated with the appointment. Each appointment references one dentist.
- **Calendar Entry**: The external calendar record corresponding to an appointment. Cancelling an appointment must be reflected in the calendar.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A patient can complete the full cancellation flow (from menu selection to confirmation message) in under 2 minutes.
- **SC-002**: 100% of appointments shown to a patient belong exclusively to that patient — no cross-patient data exposure.
- **SC-003**: 100% of cancelled appointments are correctly removed from the calendar with no orphaned records.
- **SC-004**: No appointments with a past date or time appear in the cancellation list — 0% false positives for expired appointments.
- **SC-005**: Patients with no upcoming appointments receive a clear informational message — 0 cases of blank or error screens for this state.
- **SC-006**: The cancellation flow can be abandoned at any step without altering any appointment data.

## Assumptions

- The patient's unique messaging identity (phone number or platform user ID) is already captured at booking time and stored alongside the appointment record.
- A patient may have appointments with different dentists; all their future appointments across all dentists are shown in the cancellation list.
- Cancellation is immediate — there is no "pending cancellation" state or clinic approval step required.
- Same-day cancellations are permitted as long as the appointment time has not yet passed.
- The cancellation menu option is accessible from the same main menu used for booking.
- Notification to the dentist or clinic staff about a cancellation is out of scope for this feature.
- The system does not require a reason for cancellation — patients can cancel without explanation.
