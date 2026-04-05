"""Service for dentist management and retrieval."""
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models.dentist import Dentist
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DentistNotFoundError(Exception):
    """Raised when a dentist is not found."""

    pass


class DentistInactiveError(Exception):
    """Raised when attempting to use an inactive dentist."""

    pass


class DentistService:
    """Service for managing dentists and retrieving dentist information."""

    @staticmethod
    async def get_active_dentists(session: AsyncSession) -> List[Dentist]:
        """
        Get all active dentists for the booking menu.

        Args:
            session: Database session

        Returns:
            List of active Dentist objects, sorted by name
        """
        stmt = select(Dentist).where(Dentist.active_status == True).order_by(Dentist.name)
        result = await session.execute(stmt)
        dentists = result.scalars().all()
        logger.debug(f"Found {len(dentists)} active dentists")
        return dentists

    @staticmethod
    async def get_dentist_by_id(session: AsyncSession, dentist_id: UUID) -> Dentist:
        """
        Get a specific dentist by ID, only if active.

        Args:
            session: Database session
            dentist_id: UUID of the dentist

        Returns:
            Dentist object

        Raises:
            DentistNotFoundError: If dentist not found or is inactive
        """
        stmt = select(Dentist).where(
            (Dentist.id == dentist_id) & (Dentist.active_status == True)
        )
        result = await session.execute(stmt)
        dentist = result.scalars().first()

        if not dentist:
            logger.warning(f"Dentist {dentist_id} not found or is inactive")
            raise DentistNotFoundError(f"Dentist {dentist_id} not found or is inactive")

        return dentist

    @staticmethod
    async def get_dentist_calendar_id(session: AsyncSession, dentist_id: UUID) -> str:
        """
        Get the Google Calendar ID for a specific dentist.

        Args:
            session: Database session
            dentist_id: UUID of the dentist

        Returns:
            Google Calendar ID string

        Raises:
            DentistNotFoundError: If dentist not found or is inactive
        """
        dentist = await DentistService.get_dentist_by_id(session, dentist_id)
        return dentist.calendar_id

    @staticmethod
    async def get_dentist_by_name(session: AsyncSession, name: str) -> Optional[Dentist]:
        """
        Get a dentist by name (case-sensitive).

        Args:
            session: Database session
            name: Dentist name

        Returns:
            Dentist object or None if not found
        """
        stmt = select(Dentist).where(Dentist.name == name)
        result = await session.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def create_dentist(
        session: AsyncSession,
        name: str,
        calendar_id: str,
        active_status: bool = True,
    ) -> Dentist:
        """
        Create a new dentist.

        Args:
            session: Database session
            name: Dentist name (must be unique)
            calendar_id: Google Calendar ID (must be unique)
            active_status: Whether the dentist is active

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
        logger.info(f"Created dentist: {dentist.name} ({dentist.id})")
        return dentist

    @staticmethod
    async def deactivate_dentist(session: AsyncSession, dentist_id: UUID) -> Dentist:
        """
        Deactivate a dentist (soft delete via active_status flag).

        Args:
            session: Database session
            dentist_id: UUID of the dentist

        Returns:
            Updated Dentist object
        """
        dentist = await DentistService.get_dentist_by_id(session, dentist_id)
        dentist.active_status = False
        await session.flush()
        logger.info(f"Deactivated dentist: {dentist.name}")
        return dentist

    @staticmethod
    async def activate_dentist(session: AsyncSession, dentist_id: UUID) -> Dentist:
        """
        Activate an inactive dentist.

        Args:
            session: Database session
            dentist_id: UUID of the dentist

        Returns:
            Updated Dentist object

        Raises:
            DentistNotFoundError: If dentist not found
        """
        stmt = select(Dentist).where(Dentist.id == dentist_id)
        result = await session.execute(stmt)
        dentist = result.scalars().first()

        if not dentist:
            logger.warning(f"Dentist {dentist_id} not found")
            raise DentistNotFoundError(f"Dentist {dentist_id} not found")

        dentist.active_status = True
        await session.flush()
        logger.info(f"Activated dentist: {dentist.name}")
        return dentist
