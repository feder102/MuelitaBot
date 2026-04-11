"""Appointment booking flow router and state machine."""
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, timedelta
from uuid import UUID

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
from src.services.dentist_service import DentistService, DentistNotFoundError
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

            # Initialize DentistService (for multi-dentist support)
            self.dentist_service = DentistService()
            logger.info(f"✓ DentistService initialized")

            self.appointment_service = AppointmentService(
                google_calendar_client=self.google_client,
                dentist_service=self.dentist_service,
                clinic_timezone=settings.clinic_timezone,
                reason_max_length=settings.appointment_reason_max_length,
            )
            logger.info(f"✓ AppointmentService initialized with multi-dentist support")
        except ValueError as e:
            logger.error(f"❌ ValueError initializing AppointmentRouter: {e}")
            self.google_client = None
            self.appointment_service = None
            self.dentist_service = None
        except Exception as e:
            logger.error(f"❌ Unexpected error initializing AppointmentRouter: {type(e).__name__}: {e}", exc_info=True)
            self.google_client = None
            self.appointment_service = None
            self.dentist_service = None

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
        dentist_id: UUID | None = None,
        created_by_phone: str | None = None,
        session: AsyncSession | None = None,
    ) -> tuple[ConversationStateEnum, str]:
        """Validate reason and book appointment.

        Called when user provides consultation reason.

        Args:
            user_input: Consultation reason provided by user
            patient_user_id: Telegram user ID
            selected_slot: Selected appointment slot
            dentist_id: UUID of selected dentist (for multi-dentist support)
            created_by_phone: Optional staff phone number
            session: Database session

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
                dentist_id=dentist_id,  # Multi-dentist support
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

    async def handle_appointment_request(self, session: AsyncSession) -> tuple[ConversationStateEnum, str, dict]:
        """
        Handle user selecting "1" (appointment) from main menu.

        Checks available dentists and either auto-selects (single) or shows menu (multiple).

        Args:
            session: Database session

        Returns:
            (new_state, message, context_data)
            - If single dentist: (AWAITING_SLOT_SELECTION, slots_message, {selected_dentist_id: ...})
            - If multiple dentists: (SELECTING_DENTIST, dentist_menu_message, {available_dentists: [...]})
            - If no dentists: (AWAITING_MENU, error_message, {})
        """
        logger.info("📋 handle_appointment_request() called - user selected option 1 (appointment)")

        try:
            if not self.dentist_service:
                logger.error("❌ dentist_service is None")
                return (
                    ConversationStateEnum.AWAITING_MENU,
                    "Sistema de turnos no disponible. Contacta a la secretaria.",
                    {},
                )

            # Get active dentists
            dentists = await self.dentist_service.get_active_dentists(session)
            logger.info(f"Found {len(dentists)} active dentists")

            if len(dentists) == 0:
                logger.warning("⚠️ No dentists available")
                return (
                    ConversationStateEnum.AWAITING_MENU,
                    "Lo sentimos, no hay doctores disponibles en este momento.\nPor favor, contacta a nuestra secretaria para más información.",
                    {},
                )

            if len(dentists) == 1:
                # Auto-select single dentist
                dentist = dentists[0]
                logger.info(f"✓ Single dentist found, auto-selecting: {dentist.name}")

                # Fetch and show slots for this dentist
                tomorrow = date.today() + timedelta(days=1)
                next_week = tomorrow + timedelta(days=7)

                slots, message = await self.appointment_service.fetch_and_display_slots(
                    date_start=tomorrow,
                    date_end=next_week,
                    session=session,
                    dentist_id=dentist.id,  # Multi-dentist support
                )

                if not slots:
                    logger.warning(f"⚠️ No slots available for {dentist.name}")
                    return (
                        ConversationStateEnum.AWAITING_MENU,
                        message,
                        {},
                    )

                context_data = {"selected_dentist_id": str(dentist.id)}
                return (ConversationStateEnum.AWAITING_SLOT_SELECTION, message, context_data)

            # Multiple dentists - show selection menu
            logger.info(f"📋 Showing dentist selection menu for {len(dentists)} dentists")
            dentist_list = "\n".join(
                f"{i + 1}. {d.name}" for i, d in enumerate(dentists)
            )
            message = f"¿A qué odontólogo deseas pedir turno?\n\n{dentist_list}"

            context_data = {
                "available_dentists": [str(d.id) for d in dentists],
                "dentist_names": {str(d.id): d.name for d in dentists},
            }
            return (ConversationStateEnum.SELECTING_DENTIST, message, context_data)

        except Exception as e:
            logger.error(
                f"💥 Unexpected error in handle_appointment_request: {type(e).__name__}: {e}",
                exc_info=True,
            )
            return (
                ConversationStateEnum.AWAITING_MENU,
                "Sistema de turnos no disponible. Intenta de nuevo o contacta a la secretaria.",
                {},
            )

    async def handle_dentist_selected(
        self,
        session: AsyncSession,
        user_input: str,
        available_dentist_ids: list[str],
        dentist_names: dict[str, str],
    ) -> tuple[ConversationStateEnum, str, dict]:
        """
        Handle user selecting a dentist from the dentist menu.

        Args:
            session: Database session
            user_input: User's selection (e.g., "1", "2")
            available_dentist_ids: List of available dentist IDs (from context)
            dentist_names: Mapping of dentist ID to name (from context)

        Returns:
            (new_state, message, context_data)
        """
        logger.info(f"🔍 handle_dentist_selected() called with input: '{user_input}'")

        try:
            # Parse selection
            try:
                selection_idx = int(user_input) - 1
            except ValueError:
                logger.warning(f"⚠️ Invalid selection (not a number): '{user_input}'")
                dentist_list = "\n".join(
                    f"{i + 1}. {dentist_names.get(did, 'Unknown')}"
                    for i, did in enumerate(available_dentist_ids)
                )
                message = f"Opción inválida. Por favor, selecciona un número válido.\n\n¿A qué odontólogo deseas pedir turno?\n\n{dentist_list}"
                return (ConversationStateEnum.SELECTING_DENTIST, message, {})

            # Validate selection is in range
            if selection_idx < 0 or selection_idx >= len(available_dentist_ids):
                logger.warning(f"⚠️ Selection out of range: {selection_idx} (max: {len(available_dentist_ids) - 1})")
                dentist_list = "\n".join(
                    f"{i + 1}. {dentist_names.get(did, 'Unknown')}"
                    for i, did in enumerate(available_dentist_ids)
                )
                message = f"Opción inválida. Por favor, selecciona un número entre 1 y {len(available_dentist_ids)}.\n\n¿A qué odontólogo deseas pedir turno?\n\n{dentist_list}"
                return (ConversationStateEnum.SELECTING_DENTIST, message, {})

            # Get selected dentist
            selected_dentist_id = available_dentist_ids[selection_idx]
            selected_dentist_name = dentist_names.get(selected_dentist_id, "Unknown")
            logger.info(f"✓ Dentist selected: {selected_dentist_name} ({selected_dentist_id})")

            # Verify dentist is still active
            try:
                dentist = await self.dentist_service.get_dentist_by_id(session, UUID(selected_dentist_id))
            except DentistNotFoundError:
                logger.warning(f"⚠️ Selected dentist no longer available: {selected_dentist_id}")
                return (
                    ConversationStateEnum.AWAITING_MENU,
                    f"El odontólogo seleccionado ya no está disponible.\nPor favor, intenta de nuevo.",
                    {},
                )

            # Fetch and show slots for selected dentist
            tomorrow = date.today() + timedelta(days=1)
            next_week = tomorrow + timedelta(days=7)

            slots, message = await self.appointment_service.fetch_and_display_slots(
                date_start=tomorrow,
                date_end=next_week,
                session=session,
                dentist_id=dentist.id,  # Multi-dentist support
            )

            if not slots:
                logger.warning(f"⚠️ No slots available for {selected_dentist_name}")
                return (
                    ConversationStateEnum.AWAITING_MENU,
                    message,
                    {},
                )

            context_data = {"selected_dentist_id": selected_dentist_id}
            return (ConversationStateEnum.AWAITING_SLOT_SELECTION, message, context_data)

        except Exception as e:
            logger.error(
                f"💥 Unexpected error in handle_dentist_selected: {type(e).__name__}: {e}",
                exc_info=True,
            )
            return (
                ConversationStateEnum.AWAITING_MENU,
                "Error al seleccionar odontólogo. Intenta de nuevo.",
                {},
            )
