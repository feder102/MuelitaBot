# Quickstart: Cancel Appointment Implementation

**Feature**: 004-cancel-appointment  
**Date**: 2026-04-12

This guide gives a developer all the context needed to implement the feature without re-reading the full spec.

---

## What This Feature Does

Adds a "3️⃣ Cancelar turno" option to the main Telegram bot menu. When selected, the bot shows the patient their upcoming appointments (future only), lets them pick one, asks for confirmation, then marks it `CANCELLED` in the DB and deletes the corresponding Google Calendar event.

---

## Files to Create

| File | Purpose |
|------|---------|
| `src/services/cancellation_router.py` | New state-machine handler for the cancellation flow |
| `migrations/versions/<hash>_add_google_event_id_and_cancel_states.py` | Alembic migration |
| `tests/unit/test_cancellation_router.py` | Unit tests for CancellationRouter |
| `tests/integration/test_cancel_appointment_flow.py` | End-to-end cancellation flow test |

---

## Files to Modify

| File | What Changes |
|------|-------------|
| `src/models/appointment.py` | Add `google_event_id = Column(String(255), nullable=True, index=True)` |
| `src/models/conversation_state.py` | Add `SELECTING_CANCELLATION_APPOINTMENT` and `AWAITING_CANCELLATION_CONFIRMATION` to `ConversationStateEnum` |
| `src/services/google_calendar_client.py` | Add `async delete_event(calendar_id, event_id)` method |
| `src/services/appointment_service.py` | Save `google_event_id` to `Appointment` after `create_event()` |
| `src/services/webhook_handler.py` | Add routing branches for the two new states; wire option "3" |
| `src/services/menu_router.py` | Add option 3 to menu text and routing |
| `src/services/message_parser.py` | Recognize "3", "cancelar turno", "si", "sí", "no", "volver" |

---

## Implementation Order

1. **DB schema** — `appointment.py` + `conversation_state.py` + Alembic migration (run & verify)
2. **Google Calendar delete** — `google_calendar_client.py` (add `delete_event`)
3. **Fix event ID storage** — `appointment_service.py` (save `google_event_id` after create)
4. **CancellationRouter** — new service; implement the 3-step flow
5. **MessageParser + MenuRouter** — add option 3 recognition and menu text
6. **WebhookHandler** — wire new states to CancellationRouter
7. **Tests** — unit + integration

---

## CancellationRouter Interface

```python
class CancellationRouter:
    def __init__(self, db: AsyncSession, telegram_client: TelegramClient,
                 calendar_client: GoogleCalendarClient,
                 conversation_manager: ConversationManager): ...

    async def handle_cancellation_request(self, user: TelegramUser, chat_id: int) -> None:
        """
        Entry point when user selects option 3.
        - Queries upcoming PENDING appointments for user.
        - If none: sends empty-state message, resets state to AWAITING_MENU.
        - If one or more: stores list in context_data, sends numbered list,
          sets state to SELECTING_CANCELLATION_APPOINTMENT.
        """

    async def validate_appointment_selection(self, user: TelegramUser,
                                              chat_id: int, text: str) -> None:
        """
        Called when state == SELECTING_CANCELLATION_APPOINTMENT.
        - Parses text as integer index into context_data list.
        - Invalid: sends error, keeps state.
        - Valid: stores selected appointment in context_data,
          sends confirmation prompt, sets state to AWAITING_CANCELLATION_CONFIRMATION.
        """

    async def confirm_and_cancel_appointment(self, user: TelegramUser,
                                              chat_id: int, text: str) -> None:
        """
        Called when state == AWAITING_CANCELLATION_CONFIRMATION.
        - "si": executes cancellation (DB update + calendar delete), confirms to user.
        - "no": discards, returns to menu.
        - Other: sends clarification prompt, keeps state.
        """
```

---

## WebhookHandler Routing Additions

```python
# In WebhookHandler._route_by_state() (or equivalent):

elif state == ConversationStateEnum.AWAITING_MENU and selection == "3":
    await cancellation_router.handle_cancellation_request(user, chat_id)

elif state == ConversationStateEnum.SELECTING_CANCELLATION_APPOINTMENT:
    await cancellation_router.validate_appointment_selection(user, chat_id, text)

elif state == ConversationStateEnum.AWAITING_CANCELLATION_CONFIRMATION:
    await cancellation_router.confirm_and_cancel_appointment(user, chat_id, text)
```

---

## Appointment Query (fetch upcoming)

```python
from sqlalchemy import select, and_
from sqlalchemy.orm import joinedload
from datetime import date, datetime, timezone

now = datetime.now(timezone.utc)
result = await db.execute(
    select(Appointment)
    .options(joinedload(Appointment.dentist))
    .where(
        and_(
            Appointment.patient_user_id == user.id,
            Appointment.status == AppointmentStatusEnum.PENDING,
            # Future-only filter
            (Appointment.appointment_date > now.date()) |
            (
                (Appointment.appointment_date == now.date()) &
                (Appointment.start_time > now.time())
            )
        )
    )
    .order_by(Appointment.appointment_date, Appointment.start_time)
)
appointments = result.scalars().all()
```

---

## Cancellation Execution (DB + Calendar)

```python
# 1. Re-verify ownership and status in a single UPDATE (atomic guard)
result = await db.execute(
    update(Appointment)
    .where(
        Appointment.id == appointment_id,
        Appointment.patient_user_id == user.id,
        Appointment.status == AppointmentStatusEnum.PENDING,
    )
    .values(status=AppointmentStatusEnum.CANCELLED)
    .returning(Appointment.google_event_id, Appointment.dentist_id)
)
row = result.first()
if row is None:
    # Already cancelled or not owned by user
    await telegram_client.send_message(chat_id, ERROR_MESSAGE)
    return

# 2. Delete from Google Calendar (best-effort)
if row.google_event_id:
    dentist = await dentist_service.get_by_id(row.dentist_id)
    await calendar_client.delete_event(dentist.calendar_id, row.google_event_id)
else:
    logger.warning("No google_event_id for appointment %s; skipping calendar delete", appointment_id)

# 3. Audit log
await audit_log_service.log(user_id=user.id, action="APPOINTMENT_CANCELLED",
                             details={"appointment_id": str(appointment_id)})
```

---

## Constitution Checklist (for implementer)

- [ ] No N+1 queries — use `joinedload(Appointment.dentist)` when fetching the list
- [ ] Ownership double-checked in UPDATE WHERE clause (not just in application logic)
- [ ] Audit log entry written for every successful cancellation
- [ ] Input validated before processing (numeric index bounds, confirmation text)
- [ ] Error messages in Spanish, no internal details exposed to user
- [ ] All datetimes compared in UTC
- [ ] Unit tests cover: empty list, single appointment, multiple appointments, invalid selection, already-cancelled race condition
- [ ] Integration tests run against real database (no mocks per constitution)
- [ ] `google_event_id` save added to `appointment_service.book_appointment()` before this feature ships
