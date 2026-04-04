"""Webhook processing and orchestration service."""
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.audit_log import AuditLog, AuditActionEnum, AuditStatusEnum
from src.schemas.telegram_webhook import Update
from src.services.message_parser import MessageParser
from src.services.conversation_manager import ConversationManager
from src.services.menu_router import MenuRouter
from src.utils.telegram_client import TelegramClient

logger = logging.getLogger(__name__)


class WebhookHandler:
    """Handle incoming webhook requests and orchestrate processing."""

    def __init__(self, session: AsyncSession, telegram_client: TelegramClient):
        """
        Initialize handler.

        Args:
            session: Database session
            telegram_client: Telegram API client
        """
        self.session = session
        self.telegram_client = telegram_client
        self.message_parser = MessageParser()
        self.conversation_manager = ConversationManager()
        self.menu_router = MenuRouter()

    async def handle_webhook(
        self,
        update: Update,
        ip_address: str = None,
    ) -> bool:
        """
        Handle incoming webhook request.

        Args:
            update: Telegram Update object
            ip_address: Source IP address (for audit)

        Returns:
            True if webhook processed successfully
        """
        # Log webhook received
        await self._log_audit(
            user_id=None,  # Not yet known
            action=AuditActionEnum.WEBHOOK_RECEIVED,
            status=AuditStatusEnum.SUCCESS,
            message_text=str(update.update_id),
            ip_address=ip_address,
        )

        try:
            # Parse message
            parsed = self.message_parser.parse_update(update)
            if not parsed:
                await self._log_audit(
                    user_id=None,
                    action=AuditActionEnum.MESSAGE_PARSED,
                    status=AuditStatusEnum.VALIDATION_FAILED,
                    error_detail="No message in update",
                    ip_address=ip_address,
                )
                return False

            user_id = parsed["user_id"]
            message_text = parsed.get("message_text")

            await self._log_audit(
                user_id=None,  # Don't know user_id yet at Telegram level
                action=AuditActionEnum.MESSAGE_PARSED,
                status=AuditStatusEnum.SUCCESS,
                message_text=message_text[:100] if message_text else None,
                ip_address=ip_address,
            )

            # Get or create user
            user = await self.conversation_manager.get_or_create_user(
                self.session,
                user_id,
                parsed["first_name"],
                parsed.get("last_name"),
                parsed.get("username"),
            )

            # Get user's conversation state
            state = await self.conversation_manager.get_user_state(self.session, user.id)

            # Determine action based on state
            if state.current_state.value in ["APPOINTMENT_SELECTED", "SECRETARY_SELECTED", "COMPLETED"]:
                # User already selected an option; re-display menu
                response_message = self.menu_router.get_menu_message()
                await self.conversation_manager.update_state(
                    self.session,
                    user.id,
                    # Reset state for new menu (or keep in selection state)
                )
            else:
                # Check if this is a menu selection
                selection = self.message_parser.extract_menu_selection(message_text)

                if selection:
                    # Menu selection detected
                    new_state, response_message = self.menu_router.route_selection(selection)

                    await self._log_audit(
                        user_id=user.id,
                        action=AuditActionEnum.MENU_SELECTION_MADE,
                        status=AuditStatusEnum.SUCCESS,
                        message_text=selection,
                        response_text=response_message[:100],
                        ip_address=ip_address,
                    )

                    if new_state:
                        await self.conversation_manager.update_state(
                            self.session,
                            user.id,
                            new_state,
                        )

                        # Log routing decision
                        action = (
                            AuditActionEnum.APPOINTMENT_ROUTED
                            if new_state.value == "APPOINTMENT_SELECTED"
                            else AuditActionEnum.SECRETARY_ROUTED
                        )
                        await self._log_audit(
                            user_id=user.id,
                            action=action,
                            status=AuditStatusEnum.SUCCESS,
                            message_text=selection,
                            ip_address=ip_address,
                        )
                else:
                    # No selection; display or re-display menu
                    await self.conversation_manager.increment_menu_display_count(
                        self.session,
                        user.id,
                    )

                    response_message = self.menu_router.get_menu_message()

                    # Check if this is invalid selection (user sent something)
                    if message_text:
                        await self._log_audit(
                            user_id=user.id,
                            action=AuditActionEnum.INVALID_SELECTION,
                            status=AuditStatusEnum.VALIDATION_FAILED,
                            message_text=message_text[:100],
                            response_text=response_message[:100],
                            ip_address=ip_address,
                        )
                    else:
                        await self._log_audit(
                            user_id=user.id,
                            action=AuditActionEnum.MENU_DISPLAYED,
                            status=AuditStatusEnum.SUCCESS,
                            response_text=response_message[:100],
                            ip_address=ip_address,
                        )

            # Send response via Telegram API
            await self.telegram_client.send_message(user_id, response_message)

            # Commit changes
            await self.session.commit()
            logger.info(f"Webhook processed successfully for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error processing webhook: {e}", exc_info=True)
            await self._log_audit(
                user_id=None,
                action=AuditActionEnum.DATABASE_ERROR,
                status=AuditStatusEnum.ERROR,
                error_detail=str(e)[:500],
                ip_address=ip_address,
            )
            await self.session.rollback()
            return False

    async def _log_audit(
        self,
        user_id,
        action: AuditActionEnum,
        status: AuditStatusEnum,
        message_text: str = None,
        response_text: str = None,
        error_detail: str = None,
        ip_address: str = None,
    ) -> None:
        """
        Log audit entry.

        Args:
            user_id: User's UUID (can be None if auth failed)
            action: Action type
            status: Action result status
            message_text: User's message
            response_text: Bot's response
            error_detail: Error details (if status=ERROR)
            ip_address: Source IP
        """
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            status=status,
            message_text=message_text,
            response_text=response_text,
            error_detail=error_detail,
            ip_address=ip_address,
        )
        self.session.add(audit_log)
        await self.session.flush()
