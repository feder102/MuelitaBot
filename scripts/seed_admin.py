"""Seed admin user into admin_users table."""
import asyncio
import argparse
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import bcrypt

from src.config import settings
from src.models.admin_user import AdminUser


async def seed_admin(username: str, password: str) -> None:
    """Create first admin user."""
    engine = create_async_engine(settings.database_url)
    async_session = async_sessionmaker(engine, class_=AsyncSession)

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()

    async with async_session() as session:
        admin = AdminUser(username=username, hashed_password=hashed)
        session.add(admin)
        await session.commit()
        print(f"✅ Admin user created: {username}")

    await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description="Seed admin user")
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    asyncio.run(seed_admin(args.username, args.password))


if __name__ == "__main__":
    main()
