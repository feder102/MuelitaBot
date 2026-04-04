# Feature Specification: Telegram Webhook Menu Backend

**Feature Branch**: `001-webhook-menu`  
**Created**: 2026-04-04  
**Status**: Draft  
**Input**: User description: "Debes crear un backend en fastApi que permita mostrarle al usuario de telegram o whatsapp (feature mas adelante) un menu, ejemplo: 1: Solicitar turno, 2: Hablar con secretaria. pensaba en un endpoint POST /webhook"

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - User Receives Menu From Bot (Priority: P1)

A user sends a message to the Telegram bot. The bot acknowledges the message and displays an interactive menu with numbered options. The user can see two clear options: requesting an appointment or speaking with the secretary.

**Why this priority**: This is the core MVP functionality. Without this, the bot cannot interact with users. This is the foundation all other features depend on.

**Independent Test**: Can be fully tested by sending a message to the bot and verifying the menu response is returned with correct formatting. Delivers immediate user engagement and demonstrates the bot's core capability.

**Acceptance Scenarios**:

1. **Given** a user starts a conversation with the Telegram bot, **When** the user sends any initial message, **Then** the bot responds with a welcome message and displays a numbered menu (1: Solicitar turno, 2: Hablar con secretaria)
2. **Given** the bot receives a webhook from Telegram, **When** the webhook signature is valid and contains a text message, **Then** the bot parses the message and prepares a menu response
3. **Given** the bot has prepared a menu response, **When** it sends the response back to Telegram, **Then** the message is delivered to the user with proper formatting and all menu options visible

---

### User Story 2 - User Selects Appointment Request (Priority: P2)

A user selects option 1 ("Solicitar turno") from the menu. The system acknowledges the selection and begins the appointment request flow, confirming that the appointment module is ready to handle the request.

**Why this priority**: Appointment requests are the primary use case for a medical center. This is the most valuable user flow for the business. It must work before secretary contact flow.

**Independent Test**: Can be fully tested by selecting menu option 1 and verifying the system acknowledges the selection and is ready to process appointment details. Delivers core business value.

**Acceptance Scenarios**:

1. **Given** the menu is displayed to the user, **When** the user sends "1" or selects option 1, **Then** the system recognizes the selection and confirms it (e.g., "Entendido. Solicitar turno.")
2. **Given** the user has selected appointment request, **When** the system processes the selection, **Then** the system is ready to collect appointment details (or transitions to the appointment booking module)
3. **Given** the system receives an invalid menu selection, **When** the user sends a message that doesn't match menu options, **Then** the system re-displays the menu and asks the user to select a valid option

---

### User Story 3 - User Selects Secretary Contact (Priority: P3)

A user selects option 2 ("Hablar con secretaria") from the menu. The system acknowledges the selection and provides contact information or initiates a secretary chat flow.

**Why this priority**: Secretary contact is a secondary path. It provides an escape route for users who can't or don't want to use the automated appointment system. Important but less critical than the appointment flow.

**Independent Test**: Can be fully tested by selecting menu option 2 and verifying the system acknowledges the selection and provides next steps. Delivers user support capability.

**Acceptance Scenarios**:

1. **Given** the menu is displayed to the user, **When** the user sends "2" or selects option 2, **Then** the system recognizes the selection and confirms it (e.g., "Conectando con secretaria...")
2. **Given** the user has selected secretary contact, **When** the system processes the selection, **Then** the system provides secretary contact information or indicates secretary availability/queue status
3. **Given** multiple users simultaneously select menu options, **When** the system processes each selection, **Then** each user receives the appropriate response for their selection without cross-contamination

### Edge Cases

- What happens when a user sends a message with special characters, emojis, or non-ASCII text?
- How does the system handle rapid consecutive messages from the same user within seconds?
- What happens if the Telegram webhook signature validation fails (security breach attempt)?
- How does the system respond if the database is temporarily unavailable when trying to record the user's menu selection?
- What happens if the bot receives a webhook from an unexpected Telegram user (not in system, new user)?
- How does the system handle messages that are longer than expected or contain multiple menu selections in one message?

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: System MUST receive incoming webhooks from Telegram at the POST `/webhook` endpoint
- **FR-002**: System MUST validate the webhook signature from Telegram to ensure authenticity and prevent unauthorized requests
- **FR-003**: System MUST parse incoming Telegram messages and extract the user ID and message content
- **FR-004**: System MUST respond to incoming messages by sending back a formatted menu with numbered options (1: Solicitar turno, 2: Hablar con secretaria)
- **FR-005**: System MUST recognize when a user selects an option (sends "1" or "2" or equivalent)
- **FR-006**: System MUST route the user to the appropriate flow based on their menu selection (appointment request flow or secretary contact flow)
- **FR-007**: System MUST maintain conversation context for each user across multiple messages
- **FR-008**: System MUST log all incoming messages and user interactions for audit and debugging purposes
- **FR-009**: System MUST handle user messages that do not match menu options by re-displaying the menu
- **FR-010**: System MUST support multiple concurrent conversations with different users without interference

### Key Entities *(include if feature involves data)*

- **User**: A Telegram user identified by their Telegram user ID, with conversation history and current menu state
- **Message**: An incoming message from Telegram containing user ID, message text, timestamp, and message ID
- **WebhookRequest**: The POST request from Telegram containing update information, user message, and cryptographic signature
- **MenuSelection**: A user's choice from the displayed menu (appointment request or secretary contact)
- **ConversationState**: The current state of a user's conversation (awaiting menu selection, appointment flow in progress, secretary flow in progress, etc.)

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: Bot responds to user messages within 2 seconds of receiving the webhook
- **SC-002**: 100% of valid Telegram webhooks are successfully processed and users receive the menu
- **SC-003**: Menu displays correctly in Telegram app with both options clearly visible and readable
- **SC-004**: 95% of users successfully select a menu option on their first or second attempt
- **SC-005**: All webhook requests with invalid signatures are rejected without being processed
- **SC-006**: System maintains separate conversation state for 100+ concurrent users without data loss
- **SC-007**: Appointment and secretary flows correctly route 100% of menu selections to their respective handlers

## Assumptions

- Telegram Bot API will be used for initial implementation (WhatsApp integration deferred to future feature)
- Users have a valid Telegram account and stable internet connectivity
- Telegram bot token is securely stored and accessible to the backend (environment variable)
- Webhook signature validation uses Telegram's standard HMAC-SHA256 algorithm
- Menu options are simple text responses (not interactive buttons in v1; can enhance in future)
- User context (appointment history, preferences) will be looked up from the existing medical center database when needed
- Message format is plain text (no rich media handling required for v1)
- Responses should be in Spanish (per user's description)
- The appointment request flow and secretary contact flow are implemented separately; this feature only handles routing to them
