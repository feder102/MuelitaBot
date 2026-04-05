"""Message parsing service for extracting user intent from Telegram messages."""
from typing import Optional
import logging

from src.schemas.telegram_webhook import Update

logger = logging.getLogger(__name__)


class MessageParser:
    """Parse incoming Telegram messages and extract user information."""

    @staticmethod
    def parse_update(update: Update) -> dict:
        """
        Parse Telegram Update object and extract relevant information.

        Args:
            update: Telegram Update object

        Returns:
            Dictionary with parsed data: {
                "update_id": int,
                "user_id": int,
                "first_name": str,
                "last_name": Optional[str],
                "username": Optional[str],
                "message_text": Optional[str],
                "message_id": Optional[int],
                "timestamp": Optional[int],
            }
        """
        if not update.message:
            logger.warning(f"Update {update.update_id} has no message, ignoring")
            return {}

        message = update.message
        chat = message.chat
        user = message.from_

        # Use from_ object's user info (preferred), fall back to chat info
        first_name = user.first_name if user else chat.first_name
        last_name = user.last_name if user else chat.last_name
        username = user.username if user else chat.username

        parsed = {
            "update_id": update.update_id,
            "user_id": chat.id,
            "first_name": first_name,
            "last_name": last_name,
            "username": username,
            "message_text": message.text,
            "message_id": message.message_id,
            "timestamp": message.date,
        }

        logger.info(
            f"Parsed message from user {chat.id}: "
            f"{message.text[:50] if message.text else 'No text'}"
        )

        return parsed

    @staticmethod
    def extract_menu_selection(message_text: Optional[str]) -> Optional[str]:
        """
        Extract menu selection from user message.

        Args:
            message_text: User's message text

        Returns:
            - "1" if user selected appointment option
            - "2" if user selected secretary option
            - None if message doesn't match menu options
        """
        if not message_text:
            return None

        # Normalize message: strip whitespace, lowercase
        normalized = message_text.strip().lower()

        # Match appointment selection (option 1)
        if normalized in ["1", "opción 1", "option 1", "solicitar turno"]:
            logger.info(f"Menu selection detected: 1 (appointment)")
            return "1"

        # Match secretary selection (option 2)
        elif normalized in ["2", "opción 2", "option 2", "hablar con secretaria", "secretaria"]:
            logger.info(f"Menu selection detected: 2 (secretary)")
            return "2"

        # No match
        logger.info(f"No menu selection matched in: {message_text}")
        return None
