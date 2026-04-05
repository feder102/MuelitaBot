"""Webhook processing and orchestration service."""
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.audit_log import AuditLog, AuditActionEnum, AuditStatusEnum
from src.models.conversation_state import ConversationStateEnum
from src.schemas.telegram_webhook import Update
from src.schemas.appointment import AvailableSlot
from src.services.message_parser import MessageParser
from src.services.conversation_manager import ConversationManager
from src.services.menu_router import MenuRouter
from src.services.appointment_router import AppointmentRouter
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

        try:
            logger.info(f"🚀 Initializing AppointmentRouter in WebhookHandler...")
            self.appointment_router = AppointmentRouter()
            logger.info(f"✅ AppointmentRouter initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize AppointmentRouter: {type(e).__name__}: {e}", exc_info=True)
            self.appointment_router = None

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
            if state.current_state == ConversationStateEnum.AWAITING_SLOT_SELECTION:
                # User is viewing appointment slots - expecting slot number input
                slots_data = state.context_data.get("available_slots", []) if state.context_data else []

                # Convert dict slots back to AvailableSlot objects
                available_slots = []
                if slots_data:
                    for slot_dict in slots_data:
                        available_slots.append(AvailableSlot(**slot_dict))

                logger.info(f"📊 AWAITING_SLOT_SELECTION: user_input={message_text}, available_slots={len(available_slots)}")

                new_state, response_message, selected_slot = await self.appointment_router.validate_slot_selection(
                    message_text, available_slots
                )

                logger.info(f"✅ Slot validation result: new_state={new_state}, selected_slot={selected_slot}")

                await self.conversation_manager.update_state(
                    self.session, user.id, new_state, update_metadata={"selected_slot": selected_slot.model_dump(mode='json') if selected_slot else None}
                )

                await self._log_audit(
                    user_id=user.id,
                    action=AuditActionEnum.MENU_SELECTION_MADE,
                    status=AuditStatusEnum.SUCCESS,
                    message_text=message_text[:50],
                    response_text=response_message[:100],
                    ip_address=ip_address,
                )

            elif state.current_state == ConversationStateEnum.AWAITING_REASON_TEXT:
                # User is entering consultation reason
                logger.info(f"📋 AWAITING_REASON_TEXT: Processing user reason input from user {user.id}")
                selected_slot_data = state.context_data.get("selected_slot") if state.context_data else None
                if not selected_slot_data:
                    # Fallback - shouldn't happen
                    logger.warning(f"⚠️ No selected_slot found in context_data for user {user.id}")
                    new_state = ConversationStateEnum.AWAITING_MENU
                    response_message = self.menu_router.get_menu_message()
                else:
                    logger.info(f"✓ Found selected_slot in context_data: {selected_slot_data.get('date')} {selected_slot_data.get('start_time')}")
                    # Reconstruct AvailableSlot from context_data
                    selected_slot = AvailableSlot(**selected_slot_data)
                    logger.info(f"📅 Reconstructed slot: {selected_slot.date} {selected_slot.start_time}-{selected_slot.end_time}")

                    logger.info(f"🔄 Calling validate_and_book_appointment with reason: '{message_text[:50]}'")
                    new_state, response_message = await self.appointment_router.validate_and_book_appointment(
                        user_input=message_text,
                        patient_user_id=user.id,
                        selected_slot=selected_slot,
                        session=self.session,
                    )
                    logger.info(f"✅ Booking result: new_state={new_state}, message preview={response_message[:50]}")

                await self.conversation_manager.update_state(self.session, user.id, new_state)

                await self._log_audit(
                    user_id=user.id,
                    action=AuditActionEnum.MENU_SELECTION_MADE,
                    status=AuditStatusEnum.SUCCESS,
                    message_text=message_text[:50],
                    response_text=response_message[:100],
                    ip_address=ip_address,
                )

            elif state.current_state == ConversationStateEnum.APPOINTMENT_CONFIRMED:
                # User just booked - return to menu
                await self.conversation_manager.update_state(
                    self.session, user.id, ConversationStateEnum.AWAITING_MENU
                )
                response_message = self.menu_router.get_menu_message()

                await self._log_audit(
                    user_id=user.id,
                    action=AuditActionEnum.MENU_DISPLAYED,
                    status=AuditStatusEnum.SUCCESS,
                    response_text=response_message[:100],
                    ip_address=ip_address,
                )

            elif state.current_state.value in ["APPOINTMENT_SELECTED", "SECRETARY_SELECTED", "COMPLETED"]:
                # Legacy states - redirect to menu or handle
                if state.current_state.value == "APPOINTMENT_SELECTED":
                    # User selected appointment; fetch slots
                    new_state, response_message, available_slots = await self.appointment_router.fetch_and_show_slots(session=self.session)

                    await self.conversation_manager.update_state(
                        self.session,
                        user.id,
                        new_state,
                        update_metadata={"available_slots": [slot.dict() for slot in available_slots]},
                    )

                    await self._log_audit(
                        user_id=user.id,
                        action=AuditActionEnum.APPOINTMENT_ROUTED,
                        status=AuditStatusEnum.SUCCESS,
                        response_text=response_message[:100],
                        ip_address=ip_address,
                    )
                else:
                    # Other completed states - re-display menu
                    response_message = self.menu_router.get_menu_message()
                    await self.conversation_manager.update_state(
                        self.session, user.id, ConversationStateEnum.AWAITING_MENU
                    )

            else:
                # AWAITING_MENU or AWAITING_SELECTION - check if this is a menu selection
                selection = self.message_parser.extract_menu_selection(message_text)

                if selection:
                    # Menu selection detected
                    new_state, response_message = self.menu_router.route_selection(selection)

                    logger.info(f"🎯 Menu selection: selection={selection}, new_state={new_state}, new_state.value={new_state.value if new_state else None}")

                    await self._log_audit(
                        user_id=user.id,
                        action=AuditActionEnum.MENU_SELECTION_MADE,
                        status=AuditStatusEnum.SUCCESS,
                        message_text=selection,
                        response_text=response_message[:100],
                        ip_address=ip_address,
                    )

                    # For appointment selection, fetch slots immediately
                    if new_state and new_state.value == "APPOINTMENT_SELECTED":
                        if not self.appointment_router:
                            logger.error(f"❌ appointment_router is None - cannot fetch slots!")
                            response_message = "Sistema de turnos no disponible. Contacta a la secretaria."
                            available_slots = []
                        else:
                            new_state, response_message, available_slots = await self.appointment_router.fetch_and_show_slots(session=self.session)

                        logger.info(f"🎯 Fetched {len(available_slots)} slots for user {user.id}")

                        await self.conversation_manager.update_state(
                            self.session,
                            user.id,
                            new_state,
                            update_metadata={"available_slots": [slot.model_dump(mode='json') for slot in available_slots]},
                        )

                        logger.info(f"💾 Saved {len(available_slots)} slots to context_data for state {new_state}")

                        await self._log_audit(
                            user_id=user.id,
                            action=AuditActionEnum.APPOINTMENT_ROUTED,
                            status=AuditStatusEnum.SUCCESS,
                            response_text=response_message[:100],
                            ip_address=ip_address,
                        )
                    elif new_state:
                        await self.conversation_manager.update_state(
                            self.session,
                            user.id,
                            new_state,
                        )

                        # Log routing decision
                        action = AuditActionEnum.SECRETARY_ROUTED if new_state.value == "SECRETARY_SELECTED" else AuditActionEnum.APPOINTMENT_ROUTED
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
            # Rollback session first to avoid PendingRollbackError
            await self.session.rollback()
            try:
                await self._log_audit(
                    user_id=None,
                    action=AuditActionEnum.DATABASE_ERROR,
                    status=AuditStatusEnum.ERROR,
                    error_detail=str(e)[:500],
                    ip_address=ip_address,
                )
            except Exception as audit_error:
                logger.error(f"Failed to log audit after error: {audit_error}")
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
