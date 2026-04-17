# Quickstart: Web Admin Dashboard (005)

## Prerequisites

- Backend running (`python3 src/main.py`)
- PostgreSQL up (`docker-compose up -d postgres`)
- Migration applied (`alembic upgrade head`)
- Node.js 20+ installed

## 1. Apply the new migration

```bash
alembic upgrade head
# Creates: admin_users table
```

## 2. Seed the first admin user

```bash
python3 scripts/seed_admin.py --username admin --password <your-secure-password>
```

## 3. Start the backend

```bash
source venv/bin/activate
python3 src/main.py
# Backend: http://localhost:8000
# Admin API: http://localhost:8000/admin/...
```

## 4. Install frontend dependencies

```bash
cd frontend
npm install
```

## 5. Configure frontend environment

```bash
cp .env.example .env.local
# Edit .env.local:
# NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 6. Start the frontend dev server

```bash
cd frontend
npm run dev
# Dashboard: http://localhost:3000
```

## 7. Log in

Open `http://localhost:3000` → redirects to `/login`.  
Enter the credentials from step 2.

## Running backend tests

```bash
# All tests
pytest tests/ -v

# Admin API tests only
pytest tests/admin/ -v
```

## Running frontend tests

```bash
cd frontend
npm test
```

## Production build

```bash
cd frontend
npm run build
npm start
```

## Environment Variables (frontend)

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend base URL | `http://localhost:8000` |

## Environment Variables (backend additions)

| Variable | Description |
|----------|-------------|
| `ADMIN_JWT_SECRET` | Secret key for signing JWT session tokens (min 32 chars) |
| `ADMIN_JWT_EXPIRE_MINUTES` | Session token lifetime in minutes (default: 60) |
