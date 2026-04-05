"""Appointment service for appointment booking feature."""
import pytz
from datetime import date, time, datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, and_

from src.models.appointment import Appointment, AppointmentStatusEnum
from src.schemas.appointment import AvailableSlot
from src.services.google_calendar_client import (
    GoogleCalendarClient,
    GoogleCalendarError,
    GoogleCalendarTimeoutError,
)
from src.services.slot_generator import SlotGenerator
from src.services.dentist_service import DentistService, DentistNotFoundError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class InvalidSlotError(Exception):
    """Raised when user selects an invalid slot number."""

    pass


class SlotAlreadyBookedError(Exception):
    """Raised when attempting to book an already-booked slot (concurrent booking)."""

    pass


class InvalidReasonError(Exception):
    """Raised when appointment reason is invalid."""

    pass


class AppointmentService:
    """Service for appointment booking flow orchestration.

    Coordinates Google Calendar fetching, slot display, validation, and storage.
    """

    def __init__(
        self,
        google_calendar_client: GoogleCalendarClient,
        dentist_service: Optional[DentistService] = None,
        clinic_timezone: str = "America/Argentina/Buenos_Aires",
        reason_max_length: int = 150,
    ):
        """Initialize appointment service.

        Args:
            google_calendar_client: Initialized GoogleCalendarClient
            dentist_service: DentistService for multi-dentist support (optional)
            clinic_timezone: Timezone for clinic (default Argentina)
            reason_max_length: Maximum characters for consultation reason
        """
        self.google_calendar_client = google_calendar_client
        self.dentist_service = dentist_service
        self.clinic_timezone_str = clinic_timezone  # Keep as string for Google Calendar
        self.clinic_timezone = pytz.timezone(clinic_timezone)
        self.reason_max_length = reason_max_length

    async def fetch_and_display_slots(
        self,
        date_start: Optional[date] = None,
        date_end: Optional[date] = None,
        session: Optional[AsyncSession] = None,
        dentist_id: Optional[UUID] = None,
    ) -> tuple[list[AvailableSlot], str]:
        """Fetch available and booked slots and format for Telegram display.

        Args:
            date_start: Start date for slot search (default: today)
            date_end: End date for slot search (default: today + 7 days)
            session: Database session for fetching appointments
            dentist_id: UUID of dentist (for multi-dentist support). If provided,
                       filters appointments to this dentist's calendar only.

        Returns:
            (available_slots_only, formatted_message_text)

        Raises:
            GoogleCalendarError: If calendar fetch fails
            DentistNotFoundError: If dentist_id provided but not found
        """
        # Set defaults
        today = datetime.now().date()
        if date_start is None:
            date_start = today + timedelta(days=1)  # Tomorrow
        if date_end is None:
            date_end = date_start + timedelta(days=7)

        try:
            # Get calendar_id for dentist if specified
            calendar_id = None
            if dentist_id and self.dentist_service and session:
                calendar_id = await self.dentist_service.get_dentist_calendar_id(session, dentist_id)

            # Fetch all appointments from database
            database_appointments = []
            if session:
                query_conditions = [
                    Appointment.appointment_date >= date_start,
                    Appointment.appointment_date <= date_end,
                    Appointment.status == AppointmentStatusEnum.PENDING
                ]
                # Filter by dentist_id if provided (multi-dentist support)
                if dentist_id:
                    query_conditions.append(Appointment.dentist_id == dentist_id)

                stmt = select(Appointment).where(and_(*query_conditions))
                result = await session.execute(stmt)
                db_appts = result.scalars().all()
                database_appointments = [
                    {
                        "appointment_date": appt.appointment_date,
                        "start_time": appt.start_time,
                        "end_time": appt.end_time,
                    }
                    for appt in db_appts
                ]

            # Fetch ALL slots (available + booked) from Google Calendar + DB
            all_slots = await self.google_calendar_client.get_all_slots(
                date_start=date_start,
                date_end=date_end,
                database_appointments=database_appointments,
                business_hours=(time(8, 0), time(13, 0)),
                timezone_str=self.clinic_timezone_str,
                calendar_id=calendar_id,  # Pass specific calendar_id for multi-dentist
            )

            if not all_slots:
                return [], "No hay turnos disponibles en este momento. Contáctanos."

            # Separate available and booked slots
            available_slots = [s for s in all_slots if not s['is_booked']]
            booked_slots = [s for s in all_slots if s['is_booked']]

            if not available_slots:
                return [], "No hay turnos disponibles en este momento. Contáctanos."

            # Format available slots for selection (numbered 1, 2, 3...)
            display_slots = []
            for i, slot in enumerate(available_slots, start=1):
                slot_date = slot["date"]
                slot_start = slot["start_time"]
                slot_end = slot["end_time"]

                # Format date in Spanish (e.g., "Lunes 08 de Abril")
                date_display = self._format_date_spanish(slot_date)
                # Format time (e.g., "08:00-09:00")
                time_display = f"{slot_start.strftime('%H:%M')}-{slot_end.strftime('%H:%M')}"

                display_slot = AvailableSlot(
                    slot_number=i,
                    date=slot_date,
                    date_display=date_display,
                    time_display=time_display,
                    start_time=slot_start,
                    end_time=slot_end,
                )
                display_slots.append(display_slot)

            # Format message for Telegram showing ALL slots (available + booked)
            message = "Disponibilidad de turnos:\n"

            # Show all slots in chronological order with status
            slot_counter = 1
            for slot in all_slots:
                slot_date = slot["date"]
                slot_start = slot["start_time"]
                slot_end = slot["end_time"]
                is_booked = slot["is_booked"]

                date_display = self._format_date_spanish(slot_date)
                time_display = f"{slot_start.strftime('%H:%M')}-{slot_end.strftime('%H:%M')}"

                if is_booked:
                    message += f"❌ {date_display}, {time_display} - Ocupado\n"
                else:
                    message += f"{slot_counter}. {date_display}, {time_display} ✅\n"
                    slot_counter += 1

            message += f"\nEscoge el turno deseado (1-{len(display_slots)}):"

            logger.info(f"Generated {len(display_slots)} available slots, {len(booked_slots)} booked for display")
            return display_slots, message

        except GoogleCalendarTimeoutError:
            logger.warning("Calendar timeout, returning cached slots or error")
            return [], "Sistema de turnos no disponible en este momento. Intenta en unos minutos."
        except GoogleCalendarError as e:
            logger.error(f"Calendar error: {e}")
            return [], "Sistema de turnos no disponible en este momento. Contacta a la secretaria."

    def validate_slot_selection(
        self, slot_number: str, available_slots: list[AvailableSlot]
    ) -> int:
        """Validate user's slot selection.

        Args:
            slot_number: User-provided slot number as string
            available_slots: List of available slots displayed to user

        Returns:
            0-based index into available_slots

        Raises:
            InvalidSlotError: If slot selection is invalid
        """
        try:
            slot_idx = int(slot_number)
        except ValueError:
            raise InvalidSlotError(f"Turno inválido: '{slot_number}' no es un número")

        if slot_idx < 1 or slot_idx > len(available_slots):
            raise InvalidSlotError(
                f"Turno inválido. Elige un número entre 1 y {len(available_slots)}."
            )

        return slot_idx - 1  # Convert to 0-based index

    def validate_reason(self, reason: str) -> str:
        """Validate appointment reason.

        Args:
            reason: Consultation reason text

        Returns:
            Stripped reason text

        Raises:
            InvalidReasonError: If reason is invalid
        """
        reason = reason.strip()

        if not reason:
            raise InvalidReasonError("El motivo no puede estar vacío.")

        if len(reason) > self.reason_max_length:
            raise InvalidReasonError(
                f"El motivo es muy largo (máx {self.reason_max_length} caracteres)."
            )

        return reason

    async def book_appointment(
        self,
        patient_user_id: int,
        selected_slot: AvailableSlot,
        reason: str,
        dentist_id: Optional[UUID] = None,
        created_by_user_id: Optional[int] = None,
        created_by_phone: Optional[str] = None,
        session: Optional[AsyncSession] = None,
    ) -> Appointment:
        """Book an appointment in the database and create event in Google Calendar.

        Args:
            patient_user_id: Telegram user ID of patient
            selected_slot: Selected AvailableSlot object
            reason: Consultation reason (already validated)
            dentist_id: UUID of dentist (required for multi-dentist support)
            created_by_user_id: Optional staff user ID who created appointment
            created_by_phone: Optional staff phone number
            session: Database session

        Returns:
            Appointment object (saved to DB)

        Raises:
            SlotAlreadyBookedError: If slot was booked by another user (concurrent)
            DentistNotFoundError: If dentist_id is provided but not found
            Exception: For other database errors
        """
        try:
            # Validate dentist if provided
            calendar_id = None
            if dentist_id and self.dentist_service and session:
                calendar_id = await self.dentist_service.get_dentist_calendar_id(session, dentist_id)

            # Create appointment record
            appointment = Appointment(
                patient_user_id=patient_user_id,
                dentist_id=dentist_id,
                appointment_date=selected_slot.date,
                start_time=selected_slot.start_time,
                end_time=selected_slot.end_time,
                reason=reason,
                created_by_user_id=created_by_user_id,
                created_by_phone=created_by_phone,
                status=AppointmentStatusEnum.PENDING,
            )

            if session:
                session.add(appointment)
                await session.flush()  # Check constraints before commit

            logger.info(f"✓ Appointment saved to DB: {appointment.id}")

            # Create event in Google Calendar
            logger.info(f"🔗 About to create Google Calendar event...")
            try:
                logger.info(
                    f"📅 Creating Google Calendar event: "
                    f"date={selected_slot.date}, "
                    f"time={selected_slot.start_time}-{selected_slot.end_time}, "
                    f"reason={reason[:50]}"
                )
                google_event = await self.google_calendar_client.create_event(
                    summary=f"Cita: {reason[:50]}",
                    date_start=selected_slot.date,
                    time_start=selected_slot.start_time,
                    time_end=selected_slot.end_time,
                    description=f"Paciente: {patient_user_id}\nMotivo: {reason}",
                    timezone=self.clinic_timezone_str,
                    calendar_id=calendar_id,  # Pass dentist's calendar_id if multi-dentist
                )
                event_id = google_event.get('id')
                event_link = google_event.get('htmlLink', '')
                logger.info(
                    f"✅ Google Calendar event created successfully! "
                    f"Event ID: {event_id}, "
                    f"Link: {event_link}"
                )
            except Exception as e:
                logger.error(
                    f"❌ Failed to create Google Calendar event: {type(e).__name__}: {e}",
                    exc_info=True
                )
                # Don't fail the booking if calendar creation fails

            logger.info(
                f"Booked appointment for user {patient_user_id} on "
                f"{selected_slot.date} {selected_slot.start_time} (reason: {reason[:50]}...)"
            )
            return appointment

        except IntegrityError as e:
            # Rollback session to recover from error state
            if session:
                await session.rollback()

            # Handle UNIQUE constraint violation (concurrent booking)
            if "uq_appointment_slot" in str(e):
                logger.warning(f"Concurrent booking detected for {selected_slot.start_time}")
                raise SlotAlreadyBookedError(
                    f"Turno ya fue reservado. Elige otro:"
                )
            # Re-raise for other constraint violations
            raise

    def format_confirmation(
        self, appointment: Appointment, clinic_timezone_str: str = "America/Argentina/Buenos_Aires"
    ) -> str:
        """Format appointment confirmation message for Telegram.

        Args:
            appointment: Appointment object with booking details
            clinic_timezone_str: Timezone for display conversion

        Returns:
            Formatted confirmation message in Spanish
        """
        # Format date (day name + date)
        date_display = self._format_date_spanish(appointment.appointment_date)

        # Format time range
        time_display = f"{appointment.start_time.strftime('%H:%M')}-{appointment.end_time.strftime('%H:%M')}"

        message = (
            f"✅ Tu turno ha sido confirmado:\n"
            f"{date_display}, {time_display}\n"
            f"Motivo: {appointment.reason}\n\n"
            f"¿Deseas volver al menú principal?"
        )

        return message

    @staticmethod
    def _format_date_spanish(date_obj: date) -> str:
        """Format date in Spanish (e.g., "Lunes 08 de Abril").

        Args:
            date_obj: Date to format

        Returns:
            Spanish-formatted date string
        """
        day_names = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        month_names = [
            "enero",
            "febrero",
            "marzo",
            "abril",
            "mayo",
            "junio",
            "julio",
            "agosto",
            "septiembre",
            "octubre",
            "noviembre",
            "diciembre",
        ]

        day_name = day_names[date_obj.weekday()]
        month_name = month_names[date_obj.month - 1]

        return f"{day_name} {date_obj.day:02d} de {month_name}"
