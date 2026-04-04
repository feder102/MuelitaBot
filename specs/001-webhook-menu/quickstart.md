# Quick Start: Telegram Webhook Menu Backend

**Goal**: Get the webhook server running locally and test it with Telegram in under 15 minutes.

---

## Prerequisites

- Python 3.11+ (verify: `python3 --version`)
- pip (verify: `pip --version`)
- Docker + Docker Compose (for PostgreSQL)
- Telegram account with a registered bot token (from BotFather)

---

## Step 1: Get a Telegram Bot Token (5 minutes)

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Follow prompts:
   - Bot name: "turnoHector-dev" (or your choice)
   - Bot username: "turnohectordev_bot" (must end with "_bot", must be unique)
4. Copy the bot token provided (example: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)
5. Save this token; you'll need it for `.env` file

---

## Step 2: Clone / Set Up Project (2 minutes)

Assuming you have the repo cloned:

```bash
cd /path/to/turnoHector
git checkout 001-webhook-menu  # or your current branch
```

---

## Step 3: Create Environment Variables (1 minute)

Create `.env` file in repo root:

```bash
cat > .env << 'EOF'
# Telegram Bot
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN_HERE
TELEGRAM_BOT_WEBHOOK_SECRET=your-secret-key-here-min-32-chars

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/turnohector
DATABASE_NAME=turnohector
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# API
API_HOST=0.0.0.0
API_PORT=8000
API_ENV=development

# Logging
LOG_LEVEL=INFO
EOF
```

**Replace**:
- `YOUR_BOT_TOKEN_HERE`: Paste your token from Step 1
- `your-secret-key-here-min-32-chars`: Pick a random 32+ character secret (e.g., `$(python3 -c 'import secrets; print(secrets.token_hex(32))')`)

---

## Step 4: Start PostgreSQL with Docker Compose (2 minutes)

Create `docker-compose.yml` in repo root (if not already present):

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: turnohector-postgres
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: turnohector
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

Start PostgreSQL:

```bash
docker-compose up -d postgres
# Wait for health check: ~10 seconds
docker-compose ps  # Should show "healthy"
```

---

## Step 5: Install Python Dependencies (2 minutes)

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

**If `requirements.txt` doesn't exist yet**, install manually:

```bash
pip install fastapi==0.104.0
pip install uvicorn[standard]==0.24.0
pip install python-telegram-bot==20.3
pip install sqlalchemy==2.0.23
pip install asyncpg==0.29.0
pip install pydantic==2.4.0
pip install pydantic-settings==2.0.0
pip install python-dotenv==1.0.0
pip install alembic==1.12.0
pip install pytest==7.4.0
pip install pytest-asyncio==0.21.0
pip install httpx==0.25.0
```

---

## Step 6: Run Database Migrations (1 minute)

```bash
# Create initial migration
alembic upgrade head

# Verify tables created
psql -h localhost -U postgres -d turnohector -c "
  SELECT table_name FROM information_schema.tables 
  WHERE table_schema = 'public';"
```

Expected output: `telegram_users`, `conversation_state`, `audit_log`

---

## Step 7: Start the API Server (1 minute)

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

API docs available at: **http://localhost:8000/docs** (interactive Swagger UI)

---

## Step 8: Test Locally (without Telegram) (3 minutes)

In a new terminal:

```bash
# Test webhook endpoint (will fail signature validation, as expected)
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"update_id": 1, "message": {"message_id": 1, "date": 1234567890, "chat": {"id": 12345, "type": "private", "first_name": "Test"}, "text": "Hola"}}'

# Expected: 403 Forbidden (invalid signature) → Good! Security working.
```

To test with valid signature:

```bash
# Generate signature (requires bot token)
python3 -c "
import hmac
import hashlib
import json

body = '{\"update_id\": 1, \"message\": {\"message_id\": 1, \"date\": 1234567890, \"chat\": {\"id\": 12345, \"type\": \"private\", \"first_name\": \"Test\"}, \"text\": \"Hola\"}}'
token = 'YOUR_BOT_TOKEN_HERE'
secret = token.encode()
signature = hmac.new(secret, body.encode(), hashlib.sha256).hexdigest()
print(f'X-Telegram-Bot-API-Secret-SHA256: {signature}')
"

# Use the signature in the request:
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-API-Secret-SHA256: <SIGNATURE_FROM_ABOVE>" \
  -d '{...}'

# Expected: 200 OK, menu displayed
```

---

## Step 9: Test with Real Telegram Bot (2 minutes)

### Option A: Local Tunnel (ngrok)

If webhook isn't yet set up:

```bash
# Download ngrok: https://ngrok.com/
ngrok http 8000

# Copy the forwarding URL (example: https://1234-56-78-90-123.ngrok.io)
```

### Set Telegram Webhook

```bash
python3 << 'EOF'
import requests

BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
WEBHOOK_URL = "https://your-ngrok-url.ngrok.io/webhook"
SECRET = "your-secret-key-here-min-32-chars"

url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
data = {
    "url": WEBHOOK_URL,
    "secret_token": SECRET,
    "allowed_updates": ["message"]
}

response = requests.post(url, json=data)
print(response.json())  # Should show "ok": true
EOF
```

### Send Test Message to Bot

1. Open Telegram
2. Search for your bot: `@turnohectordev_bot` (or your username from Step 1)
3. Send message: `Hola`
4. Expected bot response:
   ```
   Bienvenido 👋
   
   Selecciona una opción:
   1️⃣ Solicitar turno
   2️⃣ Hablar con secretaria
   ```

5. Reply: `1` (for appointment option)
6. Expected bot response:
   ```
   Entendido. Solicitar turno 📅
   
   Por favor, espera mientras te conectamos...
   ```

7. Check logs in terminal: Should see audit_log entries for each interaction

---

## Step 10: Verify Database Audit Log

```bash
# Connect to PostgreSQL
psql -h localhost -U postgres -d turnohector

# View audit log
SELECT action, status, message_text, response_text, created_at 
FROM audit_log 
ORDER BY created_at DESC 
LIMIT 5;
```

Expected: Entries for WEBHOOK_RECEIVED, MENU_DISPLAYED, MENU_SELECTION_MADE

---

## Troubleshooting

### "Connection refused" (PostgreSQL)

```bash
# Check Docker container
docker-compose ps
docker-compose logs postgres

# Restart
docker-compose restart postgres
sleep 5
```

### "Bot token invalid"

- Re-check token from BotFather (copy-paste carefully, no spaces)
- Verify in `.env` file
- Restart API server

### "Signature validation failed"

- Ensure `TELEGRAM_BOT_WEBHOOK_SECRET` in `.env` matches what's in code
- Check that request body is sent as-is (no JSON prettifying)

### "No menu displayed"

- Check API logs: `tail -f <logfile>` or terminal where uvicorn runs
- Verify webhook URL is publicly accessible (use ngrok if local)
- Confirm webhook is set: `curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo`

---

## Next Steps

✅ **Webhook endpoint working**
✅ **Menu displays correctly**
✅ **Menu selection routed**

Now proceed to `/speckit.tasks` to generate implementation tasks and start coding!

---

## Local Development Workflow

### Run tests

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/contract/test_telegram_webhook.py -v

# With coverage
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

### Watch logs

```bash
# From API server terminal (uvicorn)
# Or check audit table:
watch -n 1 "psql -h localhost -U postgres -d turnohector -c 'SELECT COUNT(*) FROM audit_log;'"
```

### Clean up between tests

```bash
# Reset database
psql -h localhost -U postgres -d turnohector -c "TRUNCATE telegram_users, conversation_state, audit_log CASCADE;"
```

---

## Production Deployment (Later)

When ready to deploy to production:

1. Use proper domain (not ngrok)
2. Move secrets to secrets management (AWS Secrets Manager, etc.)
3. Set up HTTPS certificate (Let's Encrypt)
4. Use managed PostgreSQL (AWS RDS, etc.)
5. Configure backups and monitoring
6. Run load tests
7. Set up monitoring + alerting

See deployment guide in `docs/deployment.md` (to be created).
