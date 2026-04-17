"""Cancellation flow router and state machine for Feature 004."""
from datetime import datetime, timezone, date as date_type
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.config import settings
from src.models.appointment import Appointment, AppointmentStatusEnum
from src.models.audit_log import AuditLog, AuditActionEnum, AuditStatusEnum
from src.models.conversation_state import ConversationStateEnum
from src.models.telegram_user import TelegramUser
from src.services.dentist_service import DentistService
from src.services.google_calendar_client import (
    GoogleCalendarClient,
    GoogleCalendarError,
)
from src.services.appointment_service import AppointmentService
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CancellationRouter:
    """Route and handle appointment cancellation state transitions.

    Follows the same pattern as AppointmentRouter: each method returns
    (new_state, message, context_data) and the caller (WebhookHandler)
    is responsible for persisting state and sending the message.
    """

    def __init__(self):
        """Initialize cancellation router with required services."""
        try:
            self.google_client = GoogleCalendarClient(
                credentials_dict=settings.google_calendar_credentials,
                calendar_id=settings.google_calendar_id,
            )
            self.dentist_service = DentistService()
            logger.info("✅ CancellationRouter initialized")
        except Exception as e:
            logger.error(
                f"❌ Failed to initialize CancellationRouter: {type(e).__name__}: {e}",
                exc_info=True,
            )
            self.google_client = None
            self.dentist_service = None

    # ------------------------------------------------------------------
    # Step 1 — User selects "3" from main menu
    # ------------------------------------------------------------------

    async def handle_cancellation_request(
        self,
        session: AsyncSession,
        user: TelegramUser,
    ) -> tuple[ConversationStateEnum, str, dict]:
        """Entry point when the patient selects 'Cancelar turno' (option 3).

        Fetches all upcoming PENDING appointments for this patient.
        - Zero appointments  → empty-state message, return to AWAITING_MENU.
        - One or more        → numbered list, move to SELECTING_CANCELLATION_APPOINTMENT.

        Returns:
            (new_state, message, context_data)
        """
        logger.info(f"📋 handle_cancellation_request() for user {user.id}")

        try:
            now_utc = datetime.now(timezone.utc)
            today = now_utc.date()
            now_time = now_utc.time()

            stmt = (
                select(Appointment)
                .options(joinedload(Appointment.dentist))
                .where(
                    Appointment.patient_user_id == user.id,
                    Appointment.status == AppointmentStatusEnum.PENDING,
                    # Only future appointments
                    (Appointment.appointment_date > today)
                    | (
                        (Appointment.appointment_date == today)
                        & (Appointment.start_time > now_time)
                    ),
                )
                .order_by(Appointment.appointment_date, Appointment.start_time)
            )
            result = await session.execute(stmt)
            appointments = result.scalars().all()

            # US3: No upcoming appointments
            if not appointments:
                logger.info(f"⚠️ No upcoming appointments for user {user.id}")
                from src.services.menu_router import MenuRouter
                message = (
                    "No tenés turnos próximos para cancelar.\n\n"
                    + MenuRouter.MENU_MESSAGE
                )
                return (ConversationStateEnum.AWAITING_MENU, message, {})

            # US1 + US2: Build numbered list
            cancellable = []
            list_lines = ["Tus turnos próximos:\n"]
            for i, appt in enumerate(appointments, start=1):
                dentist_name = appt.dentist.name if appt.dentist else "Odontólogo"
                date_display = AppointmentService._format_date_spanish(appt.appointment_date)
                time_str = appt.start_time.strftime("%H:%M")

                list_lines.append(f"{i}️⃣ {dentist_name} — {date_display} a las {time_str}")
                cancellable.append(
                    {
                        "index": i,
                        "appointment_id": str(appt.id),
                        "dentist_name": dentist_name,
                        "appointment_date": appt.appointment_date.isoformat(),
                        "start_time": time_str,
                        "google_event_id": appt.google_event_id,
                        "dentist_id": str(appt.dentist_id) if appt.dentist_id else None,
                    }
                )

            list_lines.append(
                "\n¿Cuál turno querés cancelar? Respondé con el número."
            )
            message = "\n".join(list_lines)

            context_data = {"cancellable_appointments": cancellable}
            logger.info(
                f"✅ Showing {len(cancellable)} cancellable appointment(s) to user {user.id}"
            )
            return (
                ConversationStateEnum.SELECTING_CANCELLATION_APPOINTMENT,
                message,
                context_data,
            )

        except Exception as e:
            logger.error(
                f"💥 Unexpected error in handle_cancellation_request: {type(e).__name__}: {e}",
                exc_info=True,
            )
            from src.services.menu_router import MenuRouter
            message = (
                "Error al obtener tus turnos. Intentá de nuevo o contactá a la secretaria.\n\n"
                + MenuRouter.MENU_MESSAGE
            )
            return (ConversationStateEnum.AWAITING_MENU, message, {})

    # ------------------------------------------------------------------
    # Step 2 — User sends appointment number (US2 selection path)
    # ------------------------------------------------------------------

    async def validate_appointment_selection(
        self,
        user_input: str,
        context_data: dict,
    ) -> tuple[ConversationStateEnum, str, dict]:
        """Validate the patient's numeric appointment selection.

        Called when state == SELECTING_CANCELLATION_APPOINTMENT.

        Returns:
            (new_state, message, context_data_update)
        """
        cancellable = context_data.get("cancellable_appointments", [])
        n = len(cancellable)

        try:
            idx = int(user_input.strip())
        except ValueError:
            logger.warning(f"⚠️ Non-numeric input during appointment selection: '{user_input}'")
            message = (
                f"Por favor respondé con un número entre 1 y {n}."
            )
            return (
                ConversationStateEnum.SELECTING_CANCELLATION_APPOINTMENT,
                message,
                {},
            )

        if idx < 1 or idx > n:
            logger.warning(f"⚠️ Out-of-range selection: {idx} (valid: 1-{n})")
            message = (
                f"Selección inválida. Por favor respondé con un número entre 1 y {n}."
            )
            return (
                ConversationStateEnum.SELECTING_CANCELLATION_APPOINTMENT,
                message,
                {},
            )

        selected = cancellable[idx - 1]
        dentist_name = selected["dentist_name"]
        date_display = AppointmentService._format_date_spanish(
            date_type.fromisoformat(selected["appointment_date"])
        )
        time_str = selected["start_time"]

        message = (
            f"¿Confirmás que querés cancelar el siguiente turno?\n\n"
            f"📅 {dentist_name} — {date_display} a las {time_str}\n\n"
            f"Respondé *si* para confirmar o *no* para volver al menú."
        )

        context_update = {"appointment_to_cancel": selected}
        logger.info(
            f"✅ Appointment selected for cancellation: {selected['appointment_id']}"
        )
        return (
            ConversationStateEnum.AWAITING_CANCELLATION_CONFIRMATION,
            message,
            context_update,
        )

    # ------------------------------------------------------------------
    # Step 3 — User confirms or aborts
    # ------------------------------------------------------------------

    async def confirm_and_cancel_appointment(
        self,
        session: AsyncSession,
        user: TelegramUser,
        confirmation: str,
        context_data: dict,
    ) -> tuple[ConversationStateEnum, str]:
        """Execute or abort the cancellation based on the patient's confirmation.

        Called when state == AWAITING_CANCELLATION_CONFIRMATION.

        Args:
            session: Database session
            user: The TelegramUser making the request
            confirmation: "si" or "no" (already normalized by MessageParser)
            context_data: Current conversation context; must contain 'appointment_to_cancel'

        Returns:
            (new_state, message)  — always returns to AWAITING_MENU
        """
        from src.services.menu_router import MenuRouter

        if confirmation == "no":
            logger.info(f"User {user.id} aborted cancellation")
            message = "Cancelación descartada. Volvés al menú principal.\n\n" + MenuRouter.MENU_MESSAGE
            return (ConversationStateEnum.AWAITING_MENU, message)

        if confirmation != "si":
            # Unexpected input — keep state
            message = (
                "Por favor respondé *si* para confirmar la cancelación o *no* para volver al menú."
            )
            return (ConversationStateEnum.AWAITING_CANCELLATION_CONFIRMATION, message)

        # --- confirmation == "si" ---
        appt_data = context_data.get("appointment_to_cancel")
        if not appt_data:
            logger.error(f"⚠️ No appointment_to_cancel in context_data for user {user.id}")
            message = (
                "Ocurrió un error. Volvés al menú principal.\n\n" + MenuRouter.MENU_MESSAGE
            )
            return (ConversationStateEnum.AWAITING_MENU, message)

        appointment_id_str = appt_data.get("appointment_id")
        try:
            appointment_uuid = UUID(appointment_id_str)
        except (TypeError, ValueError):
            logger.error(f"⚠️ Invalid appointment_id in context: {appointment_id_str}")
            message = (
                "Ocurrió un error. Volvés al menú principal.\n\n" + MenuRouter.MENU_MESSAGE
            )
            return (ConversationStateEnum.AWAITING_MENU, message)

        try:
            # Fetch the appointment, verifying ownership and status atomically
            stmt = (
                select(Appointment)
                .options(joinedload(Appointment.dentist))
                .where(
                    Appointment.id == appointment_uuid,
                    Appointment.patient_user_id == user.id,
                    Appointment.status == AppointmentStatusEnum.PENDING,
                )
            )
            result = await session.execute(stmt)
            appointment = result.scalars().first()

            if appointment is None:
                logger.warning(
                    f"⚠️ Appointment {appointment_uuid} not found, wrong owner, "
                    f"or already cancelled for user {user.id}"
                )
                message = (
                    "No se pudo cancelar el turno. "
                    "Es posible que ya haya sido cancelado. "
                    "Si necesitás ayuda, contactá a la secretaria.\n\n"
                    + MenuRouter.MENU_MESSAGE
                )
                return (ConversationStateEnum.AWAITING_MENU, message)

            # Store details before cancelling (for response message)
            dentist_name = appointment.dentist.name if appointment.dentist else "Odontólogo"
            date_display = AppointmentService._format_date_spanish(appointment.appointment_date)
            time_str = appointment.start_time.strftime("%H:%M")
            google_event_id = appointment.google_event_id
            dentist_calendar_id = appointment.dentist.calendar_id if appointment.dentist else None

            # Cancel in database
            appointment.status = AppointmentStatusEnum.CANCELLED
            appointment.updated_at = datetime.utcnow()
            await session.flush()
            logger.info(f"✓ Appointment {appointment_uuid} marked as CANCELLED in DB")

            # Delete from Google Calendar (best-effort)
            if dentist_calendar_id and self.google_client:
                # If no stored event ID, look it up by date/time in the calendar
                effective_event_id = google_event_id
                if not effective_event_id:
                    logger.info(
                        f"No google_event_id stored — searching calendar by date/time "
                        f"for appointment {appointment_uuid}"
                    )
                    effective_event_id = await self._find_event_id_by_time(
                        calendar_id=dentist_calendar_id,
                        appt_date=appointment.appointment_date,
                        start_time=appointment.start_time,
                    )
                    if effective_event_id:
                        logger.info(f"✓ Found event by time lookup: {effective_event_id}")
                    else:
                        logger.warning(
                            f"⚠️ Could not find calendar event for appointment "
                            f"{appointment_uuid} — skipping calendar delete"
                        )

                if effective_event_id:
                    try:
                        await self.google_client.delete_event(
                            calendar_id=dentist_calendar_id,
                            event_id=effective_event_id,
                        )
                        logger.info(
                            f"✓ Google Calendar event {effective_event_id} deleted "
                            f"from calendar {dentist_calendar_id}"
                        )
                    except GoogleCalendarError as e:
                        logger.warning(
                            f"⚠️ Calendar delete failed for event {effective_event_id}: {e}. "
                            "DB cancellation still applied."
                        )

            # Write audit log
            audit = AuditLog(
                user_id=user.id,
                action=AuditActionEnum.APPOINTMENT_CANCELLED,
                status=AuditStatusEnum.SUCCESS,
                message_text=f"appointment_id={appointment_uuid}",
                response_text=f"Cancelled by patient via Telegram",
            )
            session.add(audit)
            await session.flush()

            message = (
                f"✅ Tu turno del {date_display} a las {time_str} con {dentist_name} "
                f"fue cancelado exitosamente.\n\n"
                + MenuRouter.MENU_MESSAGE
            )
            logger.info(
                f"✅ Cancellation complete for user {user.id}, appointment {appointment_uuid}"
            )
            return (ConversationStateEnum.AWAITING_MENU, message)

        except Exception as e:
            logger.error(
                f"💥 Unexpected error in confirm_and_cancel_appointment: "
                f"{type(e).__name__}: {e}",
                exc_info=True,
            )
            message = (
                "Error al cancelar el turno. Intentá de nuevo o contactá a la secretaria.\n\n"
                + MenuRouter.MENU_MESSAGE
            )
            return (ConversationStateEnum.AWAITING_MENU, message)

    # ------------------------------------------------------------------
    # Helper — find calendar event ID by appointment date/time
    # ------------------------------------------------------------------

    async def _find_event_id_by_time(
        self,
        calendar_id: str,
        appt_date,
        start_time,
    ) -> str | None:
        """Search Google Calendar for an event matching the given date and start time.

        Used as a fallback when google_event_id was not stored (pre-migration appointments).

        Returns the event ID string, or None if no matching event is found.
        """
        import asyncio
        from datetime import datetime, timedelta
        import pytz

        try:
            service = self.google_client._get_service()

            # The appointment time is stored in clinic local time (Argentina, UTC-3).
            # Google Calendar API timeMin/timeMax require RFC3339 — we must include the
            # timezone offset so the search window aligns with the actual event time.
            clinic_tz = pytz.timezone(settings.clinic_timezone)
            dt_local = clinic_tz.localize(datetime.combine(appt_date, start_time))
            time_min = (dt_local - timedelta(minutes=1)).isoformat()
            time_max = (dt_local + timedelta(minutes=1)).isoformat()

            loop = asyncio.get_event_loop()
            request = service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
            )
            result = await asyncio.wait_for(
                loop.run_in_executor(None, request.execute), timeout=10.0
            )

            events = result.get("items", [])
            if events:
                event_id = events[0].get("id")
                logger.info(
                    f"Found {len(events)} event(s) at {dt_local.isoformat()}; "
                    f"using first: {event_id}"
                )
                return event_id

            logger.warning(f"No calendar event found at {dt_local.isoformat()} in {calendar_id}")
            return None

        except Exception as e:
            logger.warning(f"⚠️ Calendar time lookup failed: {type(e).__name__}: {e}")
            return None
