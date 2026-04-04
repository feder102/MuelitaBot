"""Telegram Bot API client wrapper."""
import logging
import aiohttp
from typing import Optional

logger = logging.getLogger(__name__)


class TelegramClient:
    """Client for interacting with Telegram Bot API."""

    BASE_URL = "https://api.telegram.org"

    def __init__(self, bot_token: str):
        """
        Initialize Telegram client.

        Args:
            bot_token: Telegram bot token
        """
        self.bot_token = bot_token
        self.base_url = f"{self.BASE_URL}/bot{bot_token}"

    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str = "HTML",
    ) -> Optional[dict]:
        """
        Send message to Telegram user.

        Args:
            chat_id: Telegram chat ID (user ID for private messages)
            text: Message text
            parse_mode: HTML or Markdown formatting

        Returns:
            Response from Telegram API or None if failed
        """
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    data = await response.json()

                    if response.status == 200 and data.get("ok"):
                        logger.info(f"Message sent to user {chat_id}")
                        return data
                    else:
                        error = data.get("description", "Unknown error")
                        logger.error(f"Failed to send message to {chat_id}: {error}")
                        return None

        except aiohttp.ClientError as e:
            logger.error(f"HTTP error sending message to {chat_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error sending message to {chat_id}: {e}", exc_info=True)
            return None
