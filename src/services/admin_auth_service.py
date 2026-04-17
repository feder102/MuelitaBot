"""Admin authentication service for Feature 005."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.admin_user import AdminUser

logger = logging.getLogger(__name__)


class AdminAuthService:
    """Manage admin authentication and JWT tokens."""

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        """Verify password against bcrypt hash."""
        return bcrypt.checkpw(plain.encode(), hashed.encode())

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password with bcrypt (cost=12)."""
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()

    @staticmethod
    def create_access_token(admin_id: UUID) -> str:
        """Create JWT token."""
        payload = {
            "sub": str(admin_id),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.admin_jwt_expire_minutes),
            "iat": datetime.now(timezone.utc),
        }
        return jwt.encode(payload, settings.admin_jwt_secret, algorithm="HS256")

    @staticmethod
    async def get_current_admin(session: AsyncSession, token: str) -> AdminUser:
        """Validate JWT and return admin."""
        try:
            payload = jwt.decode(token, settings.admin_jwt_secret, algorithms=["HS256"])
            admin_id = UUID(payload["sub"])
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
        except (jwt.InvalidTokenError, KeyError, ValueError):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        stmt = select(AdminUser).where(AdminUser.id == admin_id, AdminUser.is_active)
        result = await session.execute(stmt)
        admin = result.scalars().first()

        if not admin:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin not found")

        return admin

    @staticmethod
    async def authenticate(session: AsyncSession, username: str, password: str) -> Optional[AdminUser]:
        """Authenticate admin by username/password."""
        stmt = select(AdminUser).where(AdminUser.username == username, AdminUser.is_active)
        result = await session.execute(stmt)
        admin = result.scalars().first()

        if not admin or not AdminAuthService.verify_password(password, admin.hashed_password):
            return None

        return admin


