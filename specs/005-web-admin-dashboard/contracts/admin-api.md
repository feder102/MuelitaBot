# Admin API Contract (005)

Base path: `/admin`  
All endpoints require a valid session cookie (`Authorization` via HttpOnly JWT cookie).  
All responses: `Content-Type: application/json`.  
All timestamps: ISO 8601 UTC.

---

## Authentication

### POST /admin/auth/login
Login with username and password.

**Request**:
```json
{ "username": "admin", "password": "secret" }
```

**Response 200**: Sets `session` HttpOnly cookie (JWT, 1h expiry).
```json
{ "ok": true, "username": "admin" }
```

**Response 401**:
```json
{ "ok": false, "error": "Invalid credentials" }
```

**Response 429** (rate limit — 5 failed attempts):
```json
{ "ok": false, "error": "Too many attempts. Try again in 15 minutes." }
```

---

### POST /admin/auth/logout
Clear session cookie.

**Response 200**:
```json
{ "ok": true }
```

---

### GET /admin/auth/me
Return current admin identity.

**Response 200**:
```json
{ "username": "admin" }
```

**Response 401**: No/expired cookie.

---

## Appointments

### GET /admin/appointments
List all appointments, newest first.

**Query params**: `status` (optional: `confirmed` | `cancelled`), `page` (default 1), `page_size` (default 50, max 200).

**Response 200**:
```json
{
  "items": [
    {
      "id": "uuid",
      "patient": { "id": "uuid", "first_name": "Juan", "last_name": "Pérez", "telegram_user_id": 123456 },
      "dentist": { "id": "uuid", "name": "Hector" },
      "slot_date": "2026-05-10",
      "start_time": "09:00",
      "end_time": "09:30",
      "reason": "Consulta de rutina",
      "status": "confirmed",
      "created_at": "2026-04-17T10:00:00Z"
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 50
}
```

---

### GET /admin/appointments/{id}
Get single appointment detail.

**Response 200**: Same shape as single item above.  
**Response 404**: `{ "error": "Not found" }`

---

### PATCH /admin/appointments/{id}/cancel
Cancel a confirmed appointment.

**Response 200**:
```json
{ "ok": true, "id": "uuid", "status": "cancelled" }
```

**Response 409** (already cancelled):
```json
{ "ok": false, "error": "Appointment is already cancelled" }
```

---

### DELETE /admin/appointments/{id}
Permanently delete an appointment record.

**Response 200**:
```json
{ "ok": true }
```

**Response 404**: `{ "error": "Not found" }`

---

## Dentists

### GET /admin/dentists
List all dentists.

**Response 200**:
```json
{
  "items": [
    { "id": "uuid", "name": "Hector", "calendar_id": "hector@clinic.cal.google.com", "active_status": true, "created_at": "..." }
  ]
}
```

---

### POST /admin/dentists
Create a new dentist.

**Request**:
```json
{ "name": "Dr. García", "calendar_id": "garcia@clinic.cal.google.com" }
```

**Response 201**:
```json
{ "id": "uuid", "name": "Dr. García", "calendar_id": "garcia@clinic.cal.google.com", "active_status": true }
```

**Response 422**: Validation error (missing field, duplicate name/calendar_id).

---

### PATCH /admin/dentists/{id}
Update dentist fields (partial update).

**Request** (any subset):
```json
{ "name": "Dr. García Nuevo", "calendar_id": "...", "active_status": false }
```

**Response 200**: Updated dentist object.  
**Response 404**: Not found.

---

## Patients

### GET /admin/patients
List all registered patients, newest first.

**Query params**: `page`, `page_size`.

**Response 200**:
```json
{
  "items": [
    {
      "id": "uuid",
      "telegram_user_id": 123456,
      "first_name": "Juan",
      "last_name": "Pérez",
      "username": "juanp",
      "last_interaction": "2026-04-15T09:00:00Z"
    }
  ],
  "total": 150
}
```

---

### GET /admin/patients/{id}
Get patient detail with their appointments.

**Response 200**:
```json
{
  "id": "uuid",
  "telegram_user_id": 123456,
  "first_name": "Juan",
  "last_name": "Pérez",
  "username": "juanp",
  "appointments": [ /* same shape as appointment list items */ ]
}
```

---

## Error Format (all endpoints)

```json
{ "ok": false, "error": "Human-readable message" }
```

HTTP status codes: 200 success, 201 created, 400 bad request, 401 unauthorized, 404 not found, 409 conflict, 422 validation error, 429 rate limited, 500 server error.
