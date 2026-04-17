"""Webhook processing and orchestration service."""
import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.audit_log import AuditLog, AuditActionEnum, AuditStatusEnum
from src.models.conversation_state import ConversationStateEnum
from src.schemas.telegram_webhook import Update
from src.schemas.appointment import AvailableSlot
from src.services.message_parser import MessageParser
from src.services.conversation_manager import ConversationManager
from src.services.menu_router import MenuRouter
from src.services.appointment_router import AppointmentRouter
from src.services.cancellation_router import CancellationRouter
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

        try:
            logger.info(f"🚀 Initializing CancellationRouter in WebhookHandler...")
            self.cancellation_router = CancellationRouter()
            logger.info(f"✅ CancellationRouter initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize CancellationRouter: {type(e).__name__}: {e}", exc_info=True)
            self.cancellation_router = None

    def _get_selected_dentist_id(self, context_data: dict | None, user_id) -> UUID | None:
        """Parse selected dentist id from conversation context."""
        if not context_data or "selected_dentist_id" not in context_data:
            return None

        raw_dentist_id = context_data.get("selected_dentist_id")
        try:
            dentist_id = UUID(raw_dentist_id)
        except (TypeError, ValueError):
            logger.warning(
                "⚠️ Invalid selected_dentist_id in context_data for user %s: %r",
                user_id,
                raw_dentist_id,
            )
            raise

        logger.info(f"🦷 Multi-dentist booking with dentist_id={dentist_id}")
        return dentist_id

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

                try:
                    dentist_id = self._get_selected_dentist_id(state.context_data, user.id)
                except (TypeError, ValueError):
                    response_message = (
                        "No pudimos validar el odontólogo seleccionado.\n\n"
                        f"{self.menu_router.get_menu_message()}"
                    )
                    await self.conversation_manager.update_state(
                        self.session,
                        user.id,
                        ConversationStateEnum.AWAITING_MENU,
                    )
                    await self._log_audit(
                        user_id=user.id,
                        action=AuditActionEnum.INVALID_SELECTION,
                        status=AuditStatusEnum.VALIDATION_FAILED,
                        message_text=message_text[:50],
                        response_text=response_message[:100],
                        ip_address=ip_address,
                    )
                    logger.info(f"📨 Sending message to user {user_id}: {response_message[:100]}...")
                    await self.telegram_client.send_message(user_id, response_message)
                    await self.session.commit()
                    logger.info(f"Webhook processed successfully for user {user_id}")
                    return True

                logger.info(f"📊 AWAITING_SLOT_SELECTION: user_input={message_text}, available_slots={len(available_slots)}")

                new_state, response_message, selected_slot = await self.appointment_router.validate_slot_selection(
                    message_text,
                    available_slots,
                    session=self.session,
                    dentist_id=dentist_id,
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

                    # Get dentist_id for multi-dentist support
                    try:
                        dentist_id = self._get_selected_dentist_id(state.context_data, user.id)
                    except (TypeError, ValueError):
                        response_message = (
                            "No pudimos validar el odontólogo seleccionado.\n\n"
                            f"{self.menu_router.get_menu_message()}"
                        )
                        await self.conversation_manager.update_state(
                            self.session,
                            user.id,
                            ConversationStateEnum.AWAITING_MENU,
                        )
                        await self._log_audit(
                            user_id=user.id,
                            action=AuditActionEnum.INVALID_SELECTION,
                            status=AuditStatusEnum.VALIDATION_FAILED,
                            message_text=message_text[:50],
                            response_text=response_message[:100],
                            ip_address=ip_address,
                        )
                        logger.info(f"📨 Sending message to user {user_id}: {response_message[:100]}...")
                        await self.telegram_client.send_message(user_id, response_message)
                        await self.session.commit()
                        logger.info(f"Webhook processed successfully for user {user_id}")
                        return True

                    logger.info(f"🔄 Calling validate_and_book_appointment with reason: '{message_text[:50]}'")
                    new_state, response_message = await self.appointment_router.validate_and_book_appointment(
                        user_input=message_text,
                        patient_user_id=user.id,
                        selected_slot=selected_slot,
                        dentist_id=dentist_id,  # Multi-dentist support
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

            elif state.current_state == ConversationStateEnum.SELECTING_CANCELLATION_APPOINTMENT:
                # User is viewing their cancellable appointment list and selecting one
                logger.info(f"🗑️ SELECTING_CANCELLATION_APPOINTMENT: Processing selection from user {user.id}")
                new_state, response_message, context_update = await self.cancellation_router.validate_appointment_selection(
                    user_input=message_text,
                    context_data=state.context_data or {},
                )
                update_metadata = context_update if context_update else None
                await self.conversation_manager.update_state(
                    self.session, user.id, new_state, update_metadata=update_metadata
                )
                await self._log_audit(
                    user_id=user.id,
                    action=AuditActionEnum.MENU_SELECTION_MADE,
                    status=AuditStatusEnum.SUCCESS,
                    message_text=message_text[:50] if message_text else None,
                    response_text=response_message[:100],
                    ip_address=ip_address,
                )

            elif state.current_state == ConversationStateEnum.AWAITING_CANCELLATION_CONFIRMATION:
                # User is confirming or aborting cancellation
                logger.info(f"🗑️ AWAITING_CANCELLATION_CONFIRMATION: Processing confirmation from user {user.id}")
                confirmation = self.message_parser.extract_cancellation_confirmation(message_text)
                # If confirmation is None (unexpected input), pass it through; router will re-prompt
                effective_confirmation = confirmation if confirmation else (message_text or "")
                new_state, response_message = await self.cancellation_router.confirm_and_cancel_appointment(
                    session=self.session,
                    user=user,
                    confirmation=effective_confirmation,
                    context_data=state.context_data or {},
                )
                await self.conversation_manager.update_state(
                    self.session, user.id, new_state
                )
                await self._log_audit(
                    user_id=user.id,
                    action=AuditActionEnum.APPOINTMENT_CANCELLED
                    if new_state == ConversationStateEnum.AWAITING_MENU and effective_confirmation == "si"
                    else AuditActionEnum.MENU_SELECTION_MADE,
                    status=AuditStatusEnum.SUCCESS,
                    message_text=message_text[:50] if message_text else None,
                    response_text=response_message[:100],
                    ip_address=ip_address,
                )

            elif state.current_state == ConversationStateEnum.SELECTING_DENTIST:
                # User is selecting which dentist to book with
                logger.info(f"🦷 SELECTING_DENTIST: Processing dentist selection from user {user.id}")
                available_dentist_ids = state.context_data.get("available_dentists", []) if state.context_data else []
                dentist_names = state.context_data.get("dentist_names", {}) if state.context_data else {}

                logger.info(f"📋 Available dentists: {available_dentist_ids}")

                new_state, response_message, context_data = await self.appointment_router.handle_dentist_selected(
                    session=self.session,
                    user_input=message_text,
                    available_dentist_ids=available_dentist_ids,
                    dentist_names=dentist_names,
                )

                logger.info(f"✅ Dentist selection result: new_state={new_state}")

                update_metadata = {}
                if context_data and "selected_dentist_id" in context_data:
                    update_metadata["selected_dentist_id"] = context_data["selected_dentist_id"]
                if context_data and "available_dentists" in context_data:
                    update_metadata["available_dentists"] = context_data["available_dentists"]
                    update_metadata["dentist_names"] = context_data.get("dentist_names", {})
                if context_data and "available_slots" in context_data:
                    update_metadata["available_slots"] = context_data["available_slots"]

                await self.conversation_manager.update_state(
                    self.session,
                    user.id,
                    new_state,
                    update_metadata=update_metadata,
                )

                await self._log_audit(
                    user_id=user.id,
                    action=AuditActionEnum.MENU_SELECTION_MADE,
                    status=AuditStatusEnum.SUCCESS,
                    message_text=message_text[:50],
                    response_text=response_message[:100],
                    ip_address=ip_address,
                )

            elif state.current_state.value in ["APPOINTMENT_SELECTED", "SECRETARY_SELECTED", "COMPLETED"]:
                # Legacy states - redirect to menu or handle
                if state.current_state.value == "APPOINTMENT_SELECTED":
                    # User selected appointment; check for multi-dentist support
                    new_state, response_message, context_data = await self.appointment_router.handle_appointment_request(session=self.session)

                    update_metadata = {}
                    if context_data:
                        if "selected_dentist_id" in context_data:
                            update_metadata["selected_dentist_id"] = context_data["selected_dentist_id"]
                        if "available_dentists" in context_data:
                            update_metadata["available_dentists"] = context_data["available_dentists"]
                            update_metadata["dentist_names"] = context_data.get("dentist_names", {})
                        if "available_slots" in context_data:
                            update_metadata["available_slots"] = context_data["available_slots"]

                    await self.conversation_manager.update_state(
                        self.session,
                        user.id,
                        new_state,
                        update_metadata=update_metadata,
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
                    # Option 3: Cancel appointment — handle directly, no intermediate state needed
                    if selection == "3":
                        logger.info(f"🗑️ Menu selection: 3 (cancel appointment) for user {user.id}")
                        new_state, response_message, context_data = await self.cancellation_router.handle_cancellation_request(
                            session=self.session, user=user
                        )
                        update_metadata = context_data if context_data else None
                        await self.conversation_manager.update_state(
                            self.session, user.id, new_state, update_metadata=update_metadata
                        )
                        await self._log_audit(
                            user_id=user.id,
                            action=AuditActionEnum.MENU_SELECTION_MADE,
                            status=AuditStatusEnum.SUCCESS,
                            message_text=selection,
                            response_text=response_message[:100],
                            ip_address=ip_address,
                        )
                    else:
                        # Menu selection detected (options 1, 2)
                        new_state, response_message = self.menu_router.route_selection(selection)

                        logger.info(f"🎯 Menu selection: selection={selection}, new_state={new_state}, new_state.value={new_state.value if new_state else None}")

                        # Handle appointment selection immediately without waiting for next message
                        if new_state == ConversationStateEnum.APPOINTMENT_SELECTED:
                            logger.info(f"🚀 Auto-processing APPOINTMENT_SELECTED immediately...")
                            logger.info(f"   appointment_router: {self.appointment_router}")
                            logger.info(f"   appointment_router.dentist_service: {self.appointment_router.dentist_service if self.appointment_router else 'N/A'}")
                            new_state, response_message, context_data = await self.appointment_router.handle_appointment_request(session=self.session)
                            logger.info(f"   ✅ handle_appointment_request() returned: new_state={new_state}, context_data keys={context_data.keys() if context_data else None}")

                            update_metadata = {}
                            if context_data:
                                if "selected_dentist_id" in context_data:
                                    update_metadata["selected_dentist_id"] = context_data["selected_dentist_id"]
                                if "available_dentists" in context_data:
                                    update_metadata["available_dentists"] = context_data["available_dentists"]
                                    update_metadata["dentist_names"] = context_data.get("dentist_names", {})
                                if "available_slots" in context_data:
                                    update_metadata["available_slots"] = context_data["available_slots"]

                            logger.info(f"   Calling update_state with new_state={new_state}, update_metadata={update_metadata.keys() if update_metadata else {}}")
                            await self.conversation_manager.update_state(
                                self.session,
                                user.id,
                                new_state,
                                update_metadata=update_metadata,
                            )

                            logger.info(f"✅ APPOINTMENT_SELECTED processed, new_state={new_state}, final response_message={response_message[:60]}...")
                        else:
                            # For other selections (Secretary, etc.), just update state
                            await self.conversation_manager.update_state(
                                self.session, user.id, new_state
                            )

                        await self._log_audit(
                            user_id=user.id,
                            action=AuditActionEnum.MENU_SELECTION_MADE,
                            status=AuditStatusEnum.SUCCESS,
                            message_text=selection,
                            response_text=response_message[:100],
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
            logger.info(f"📨 Sending message to user {user_id}: {response_message[:100]}...")
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
