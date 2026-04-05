# Feature Specification: Multi-Dentist Appointment Booking

**Feature Branch**: `003-multi-dentist-booking`  
**Created**: 2026-04-05  
**Status**: Draft  
**Input**: El proximo spec consiste en soportar el bot para multiples calendarios, es decir multiples doctores, hoy solo el flujo funciona para un calendario. El bot al lanzar el menu, solicita dos opciones, 1 turno, 2 secretaria, cuando selecciona 1, debe preguntar para que odontologo quiere pedir turno, si para Hector o para FUlano, hector tiene su propio calendar_id y fulano, tiene su propio calendar_id, esto debe ser escalable.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Appointment Booking with Dentist Selection (Priority: P1)

A patient opens the appointment booking bot, selects option 1 (appointment), and is presented with a list of available dentists. They select their preferred dentist (e.g., Hector or Fulano) and proceed to book an appointment in that dentist's calendar.

**Why this priority**: This is the core functionality that differentiates this feature from the existing single-calendar implementation. It's the primary value proposition - patients can now choose which dentist to book with.

**Independent Test**: Can be fully tested by having a patient complete the appointment booking flow with dentist selection and verifying the appointment appears in the correct dentist's calendar.

**Acceptance Scenarios**:

1. **Given** the bot menu is displayed, **When** the user selects option 1 (appointment), **Then** the bot asks which dentist they want to book with and displays all available dentists
2. **Given** the user has selected a dentist, **When** they proceed with the appointment booking flow, **Then** the appointment is created in that specific dentist's calendar
3. **Given** multiple appointments are booked with different dentists, **When** each dentist checks their calendar, **Then** each sees only their own appointments

---

### User Story 2 - Secretary Multi-Calendar Management (Priority: P2)

A secretary or administrator can manage appointments across all dentist calendars through the bot. When selecting option 2 (secretary), they can view, modify, or manage appointments for any dentist.

**Why this priority**: Important for workflow efficiency but secondary to the core patient-facing appointment booking. Allows staff to manage the system.

**Independent Test**: Can be fully tested by having a secretary access the secretary menu and verify they can interact with appointments across multiple dentist calendars.

**Acceptance Scenarios**:

1. **Given** the bot menu is displayed, **When** the secretary selects option 2 (secretary), **Then** they access administrative functionality
2. **Given** the secretary is in admin mode, **When** they interact with appointment management, **Then** they can manage appointments for all dentists

---

### User Story 3 - Scalable Dentist Configuration (Priority: P3)

The system maintains a configurable list of dentists and their associated Google Calendar IDs. New dentists can be added or removed from the system without modifying bot code, supporting business growth and changes.

**Why this priority**: Ensures long-term maintainability and scalability. Enables the business to easily expand to new dentists or manage dentist roster changes.

**Independent Test**: Can be fully tested by verifying dentist information can be added, updated, or removed from the system and immediately appears/disappears from the bot menu.

**Acceptance Scenarios**:

1. **Given** the system is configured with dentists, **When** a new dentist is added to the configuration, **Then** the bot menu immediately displays them as a booking option
2. **Given** a dentist is removed from the configuration, **When** the bot is queried, **Then** that dentist no longer appears as a booking option
3. **Given** a dentist's calendar_id is updated, **When** users book with that dentist, **Then** appointments are created in the updated calendar

---

### Edge Cases

- What happens when the dentist list is empty? (System should gracefully inform users no dentists are available)
- How does the system handle a dentist's calendar_id being invalid or unreachable? (Appointment booking should fail with user-friendly error message)
- What if two users simultaneously try to book the same time slot with the same dentist? (System should handle booking conflict gracefully, following existing appointment booking logic)
- What happens when a dentist is removed while a user is in the middle of booking with them? (User should receive a notification that the dentist is no longer available)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST store and maintain a configurable list of dentists with their associated Google Calendar IDs
- **FR-002**: System MUST display the list of available dentists when a user selects option 1 (appointment) from the bot menu
- **FR-003**: Users MUST be able to select a specific dentist from the displayed list
- **FR-004**: System MUST use the selected dentist's calendar_id when creating appointments
- **FR-005**: System MUST verify that a selected dentist is still available before proceeding with appointment booking
- **FR-006**: System MUST support adding new dentists and their calendar IDs to the configuration without code changes
- **FR-007**: System MUST support removing dentists from the configuration
- **FR-008**: System MUST handle cases where appointment booking fails for a specific dentist (e.g., calendar unreachable) with appropriate error messages
- **FR-009**: Secretary option (option 2) MUST work with the multi-dentist system for appointment management
- **FR-010**: System MUST preserve existing single-calendar appointment booking logic and extend it for multiple calendars

### Key Entities

- **Dentist**: Represents a dental professional with a name and associated Google Calendar ID. Attributes: dentist_name, calendar_id, active_status
- **Appointment**: Booking record linked to a specific Dentist's calendar. Relationships: belongs to a specific Dentist's calendar
- **Dentist Configuration**: Data structure storing the mapping of dentists to their calendar IDs. Can be updated dynamically without code deployment

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can select from available dentists and complete an appointment booking within the existing average booking time (same as single-dentist flow)
- **SC-002**: System correctly routes appointments to the selected dentist's calendar with 100% accuracy
- **SC-003**: New dentists can be added to the system and appear in the bot menu within 5 minutes (accounting for cache refresh)
- **SC-004**: System maintains backward compatibility - existing single-dentist flows continue to work without modification
- **SC-005**: Appointment booking succeeds for all dentists in the system on first attempt 95% of the time
- **SC-006**: The dentist selection menu is intuitive and requires no additional user training

## Assumptions

- Each dentist has a dedicated Google Calendar with a unique calendar_id (existing pattern from single-calendar implementation)
- Dentist configuration will be stored in a database/config system that can be queried at runtime (not hardcoded)
- The existing Google Calendar API integration will continue to work for multiple calendar_ids without modification
- User selection of dentist is the only required change to the current appointment booking flow
- The secretary functionality (option 2) will be handled in a separate feature or extends naturally from the existing implementation
- The system has access to a list/database of active dentists and their calendar_ids at runtime
- No authentication changes are needed - users continue to authenticate the same way
- SMS/Telegram notifications continue to work as before, specifying which dentist's appointment was booked
