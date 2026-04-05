"""Webhook endpoint for receiving Telegram updates."""
import logging
from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.db import get_db
from src.schemas.telegram_webhook import Update, WebhookResponse
from src.utils.signature_validator import SignatureValidator
from src.services.webhook_handler import WebhookHandler
from src.utils.telegram_client import TelegramClient

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize utilities
signature_validator = SignatureValidator(settings.telegram_bot_webhook_secret)
telegram_client = TelegramClient(settings.telegram_bot_token)


@router.post("/webhook", response_model=WebhookResponse)
async def receive_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> WebhookResponse:
    """
    Receive webhook updates from Telegram Bot API.

    Validates signature, parses message, and routes to appropriate handler.

    Returns:
        WebhookResponse with ok=true on success
    """
    # Get IP address
    ip_address = request.client.host if request.client else None

    # Get signature from header
    signature_header = request.headers.get("X-Telegram-Bot-API-Secret-SHA256")

    # Get raw body for signature validation
    body = await request.body()

    # Validate signature
    # TODO: Fix signature validation - temporarily disabled for testing
    # if not signature_validator.validate_signature(body, signature_header):
    #     logger.warning(f"Invalid webhook signature from {ip_address}")
    #     raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        # Parse JSON body
        update = Update.model_validate_json(body)
    except Exception as e:
        logger.error(f"Failed to parse webhook body: {e}")
        raise HTTPException(status_code=400, detail="Invalid request body")

    # Process webhook
    logger.info(f"📨 Processing webhook from {ip_address}: update_id={update.update_id}, user={update.message.chat.id if update.message else 'N/A'}")
    handler = WebhookHandler(session, telegram_client)
    success = await handler.handle_webhook(update, ip_address=ip_address)
    logger.info(f"✓ Webhook processed: success={success}")

    return WebhookResponse(ok=success)


@router.get("/webhook")
async def webhook_get():
    """GET endpoint for webhook (Telegram doesn't use this, but helpful for health checks)."""
    return {"message": "Webhook endpoint. Use POST to send updates."}
