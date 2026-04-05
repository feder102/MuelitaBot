"""Appointment booking flow router and state machine."""
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, timedelta

from src.config import settings
from src.models.conversation_state import ConversationStateEnum
from src.schemas.appointment import AvailableSlot
from src.services.google_calendar_client import GoogleCalendarClient, GoogleCalendarError
from src.services.appointment_service import (
    AppointmentService,
    InvalidSlotError,
    InvalidReasonError,
    SlotAlreadyBookedError,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AppointmentRouter:
    """Route and handle appointment booking state transitions."""

    def __init__(self):
        """Initialize appointment router with services."""
        try:
            logger.info(f"📋 Initializing AppointmentRouter...")
            logger.info(f"   Calendar ID: {settings.google_calendar_id}")
            self.google_client = GoogleCalendarClient(
                credentials_dict=settings.google_calendar_credentials,
                calendar_id=settings.google_calendar_id,
            )
            logger.info(f"✓ GoogleCalendarClient initialized")

            self.appointment_service = AppointmentService(
                google_calendar_client=self.google_client,
                clinic_timezone=settings.clinic_timezone,
                reason_max_length=settings.appointment_reason_max_length,
            )
            logger.info(f"✓ AppointmentService initialized")
        except ValueError as e:
            logger.error(f"❌ ValueError initializing AppointmentRouter: {e}")
            self.google_client = None
            self.appointment_service = None
        except Exception as e:
            logger.error(f"❌ Unexpected error initializing AppointmentRouter: {type(e).__name__}: {e}", exc_info=True)
            self.google_client = None
            self.appointment_service = None

    async def fetch_and_show_slots(self, session: AsyncSession = None) -> tuple[ConversationStateEnum, str, list[AvailableSlot]]:
        """Fetch available slots and format for user display.

        Called when user selects "1" (Solicitar turno).

        Args:
            session: Optional database session for fetching existing appointments

        Returns:
            (new_state, message, available_slots)
        """
        logger.info(f"🔍 fetch_and_show_slots() called")

        if not self.appointment_service:
            logger.error(f"❌ appointment_service is None - Google Calendar not initialized!")
            return (
                ConversationStateEnum.AWAITING_MENU,
                "Sistema de turnos no disponible. Contacta a la secretaria.",
                [],
            )

        try:
            # Fetch tomorrow to next week
            tomorrow = date.today() + timedelta(days=1)
            next_week = tomorrow + timedelta(days=7)
            logger.info(f"📅 Fetching slots from {tomorrow} to {next_week}")

            slots, message = await self.appointment_service.fetch_and_display_slots(
                date_start=tomorrow, date_end=next_week, session=session
            )
            logger.info(f"✅ Got {len(slots)} slots from service")

            if not slots:
                logger.warning(f"⚠️ No slots available in date range")
                return (
                    ConversationStateEnum.AWAITING_MENU,
                    message,
                    [],
                )

            logger.info(f"✓ Returning {len(slots)} slots to user")
            return (ConversationStateEnum.AWAITING_SLOT_SELECTION, message, slots)

        except GoogleCalendarError as e:
            logger.error(f"❌ GoogleCalendarError in fetch_and_show_slots: {type(e).__name__}: {e}", exc_info=True)
            return (
                ConversationStateEnum.AWAITING_MENU,
                "Sistema de turnos no disponible. Contacta a la secretaria.",
                [],
            )
        except Exception as e:
            logger.error(f"💥 Unexpected error in fetch_and_show_slots: {type(e).__name__}: {e}", exc_info=True)
            return (
                ConversationStateEnum.AWAITING_MENU,
                "Sistema de turnos no disponible. Contacta a la secretaria.",
                [],
            )

    async def validate_slot_selection(
        self, user_input: str, available_slots: list[AvailableSlot]
    ) -> tuple[ConversationStateEnum, str, AvailableSlot | None]:
        """Validate user's slot selection.

        Called when user sends a number after viewing slots.

        Returns:
            (new_state, message, selected_slot_or_none)
        """
        try:
            slot_index = self.appointment_service.validate_slot_selection(user_input, available_slots)
            selected_slot = available_slots[slot_index]

            message = "Entendido. Indícanos el motivo de tu consulta (máx 150 caracteres):"
            return (ConversationStateEnum.AWAITING_REASON_TEXT, message, selected_slot)

        except InvalidSlotError as e:
            # Invalid selection; re-show slots
            _, slots_message, _ = await self.fetch_and_show_slots()
            message = f"{str(e)}\n\n{slots_message}"
            return (ConversationStateEnum.AWAITING_SLOT_SELECTION, message, None)

    async def validate_and_book_appointment(
        self,
        user_input: str,
        patient_user_id: int,
        selected_slot: AvailableSlot,
        created_by_phone: str | None = None,
        session: AsyncSession | None = None,
    ) -> tuple[ConversationStateEnum, str]:
        """Validate reason and book appointment.

        Called when user provides consultation reason.

        Returns:
            (new_state, confirmation_message)
        """
        try:
            # Validate reason
            logger.info(f"🔍 Validating reason: '{user_input[:50]}'")
            reason = self.appointment_service.validate_reason(user_input)
            logger.info(f"✓ Reason is valid: '{reason[:50]}'")

            # Book appointment
            logger.info(
                f"📝 Booking appointment: patient={patient_user_id}, "
                f"slot={selected_slot.date} {selected_slot.start_time}-{selected_slot.end_time}, "
                f"reason={reason[:50]}"
            )
            appointment = await self.appointment_service.book_appointment(
                patient_user_id=patient_user_id,
                selected_slot=selected_slot,
                reason=reason,
                created_by_phone=created_by_phone,
                session=session,
            )
            logger.info(
                f"✅ Appointment booked successfully! "
                f"ID: {appointment.id}, Status: {appointment.status}"
            )

            # Format confirmation
            confirmation_message = self.appointment_service.format_confirmation(appointment)

            return (ConversationStateEnum.APPOINTMENT_CONFIRMED, confirmation_message)

        except InvalidReasonError as e:
            # Invalid reason; re-prompt
            logger.warning(f"⚠️ Invalid reason: {e}")
            message = f"{str(e)}\n\nIntenta de nuevo:"
            return (ConversationStateEnum.AWAITING_REASON_TEXT, message)

        except SlotAlreadyBookedError as e:
            # Concurrent booking; fetch fresh slots
            logger.warning(f"🔄 Slot already booked, fetching fresh slots: {e}")
            _, slots_message, _ = await self.fetch_and_show_slots()
            message = f"{str(e)}\n\n{slots_message}"
            return (ConversationStateEnum.AWAITING_SLOT_SELECTION, message)

        except Exception as e:
            logger.error(
                f"💥 Unexpected error booking appointment: {type(e).__name__}: {e}",
                exc_info=True
            )
            message = "Error al registrar el turno. Intenta de nuevo o contacta a la secretaria."
            return (ConversationStateEnum.AWAITING_MENU, message)
