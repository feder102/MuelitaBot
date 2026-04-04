# Feature Specification: Appointment Booking with Google Calendar

**Feature Branch**: `002-appointment-booking`  
**Created**: 2026-04-04  
**Status**: Draft  
**Input**: User description: "Vamos a gestionar el flujo 1 del menu, si el cliente ingresa el numero 1 del menu debe ser posible buscar los eventos disponibles de un calendario de google, credenciales cargadas en .env_template y de esta forma traerles los eventos disponibles que van de lunes a viernes de 08:00 a 13:00 horas donde cada evento es de 1 hora y el usuario selecciona el evento a registrarse indicando un motivo de la consulta"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Display Available Appointment Slots (Priority: P1)

A user selects option 1 ("Solicitar turno") from the main menu. The system connects to Google Calendar, retrieves available time slots, and displays them to the user with clear formatting. Each slot is a 1-hour appointment from Monday to Friday, 08:00 to 13:00.

**Why this priority**: This is the core appointment booking functionality. Without displaying available slots, users cannot book appointments. This is the foundation of the entire booking flow.

**Independent Test**: Can be fully tested by selecting menu option 1 and verifying the system fetches and displays available appointment slots. Delivers immediate user value by showing what times are available.

**Acceptance Scenarios**:

1. **Given** a user selects "Solicitar turno" from the menu, **When** the system queries the Google Calendar, **Then** the system displays all available 1-hour slots between 08:00 and 13:00, Monday through Friday
2. **Given** the Google Calendar has available slots, **When** the system formats the response, **Then** each slot is displayed with date (day of week), time range (e.g., "Lunes 08:00-09:00"), and a selection number
3. **Given** the system retrieves calendar data, **When** there are no available slots, **Then** the system displays a message indicating no appointments are available and offers to contact the secretary
4. **Given** a user views the appointment list, **When** the slots are displayed, **Then** the list includes only Monday-Friday slots within business hours (08:00-13:00)

---

### User Story 2 - User Selects Appointment and Provides Reason (Priority: P1)

A user selects an available time slot by entering the corresponding number. The system acknowledges the selection and prompts the user to provide the reason for the appointment (motivo de la consulta). The reason is captured and stored for later reference.

**Why this priority**: This is essential for completing the appointment booking flow. The reason for the visit is critical medical information needed for the doctor. Collecting this ensures complete appointment information.

**Independent Test**: Can be fully tested by selecting an appointment slot and providing a reason. Verifies that the system correctly captures and stores both the time selection and the consultation reason.

**Acceptance Scenarios**:

1. **Given** appointment slots are displayed to the user, **When** the user sends a number corresponding to a slot (e.g., "1" for first slot), **Then** the system acknowledges the selection and prompts for the consultation reason
2. **Given** the system has received a time selection, **When** it prompts for a reason, **Then** the message clearly instructs the user to describe why they need the appointment (in Spanish)
3. **Given** the user provides a reason, **When** the system receives the message, **Then** the reason is captured and linked to the selected time slot
4. **Given** a user selects an invalid option (not in the list), **When** the system receives the input, **Then** the system displays the appointment list again and asks for a valid selection

---

### User Story 3 - Appointment Confirmation and Storage (Priority: P2)

After the user provides a reason, the system confirms the appointment booking, displays a summary (time, reason), and stores the appointment record for the doctor's reference. The user receives confirmation.

**Why this priority**: Confirmation is important for user experience and record-keeping, but the core booking happens before this. It's secondary to capturing the appointment details.

**Independent Test**: Can be tested by completing appointment selection and reason entry, then verifying confirmation is displayed and stored in the system.

**Acceptance Scenarios**:

1. **Given** a user has selected a time and provided a reason, **When** the system processes the information, **Then** a confirmation message is displayed with the appointment details (date, time, reason)
2. **Given** appointment information is complete, **When** the system stores it, **Then** the appointment is saved for the doctor to review
3. **Given** an appointment is booked, **When** the confirmation is shown, **Then** the user is offered options to return to the menu or contact the secretary if needed

---

### Edge Cases

- What happens if the Google Calendar credentials are invalid or expired?
- How does the system handle if Google Calendar is unreachable (network error)?
- What happens if a user tries to book an appointment for a time that's no longer available (concurrent bookings)?
- How does the system handle if a user provides an empty reason (just whitespace)?
- What if the user takes too long to respond and the conversation times out?
- How does the system handle special characters or very long reason text (e.g., >1000 characters)?
- What if all slots for a day are booked and only one doctor is available?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST connect to Google Calendar using credentials stored in environment variables
- **FR-002**: System MUST retrieve available time slots from the configured calendar
- **FR-003**: System MUST filter available slots to only show Monday-Friday, 08:00-13:00 time ranges
- **FR-004**: System MUST generate 1-hour time slots (08:00-09:00, 09:00-10:00, etc.)
- **FR-005**: System MUST display available slots in human-readable format in Spanish
- **FR-006**: System MUST recognize user appointment selection (by number)
- **FR-007**: System MUST prompt user for appointment reason (motivo de la consulta)
- **FR-008**: System MUST validate that the reason is not empty and maximum 150 characters
- **FR-009**: System MUST store appointment details (date, time, reason, created_by_user_id, created_by_phone) for doctor reference
- **FR-010**: System MUST capture and store the user ID or phone number of the staff member who creates the appointment
- **FR-011**: System MUST maintain conversation context to track booking progress
- **FR-012**: System MUST handle Google Calendar API errors gracefully and inform the user
- **FR-013**: System MUST prevent double-booking (same time cannot be booked twice)
- **FR-014**: System MUST convert calendar times to user's local timezone (or UTC consistent)
- **FR-015**: System MUST provide confirmation of booked appointment

### Key Entities *(include if feature involves data)*

- **Appointment**: Represents a booked appointment with fields: id, patient_user_id (Telegram user), date, time_start, time_end, reason (max 150 chars), created_by_user_id, created_by_phone, created_at, status
- **AvailableSlot**: Represents an available time slot from Google Calendar with fields: date, start_time, end_time, is_available
- **CalendarCredentials**: Stores Google Calendar API credentials (service account or OAuth) from environment
- **AppointmentRequest**: User's appointment booking request containing: patient_user_id, selected_slot, consultation_reason (150 chars max), created_by_user_id, created_by_phone

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: System retrieves and displays available appointments within 3 seconds of user requesting them
- **SC-002**: 100% of available Monday-Friday 08:00-13:00 slots from Google Calendar are correctly displayed to the user
- **SC-003**: 95% of users successfully complete appointment booking (select slot + provide reason) on first or second attempt
- **SC-004**: All appointment details (time and reason) are accurately stored and retrievable
- **SC-005**: System prevents double-booking: same time slot cannot be reserved twice
- **SC-006**: 100% of user-provided reasons are captured and linked to the correct appointment
- **SC-007**: Invalid menu selections (out of range numbers) are handled gracefully with re-display of options
- **SC-008**: Google Calendar API errors result in user-friendly error messages (not technical errors)

## Assumptions

- Google Calendar API credentials (service account or OAuth) will be securely provided via environment variables
- The medical center uses Google Calendar to manage appointment availability
- Appointments are always 1-hour duration (no variable-length appointments in v1)
- Business hours are fixed: Monday-Friday, 08:00-13:00 (no holidays or special hours in v1)
- All times are stored and displayed in a single timezone (server timezone or UTC)
- One doctor/calendar is used (no multi-doctor scheduling complexity in v1)
- Users have Spanish language preference (responses in Spanish)
- Appointment bookings are confirmed immediately (no admin approval required)
- Appointment reason (motivo de la consulta) is limited to 150 characters maximum
- Staff member creating the appointment must provide either their user ID or phone number (for service/admin tracking)
- Doctor will review pending appointments in a separate admin interface (not part of this feature)
- The system tracks who created the appointment (staff/service user) separately from who the appointment is for (patient/Telegram user)
