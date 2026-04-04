"""Conversation state management service."""
from datetime import datetime
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.models.telegram_user import TelegramUser
from src.models.conversation_state import ConversationState, ConversationStateEnum

logger = logging.getLogger(__name__)


class ConversationManager:
    """Manage user profiles and conversation states."""

    @staticmethod
    async def get_or_create_user(
        session: AsyncSession,
        telegram_user_id: int,
        first_name: str,
        last_name: str = None,
        username: str = None,
    ) -> TelegramUser:
        """
        Get existing user or create new one.

        Args:
            session: Database session
            telegram_user_id: Telegram user ID
            first_name: User's first name
            last_name: User's last name (optional)
            username: User's username (optional)

        Returns:
            TelegramUser instance
        """
        # Try to find existing user
        stmt = select(TelegramUser).where(
            TelegramUser.telegram_user_id == telegram_user_id
        )
        result = await session.execute(stmt)
        user = result.scalars().first()

        if user:
            logger.info(f"Found existing user: {user.id}")
            return user

        # Create new user
        user = TelegramUser(
            telegram_user_id=telegram_user_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
        )
        session.add(user)
        await session.flush()  # Flush to get the ID
        logger.info(f"Created new user: {user.id}")
        return user

    @staticmethod
    async def get_user_state(
        session: AsyncSession,
        user_id: str,
    ) -> ConversationState:
        """
        Get user's conversation state.

        Args:
            session: Database session
            user_id: User's UUID

        Returns:
            ConversationState instance (creates if doesn't exist)
        """
        stmt = select(ConversationState).where(
            ConversationState.user_id == user_id
        )
        result = await session.execute(stmt)
        state = result.scalars().first()

        if state:
            logger.info(f"Found conversation state for user {user_id}: {state.current_state}")
            return state

        # Create new state
        state = ConversationState(user_id=user_id)
        session.add(state)
        await session.flush()
        logger.info(f"Created new conversation state for user {user_id}")
        return state

    @staticmethod
    async def update_state(
        session: AsyncSession,
        user_id: str,
        new_state: ConversationStateEnum,
        update_metadata: dict = None,
    ) -> ConversationState:
        """
        Update user's conversation state.

        Args:
            session: Database session
            user_id: User's UUID
            new_state: New state to set
            update_metadata: Optional metadata updates

        Returns:
            Updated ConversationState
        """
        state = await ConversationManager.get_user_state(session, user_id)
        state.current_state = new_state
        state.last_interaction = datetime.utcnow()
        state.updated_at = datetime.utcnow()

        if update_metadata:
            if state.context_data is None:
                state.context_data = {}
            state.context_data.update(update_metadata)

        await session.flush()
        logger.info(f"Updated state for user {user_id} to {new_state}")
        return state

    @staticmethod
    async def increment_menu_display_count(
        session: AsyncSession,
        user_id: str,
    ) -> ConversationState:
        """
        Increment menu display counter for user.

        Args:
            session: Database session
            user_id: User's UUID

        Returns:
            Updated ConversationState
        """
        state = await ConversationManager.get_user_state(session, user_id)
        state.menu_display_count += 1
        state.last_interaction = datetime.utcnow()
        await session.flush()
        logger.info(f"Menu display count for user {user_id}: {state.menu_display_count}")
        return state
