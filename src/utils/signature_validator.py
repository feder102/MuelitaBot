"""Telegram webhook signature validation utility."""
import hmac
import hashlib
from typing import Optional


class SignatureValidator:
    """Validate Telegram webhook signatures using HMAC-SHA256."""

    def __init__(self, bot_token: str):
        """
        Initialize validator with bot token.

        Args:
            bot_token: Telegram bot token (used as secret key)
        """
        self.bot_token = bot_token

    def validate_signature(
        self,
        request_body: bytes,
        signature_header: Optional[str],
    ) -> bool:
        """
        Validate webhook signature against X-Telegram-Bot-API-Secret-SHA256 header.

        Args:
            request_body: Raw request body (bytes, not parsed JSON)
            signature_header: Value of X-Telegram-Bot-API-Secret-SHA256 header

        Returns:
            True if signature is valid, False otherwise
        """
        if not signature_header:
            return False

        # Compute expected signature
        expected_signature = hmac.new(
            self.bot_token.encode(),
            request_body,
            hashlib.sha256,
        ).hexdigest()

        # Compare signatures (constant-time comparison to prevent timing attacks)
        return hmac.compare_digest(expected_signature, signature_header)
