# Service Contract: Dentist Selection Flow

**Feature**: 003-multi-dentist-booking | **Interface**: Telegram Bot Message Flow | **Date**: 2026-04-05

## Contract Overview

This document defines the Telegram bot message interface for dentist selection in the appointment booking flow. It specifies the exact messages, options, and state transitions users and the system go through.

---

## Interface: Telegram Bot Messages

### Flow Diagram

```
User selects "1 - Solicitar Turno" (Appointment)
         ↓
System checks number of active dentists
         ↓
      ┌──────────────────────────────┐
      │ 0 dentists available         │ 1 dentist available          │ 2+ dentists available
      │ (error)                      │ (auto-select)               │ (show selection menu)
      ↓                              ↓                               ↓
Error message                   Auto-select dentist         Show numbered list
"No dentists available"         Set step_context            "Which dentist?"
Contact secretary               Show slots immediately      "1. Hector"
                                                           "2. Fulano"
                                                           "3. ..."
                                                                ↓
                                                           User sends "1", "2", etc.
                                                                ↓
                                                           Validate selection
                                                                ↓
                                                           Set selected_dentist_id
                                                           Show slots for selected dentist
```

---

## Message Contracts

### 1. Menu Response (existing, unchanged)

**Trigger**: User types `/start` or "0" (menu)

**System Message** (Spanish):
```
Bienvenido a turnoHector!

¿Qué deseas hacer?

1. Solicitar Turno
2. Secretaria
```

**State After**: `current_step` = `MENU`

---

### 2. Appointment Option Selected - No Dentists

**Trigger**: User types "1" AND `get_active_dentists()` returns empty list

**System Message** (Spanish):
```
Lo sentimos, no hay doctores disponibles en este momento.
Por favor, contacta a nuestra secretaria para más información.

¿Deseas volver al menú? (Si/No)
```

**State After**: `current_step` = `MENU` (return to menu or loop on secretary contact)

**Error Code**: `DENTIST_LIST_EMPTY`

---

### 3a. Appointment Option Selected - Single Dentist (Auto-Select)

**Trigger**: User types "1" AND `get_active_dentists()` returns exactly 1 dentist

**System Message** (Spanish):
```
Buscando horarios disponibles con {dentist_name}...
```

**State After**: 
- `current_step` = `WAITING_FOR_APPOINTMENT`
- `step_context.selected_dentist_id` = <dentist_uuid>
- Transitions immediately to slot display (no user input required)

**UX Note**: User is not aware of auto-selection; experience is identical to old single-dentist flow.

---

### 3b. Appointment Option Selected - Multiple Dentists (Show Menu)

**Trigger**: User types "1" AND `get_active_dentists()` returns 2+ dentists

**System Message** (Spanish):
```
¿A qué odontólogo deseas pedir turno?

1. Hector
2. Fulano
[3. ... if more dentists exist]
```

**State After**: 
- `current_step` = `SELECTING_DENTIST`
- `step_context` = `{available_dentists: [<dentist_id_1>, <dentist_id_2>, ...]}`

**Valid User Inputs**: "1", "2", "3", etc. (number corresponding to dentist in list)

---

### 4. Invalid Dentist Selection

**Trigger**: User types non-numeric input, out-of-range number, or invalid format while in `SELECTING_DENTIST` state

**System Message** (Spanish):
```
Opción inválida. Por favor, selecciona un número válido.

¿A qué odontólogo deseas pedir turno?

1. Hector
2. Fulano
```

**State After**: `current_step` = `SELECTING_DENTIST` (repeat menu)

**Error Code**: `INVALID_DENTIST_SELECTION`

---

### 5. Valid Dentist Selection

**Trigger**: User types valid number (e.g., "1") while in `SELECTING_DENTIST` state

**System Message** (Spanish):
```
Buscando horarios disponibles con {selected_dentist_name}...
```

**State After**:
- `current_step` = `WAITING_FOR_APPOINTMENT`
- `step_context.selected_dentist_id` = <dentist_uuid>
- Transitions immediately to slot display

**State Transition**: `SELECTING_DENTIST` → `WAITING_FOR_APPOINTMENT`

---

### 6. Dentist Becomes Inactive During Selection

**Trigger**: Dentist marked `active_status = FALSE` while user is viewing selection menu (edge case)

**System Message** (Spanish):
```
El odontólogo seleccionado ya no está disponible. 

Por favor, selecciona otro odontólogo.

¿A qué odontólogo deseas pedir turno?

1. Hector
```

**State After**: `current_step` = `SELECTING_DENTIST` (refresh menu)

**Error Code**: `DENTIST_UNAVAILABLE`

**Implementation Note**: Validate dentist still active before transitioning to `WAITING_FOR_APPOINTMENT`.

---

### 7. Slot Display (existing, now with dentist context)

**Trigger**: After dentist selection, system displays available slots

**System Message** (Spanish, example):
```
Horarios disponibles con Hector:

1. Lunes, 08:00 - 09:00
2. Lunes, 09:00 - 10:00
3. Martes, 08:00 - 09:00
[...]

¿Cuál prefieres?
```

**State After**: 
- `current_step` = `WAITING_FOR_APPOINTMENT`
- `step_context` = `{selected_dentist_id: <uuid>, available_slots: [...]}`

**UX Note**: Dentist name is displayed to confirm selection.

---

### 8. Appointment Confirmation (existing, extended)

**Trigger**: User selects slot AND provides reason

**System Message** (Spanish, example):
```
✓ Turno confirmado con Hector

Fecha: Lunes, 08:00 - 09:00
Motivo: Limpieza dental

Tu turno ha sido registrado. ¡Gracias!

¿Deseas volver al menú? (Si/No)
```

**State After**: 
- `current_step` = `MENU` or `WAITING_FOR_ACTION`
- Appointment created in DB with `dentist_id`

---

## State Machine

```
┌─────────────────────────────────────────────────────────┐
│                      MENU                               │
│  (User types "1" for appointment or "2" for secretary)  │
└──────────────────────┬──────────────────────────────────┘
                       │ (User selects "1")
                       ↓
        ┌──────────────────────────────┐
        │ Check active dentist count   │
        └──────┬─────────────┬─────────┘
               │             │
          0    │             │  1 or 2+
         ┌─────┘             └──────┐
         ↓                          ↓
    ERROR_MESSAGE            ┌──────────────────┐
    (no dentists)            │ 1 dentist:       │
    Back to MENU          AUTO-SELECT   │ 2+ dentists:
                           ↓             │ SELECTING_DENTIST
                    ┌─────────────┐      │ (wait for input)
                    │ Set         │      └──────┬───────┐
                    │ dentist_id  │             │       │
                    └──────┬──────┘             │       │
                           │                   ↓       │
         ┌─────────────────┘            Invalid    Valid
         │                             Selection  Selection
         │                                │           │
         └─────────────────┬─────────────┘           │
                           │                       ┌─┘
                           ↓                       ↓
                    ┌─────────────────┐       ┌──────────────┐
                    │ WAITING_FOR     │       │ Set dentist  │
                    │ APPOINTMENT     │◄──────│ in context   │
                    │ (show slots)    │       └──────────────┘
                    └────────┬────────┘
                             │
                    ┌────────┴────────┐
                    │ (User selects   │
                    │  slot & reason) │
                    ↓                 ↓
              CONFIRMATION    ERROR/RETRY
                    │              │
                    └──────┬───────┘
                           ↓
                        MENU

```

---

## Data Contracts

### Request: Dentist Selection

**Type**: User message (string)

**Valid Values**: "1", "2", "3", ... (numeric string matching list position)

**Invalid Values**: "", "abc", "0", "-1", "100" (out of range), etc.

---

### Response: Available Dentists List

**Type**: Telegram message (text)

**Format**:
```
¿A qué odontólogo deseas pedir turno?

1. Hector
2. Fulano
```

**Data Payload** (internal):
```json
{
  "available_dentists": [
    {"id": "uuid-1", "name": "Hector"},
    {"id": "uuid-2", "name": "Fulano"}
  ]
}
```

---

### Response: Appointment Confirmation

**Type**: Telegram message (text)

**Format**:
```
✓ Turno confirmado con {dentist_name}

Fecha: {date_formatted}
Motivo: {reason}

Tu turno ha sido registrado. ¡Gracias!
```

**Database Payload**:
```python
appointment = Appointment(
    id=<uuid>,
    patient_user_id=<user_id>,
    dentist_id=<selected_dentist_id>,  # NEW
    appointment_date=<date>,
    start_time=<time>,
    reason=<reason>,
    status="PENDING",
    created_at=<now>,
    updated_at=<now>
)
```

---

## Error Codes & Handling

| Error Code | HTTP/Condition | User Message | Action |
|-----------|---|---|---|
| `DENTIST_LIST_EMPTY` | 0 active dentists | "No dentists available" | Return to MENU |
| `INVALID_DENTIST_SELECTION` | Input doesn't match list | "Invalid option" | Repeat SELECTING_DENTIST menu |
| `DENTIST_UNAVAILABLE` | Dentist became inactive | "Selected dentist unavailable" | Refresh menu or retry |
| `GOOGLE_CALENDAR_ERROR` | Calendar API unreachable | "Unable to fetch slots. Retry or contact secretary" | Offer retry + fallback |
| `DUPLICATE_BOOKING` | Slot already booked (race condition) | "Slot no longer available. Choose another" | Refresh slots & retry |

---

## Backward Compatibility

**Single-Dentist Clinic Behavior** (when only 1 dentist active):
- User selects "1" (appointment)
- System auto-selects the single dentist
- **No dentist selection menu is shown**
- User sees slot display immediately (identical to Feature 002)
- `selected_dentist_id` is set internally but user is unaware

**Multi-Dentist Clinic Behavior** (when 2+ dentists active):
- User selects "1" (appointment)
- System shows dentist selection menu
- User selects dentist (new step)
- User sees slot display for selected dentist

**Result**: Existing single-dentist deployments require zero UX changes. Multi-dentist deployments introduce new selection step.

---

## Testing Contract

**Test Scenario 1**: Zero dentists
```
User: "1" (appointment)
Bot: "No dentists available..."
User: "0" (menu)
Expected: Return to MENU state
```

**Test Scenario 2**: One dentist
```
User: "1" (appointment)
Bot: "Buscando horarios..." (immediately shows slots)
Expected: Auto-selection, no menu shown
```

**Test Scenario 3**: Multiple dentists
```
User: "1" (appointment)
Bot: "1. Hector\n2. Fulano"
User: "1"
Bot: "Buscando horarios con Hector..."
Expected: selected_dentist_id = hector_uuid, transition to slots
```

**Test Scenario 4**: Invalid dentist selection
```
User: "1" (appointment)
Bot: "1. Hector\n2. Fulano"
User: "5" (out of range)
Bot: "Opción inválida...\n1. Hector\n2. Fulano"
Expected: Repeat menu, no state change
```

---

## Localization Notes

All messages shown above are in Spanish (es-AR dialect). For future multi-language support:
- Message templates should be externalized to `i18n/` directory
- `dentist.name` should be UI-agnostic (no language in database)
- Message formatting should respect locale (dates, numbers)

---

## Performance Considerations

**Dentist List Query**:
- Should be cached in-app (refresh every 5 minutes or on dentist change)
- Reduces DB queries during high booking volume
- Cache key: `active_dentists_list`

**Slot Display**:
- Uses existing Google Calendar API calls (no performance regression)
- `dentist_id` parameter passed to GoogleCalendarClient
- Single API call per dentist, not one per user

---

## Related Documentation

- **Data Model**: [../data-model.md](../data-model.md)
- **Implementation**: [../quickstart.md](../quickstart.md)
- **Specification**: [../spec.md](../spec.md)
