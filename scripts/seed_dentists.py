#!/usr/bin/env python3
"""Script to seed dentists into the database.

Usage:
    python scripts/seed_dentists.py "Hector" "hector@clinic.calendar.google.com"
    python scripts/seed_dentists.py "Fulano" "fulano@clinic.calendar.google.com"

    Or provide a JSON file with dentist data:
    python scripts/seed_dentists.py --file dentists.json
"""
import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.config import settings
from src.models.dentist import Dentist
from src.db import Base


async def create_database_session():
    """Create async database session."""
    engine = create_async_engine(
        settings.database_url,
        echo=False,
    )
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, async_session


async def seed_dentist(
    session: AsyncSession,
    name: str,
    calendar_id: str,
    active_status: bool = True,
) -> Dentist:
    """Add a single dentist to the database.

    Args:
        session: Database session
        name: Dentist name
        calendar_id: Google Calendar ID
        active_status: Whether dentist is active

    Returns:
        Created Dentist object
    """
    dentist = Dentist(
        name=name,
        calendar_id=calendar_id,
        active_status=active_status,
    )
    session.add(dentist)
    await session.flush()
    await session.commit()
    print(f"✅ Created dentist: {dentist.name} (ID: {dentist.id})")
    return dentist


async def seed_from_json(session: AsyncSession, json_file: str) -> list[Dentist]:
    """Load dentists from JSON file.

    JSON file format:
    [
        {"name": "Hector", "calendar_id": "hector@clinic.calendar.google.com", "active_status": true},
        {"name": "Fulano", "calendar_id": "fulano@clinic.calendar.google.com", "active_status": true}
    ]

    Args:
        session: Database session
        json_file: Path to JSON file

    Returns:
        List of created Dentist objects
    """
    with open(json_file, 'r') as f:
        dentist_data = json.load(f)

    created_dentists = []
    for dentist in dentist_data:
        d = await seed_dentist(
            session,
            name=dentist['name'],
            calendar_id=dentist['calendar_id'],
            active_status=dentist.get('active_status', True),
        )
        created_dentists.append(d)

    return created_dentists


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    engine, async_session_factory = await create_database_session()

    try:
        async with async_session_factory() as session:
            if sys.argv[1] == "--file" and len(sys.argv) >= 3:
                # Load from JSON file
                json_file = sys.argv[2]
                print(f"📁 Loading dentists from {json_file}...")
                await seed_from_json(session, json_file)
                print(f"✅ Dentists seeded successfully")

            elif len(sys.argv) >= 3:
                # Command line arguments: name calendar_id
                name = sys.argv[1]
                calendar_id = sys.argv[2]
                print(f"➕ Adding dentist: {name}")
                await seed_dentist(session, name, calendar_id)
                print(f"✅ Dentist seeded successfully")

            else:
                print(__doc__)
                return 1

    except FileNotFoundError as e:
        print(f"❌ File not found: {e}")
        return 1
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        return 1
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        return 1
    finally:
        await engine.dispose()

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
