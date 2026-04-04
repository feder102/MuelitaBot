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
            self.google_client = GoogleCalendarClient(
                credentials_dict=settings.google_calendar_credentials,
                calendar_id=settings.google_calendar_id,
            )
            self.appointment_service = AppointmentService(
                google_calendar_client=self.google_client,
                clinic_timezone=settings.clinic_timezone,
                reason_max_length=settings.appointment_reason_max_length,
            )
        except ValueError as e:
            logger.warning(f"Google Calendar not configured: {e}")
            self.google_client = None
            self.appointment_service = None

    async def fetch_and_show_slots(self) -> tuple[ConversationStateEnum, str, list[AvailableSlot]]:
        """Fetch available slots and format for user display.

        Called when user selects "1" (Solicitar turno).

        Returns:
            (new_state, message, available_slots)
        """
        if not self.appointment_service:
            return (
                ConversationStateEnum.AWAITING_MENU,
                "Sistema de turnos no disponible. Contacta a la secretaria.",
                [],
            )

        try:
            # Fetch tomorrow to next week
            tomorrow = date.today() + timedelta(days=1)
            next_week = tomorrow + timedelta(days=7)

            slots, message = await self.appointment_service.fetch_and_display_slots(
                date_start=tomorrow, date_end=next_week
            )

            if not slots:
                return (
                    ConversationStateEnum.AWAITING_MENU,
                    message,
                    [],
                )

            return (ConversationStateEnum.AWAITING_SLOT_SELECTION, message, slots)

        except GoogleCalendarError as e:
            logger.error(f"Google Calendar error: {e}")
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
            reason = self.appointment_service.validate_reason(user_input)

            # Book appointment
            appointment = await self.appointment_service.book_appointment(
                patient_user_id=patient_user_id,
                selected_slot=selected_slot,
                reason=reason,
                created_by_phone=created_by_phone,
                session=session,
            )

            # Format confirmation
            confirmation_message = self.appointment_service.format_confirmation(appointment)

            return (ConversationStateEnum.APPOINTMENT_CONFIRMED, confirmation_message)

        except InvalidReasonError as e:
            # Invalid reason; re-prompt
            message = f"{str(e)}\n\nIntenta de nuevo:"
            return (ConversationStateEnum.AWAITING_REASON_TEXT, message)

        except SlotAlreadyBookedError as e:
            # Concurrent booking; fetch fresh slots
            _, slots_message, _ = await self.fetch_and_show_slots()
            message = f"{str(e)}\n\n{slots_message}"
            return (ConversationStateEnum.AWAITING_SLOT_SELECTION, message)

        except Exception as e:
            logger.error(f"Unexpected error booking appointment: {e}")
            message = "Error al registrar el turno. Intenta de nuevo o contacta a la secretaria."
            return (ConversationStateEnum.AWAITING_MENU, message)
