# Contract: Telegram Webhook Interface

**Version**: 1.0.0
**Created**: 2026-04-04
**Purpose**: Define the HTTP interface for receiving updates from Telegram Bot API

---

## Endpoint Specification

### HTTP Details

| Item | Value |
|------|-------|
| Method | POST |
| Path | /webhook |
| Protocol | HTTPS (TLS 1.3+) |
| Content-Type (request) | application/json |
| Content-Type (response) | application/json |

### Security

- **Signature validation**: REQUIRED
  - Header: `X-Telegram-Bot-API-Secret-SHA256`
  - Value: Hex-encoded HMAC-SHA256 of request body
  - Algorithm: HMAC_SHA256(bot_token, raw_request_body)
  - Failure handling: Return 403 Forbidden, do not process request
  - Log: Record failed signature attempts in audit_log

---

## Request Contract

### Headers (Required)

```
Content-Type: application/json
X-Telegram-Bot-API-Secret-SHA256: <hex-signature>
```

### Body Schema (Telegram Update Object)

Pydantic model:

```python
from telegram import Update  # From python-telegram-bot library

class WebhookRequest(BaseModel):
    update_id: int  # Unique identifier for this update
    message: Optional[Message] = None
    
class Message(BaseModel):
    message_id: int
    date: int  # Unix timestamp
    chat: Chat
    text: Optional[str] = None
    
class Chat(BaseModel):
    id: int  # Telegram user ID (can be negative for groups; we only handle private chats)
    type: str  # "private", "group", "supergroup", "channel"
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
```

### Example Valid Request

```json
{
  "update_id": 987654321,
  "message": {
    "message_id": 42,
    "date": 1712234400,
    "chat": {
      "id": 123456789,
      "type": "private",
      "first_name": "Juan",
      "last_name": "Pérez",
      "username": "juanperez"
    },
    "text": "Hola"
  }
}
```

### Validation Rules

- **update_id**: integer > 0 (required)
- **message**: object (required if message update)
- **message.message_id**: integer > 0
- **message.date**: Unix timestamp (integer)
- **message.chat.id**: integer ≠ 0 (can be negative for groups)
- **message.chat.type**: one of ["private", "group", "supergroup", "channel"]
- **message.chat.first_name**: string, not empty
- **message.text**: string or null
  - If null: not a text message (ignore photo/video/etc.)
  - If present: 1–4096 characters (Telegram limit)

### Processing Rules

1. **Validate signature**
   - If invalid → 403 Forbidden (do not process)
   
2. **Extract user and message**
   - Create or update TelegramUser from chat object
   - Parse message.text
   
3. **State lookup**
   - Query ConversationState for this user
   - If no state exists → create new with AWAITING_MENU
   
4. **Route action**
   - If text is "1", "opción 1", etc. → route to appointment handler
   - If text is "2", "opción 2", etc. → route to secretary handler
   - Otherwise → display menu again
   
5. **Log audit entry**
   - Insert into audit_log: action, status, message_text, response_text

---

## Response Contract

### Success Response (200 OK)

```json
{
  "ok": true
}
```

**Meaning**: Webhook was processed successfully. The bot will send a reply message to the user separately via the Telegram Bot API (not via this response).

### Validation Failure Response (403 Forbidden)

```json
{
  "ok": false,
  "error_code": 403,
  "description": "Invalid signature"
}
```

**Meaning**: Signature validation failed. Request ignored, no processing. Request logged for security review.

### Server Error Response (5xx)

```json
{
  "ok": false,
  "error_code": 500,
  "description": "Internal server error"
}
```

**Meaning**: Unexpected error (DB unavailable, crash, etc.). Request logged with error details. Telegram will retry.

---

## Response Format (JSON Schema)

```json
{
  "type": "object",
  "properties": {
    "ok": {
      "type": "boolean",
      "description": "Whether the request was successful"
    },
    "error_code": {
      "type": "integer",
      "description": "HTTP status code (200, 403, 500, etc.)"
    },
    "description": {
      "type": "string",
      "description": "Human-readable error message (if applicable)"
    }
  },
  "required": ["ok"]
}
```

---

## User-Facing Message Contract

After processing the webhook, the bot sends a message back to the Telegram user. This is NOT part of the webhook response; it's a separate API call from the bot to Telegram.

### Message Scenarios

#### Scenario 1: First-time user or AWAITING_MENU state

**Bot sends**:
```
Bienvenido 👋

Selecciona una opción:
1️⃣ Solicitar turno
2️⃣ Hablar con secretaria
```

**Telegram user sees**: Menu with numbered options

#### Scenario 2: User selects option 1

**User sends**: "1"  
**Bot sends**:
```
Entendido. Solicitar turno 📅

Por favor, espera mientras te conectamos...
```

**State update**: current_state = APPOINTMENT_SELECTED

#### Scenario 3: User selects option 2

**User sends**: "2"  
**Bot sends**:
```
Conectando con secretaria 📞

Un momento por favor...
```

**State update**: current_state = SECRETARY_SELECTED

#### Scenario 4: Invalid selection

**User sends**: "help"  
**Bot sends**:
```
No entiendo esa opción. 

Selecciona una opción:
1️⃣ Solicitar turno
2️⃣ Hablar con secretaria
```

**State update**: No state change (remains AWAITING_SELECTION)

---

## Error Handling Contract

### Signature Validation Fails

```
HTTP 403 Forbidden
Body: {"ok": false, "error_code": 403, "description": "Invalid signature"}
Audit log: action=SIGNATURE_VALIDATION_FAILED, status=VALIDATION_FAILED, user_id=null
```

### Database Unavailable

```
HTTP 500 Internal Server Error
Body: {"ok": false, "error_code": 500, "description": "Service temporarily unavailable"}
Audit log: action=DATABASE_ERROR, status=ERROR, user_id=null (or known user), error_detail="Connection pool exhausted"
```

### Malformed JSON

```
HTTP 400 Bad Request
Body: {"ok": false, "error_code": 400, "description": "Invalid request body"}
Audit log: action=WEBHOOK_RECEIVED, status=VALIDATION_FAILED, user_id=null
```

### Telegram API Rate Limit (when sending reply)

```
HTTP 200 OK  (webhook itself accepted)
Body: {"ok": true}
Audit log: action=TELEGRAM_API_ERROR, status=ERROR, error_detail="Rate limited by Telegram"
(Telegram will retry the webhook later)
```

---

## Retry Behavior

### Telegram's retry logic

- Telegram will retry failed webhooks (non-200 responses) up to 25 times
- Backoff strategy: exponential (Telegram decides)
- Max retry period: ~1 week

### Our handling

- **Idempotency**: Webhook with same update_id should produce same result
- **Deduplication**: Check if update_id already processed in audit_log before reprocessing
- **Logging**: Always log webhook receipt (even if duplicate) for audit trail

### Duplicate handling

```sql
-- Check if we've seen this update before
SELECT COUNT(*) FROM audit_log 
WHERE action = 'WEBHOOK_RECEIVED' 
  AND message_text LIKE '%update_id' -- (or store update_id separately)
```

If duplicate detected:
- Log as redundant receipt
- Return 200 OK (acknowledge to Telegram)
- Do not re-process (prevents duplicate messages to user)

---

## Rate Limiting

### Inbound (webhook from Telegram)

- No explicit rate limit (Telegram sends webhooks at user message rate, which is implicitly limited)
- Our concern: Handle 100+ concurrent webhooks
- Solution: Async/await handles concurrency; DB connection pool prevents exhaustion

### Outbound (bot replies to Telegram)

- Telegram's limit: ~30 messages per second per bot
- Our solution: Queue replies if needed (future optimization)
- Current: Send synchronously; if rate limited, Telegram returns error, we log and retry

---

## Testing Contract

### Contract Test Cases (pytest)

```python
def test_valid_webhook():
    # Given: Valid webhook with signature
    # When: POST /webhook
    # Then: 200 OK, {"ok": true}
    
def test_invalid_signature():
    # Given: Webhook with invalid signature
    # When: POST /webhook
    # Then: 403 Forbidden
    
def test_menu_selection():
    # Given: Webhook with text="1"
    # When: POST /webhook
    # Then: 200 OK, state updated to APPOINTMENT_SELECTED
    
def test_invalid_menu_selection():
    # Given: Webhook with text="invalid"
    # When: POST /webhook
    # Then: 200 OK, menu re-displayed, state unchanged
    
def test_concurrent_webhooks():
    # Given: 100 concurrent webhooks from different users
    # When: POST /webhook (all parallel)
    # Then: All 200 OK, each user has correct state, no cross-contamination
```

### Integration Test Cases

- Webhook received → message logged → response sent
- User state transitions (AWAITING_MENU → APPOINTMENT_SELECTED)
- Database transaction consistency under load
- Audit logging completeness

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-04-04 | Initial contract (menu selection for appointment and secretary) |

---

## Future Enhancements (Out of Scope v1)

- Interactive inline buttons (Telegram ReplyKeyboardMarkup) instead of text parsing
- Message deduplication via message_id tracking
- User preferences storage (language, timezone)
- Webhook batching (multiple updates per request)
- Webhook timeout (current: Telegram default ~25s)
