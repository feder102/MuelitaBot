# Setup Guide

## Database

Run migrations before using the bot:

```bash
alembic upgrade head
```

## Dentist Configuration

Add dentists without changing code:

```bash
python3 scripts/seed_dentists.py "Hector" "hector@clinic.calendar.google.com"
python3 scripts/seed_dentists.py "Fulano" "fulano@clinic.calendar.google.com"
```

Bulk import also works:

```bash
python3 scripts/seed_dentists.py --file scripts/dentists.json.example
```

The bot reads active dentists from the `dentists` table on each interaction, so new records appear in the booking menu without redeploying the app.
