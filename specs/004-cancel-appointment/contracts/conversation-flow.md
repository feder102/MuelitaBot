# Contract: Cancellation Conversation Flow

**Type**: Telegram Bot Conversation State Machine  
**Feature**: 004-cancel-appointment  
**Date**: 2026-04-12

---

## State Transitions

```
AWAITING_MENU
    │
    │ user sends "3" / "cancelar turno"
    ▼
SELECTING_CANCELLATION_APPOINTMENT
    │                          │
    │ user sends valid          │ user has no
    │ appointment number        │ upcoming appointments
    ▼                          ▼
AWAITING_CANCELLATION_CONFIRMATION    AWAITING_MENU
    │             │
    │ "si"        │ "no" / "cancelar"
    ▼             ▼
AWAITING_MENU  AWAITING_MENU
```

---

## Message Contracts

### Trigger: User selects "3" from main menu

**System response (appointments found)**:
```
Tus turnos próximos:

1️⃣ Hector — Lunes 20 de abril a las 10:00
2️⃣ Fulano — Sábado 3 de mayo a las 14:00

¿Cuál turno querés cancelar? Respondé con el número.
```

**System response (no upcoming appointments)**:
```
No tenés turnos próximos para cancelar.
```
→ State returns to `AWAITING_MENU`, main menu re-displayed.

---

### Trigger: User sends appointment number (e.g., "1")

**Validation rules**:
- Must be a positive integer within the range `[1, N]` where N = number of appointments shown.
- Non-numeric or out-of-range input → error message, state stays `SELECTING_CANCELLATION_APPOINTMENT`.

**Error response**:
```
Selección inválida. Por favor respondé con un número entre 1 y {N}.
```

**System response (valid selection)**:
```
Confirmás que querés cancelar el siguiente turno?

📅 Hector — Lunes 20 de abril a las 10:00

Respondé *si* para confirmar o *no* para volver al menú.
```
→ State moves to `AWAITING_CANCELLATION_CONFIRMATION`.

---

### Trigger: User sends "si" (confirmation)

**Validation**: Case-insensitive; accept "si", "sí", "yes".

**System response (success)**:
```
✅ Tu turno del lunes 20 de abril a las 10:00 con Hector fue cancelado exitosamente.
```
→ State returns to `AWAITING_MENU`, main menu re-displayed.

**System response (failure — appointment already cancelled or not found)**:
```
No se pudo cancelar el turno. Es posible que ya haya sido cancelado. Si necesitás ayuda, contactá a la secretaria.
```
→ State returns to `AWAITING_MENU`.

---

### Trigger: User sends "no" (abort)

**Validation**: Case-insensitive; accept "no", "cancelar", "volver".

**System response**:
```
Cancelación descartada. Volvés al menú principal.
```
→ State returns to `AWAITING_MENU`, main menu re-displayed.

---

### Trigger: Unexpected input during cancellation flow

**System response** (at `SELECTING_CANCELLATION_APPOINTMENT`):
```
Por favor respondé con el número del turno que querés cancelar, o volvé al menú con /menu.
```

**System response** (at `AWAITING_CANCELLATION_CONFIRMATION`):
```
Por favor respondé *si* para confirmar la cancelación o *no* para volver al menú.
```

---

## Main Menu Update

**Current**:
```
Bienvenido 👋

Selecciona una opción:
1️⃣ Solicitar turno
2️⃣ Hablar con secretaria
```

**Updated**:
```
Bienvenido 👋

Selecciona una opción:
1️⃣ Solicitar turno
2️⃣ Hablar con secretaria
3️⃣ Cancelar turno
```

---

## MessageParser Additions

| Input Tokens | Normalized Output |
|---|---|
| `"3"` | `"3"` |
| `"cancelar turno"` | `"3"` |
| `"cancelar"` (at menu state) | `"3"` |
| `"si"`, `"sí"`, `"yes"` | `"si"` |
| `"no"`, `"volver"` | `"no"` |
