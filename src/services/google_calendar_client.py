"""Google Calendar API client for appointment booking feature."""
import asyncio
from datetime import date, time, datetime, timedelta
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.utils.logger import get_logger

logger = get_logger(__name__)


class GoogleCalendarError(Exception):
    """Base exception for Google Calendar errors."""

    pass


class GoogleCalendarAuthError(GoogleCalendarError):
    """Raised when Google Calendar authentication fails."""

    pass


class GoogleCalendarAPIError(GoogleCalendarError):
    """Raised when Google Calendar API call fails."""

    pass


class GoogleCalendarTimeoutError(GoogleCalendarError):
    """Raised when Google Calendar API call times out."""

    pass


class GoogleCalendarClient:
    """Client for Google Calendar API integration.

    Fetches availability from Google Calendar and generates appointment slots.
    """

    SCOPES = ["https://www.googleapis.com/auth/calendar"]  # Changed from readonly to allow writes
    MAX_RETRIES = 3
    RETRY_DELAYS = [1, 2, 4]  # Exponential backoff: 1s, 2s, 4s

    def __init__(self, credentials_dict: dict, calendar_id: str):
        """Initialize Google Calendar client.

        Args:
            credentials_dict: Service account credentials dict (from base64 decode)
            calendar_id: Google Calendar ID (e.g., medical-center@group.calendar.google.com)

        Raises:
            GoogleCalendarAuthError: If credentials are invalid
        """
        self.calendar_id = calendar_id

        try:
            self.credentials = Credentials.from_service_account_info(
                credentials_dict, scopes=self.SCOPES
            )
        except Exception as e:
            logger.error(f"Failed to create Google Calendar credentials: {e}")
            raise GoogleCalendarAuthError(f"Invalid credentials: {e}")

        # Service will be created lazily
        self.service = None

    def _get_service(self):
        """Get or create Google Calendar service."""
        if self.service is None:
            self.service = build("calendar", "v3", credentials=self.credentials)
        return self.service

    async def get_calendar_events(
        self, date_start: date, date_end: date, calendar_id: str = None
    ) -> list[dict]:
        """Fetch raw events from Google Calendar API.

        Args:
            date_start: Start date for event search
            date_end: End date for event search
            calendar_id: Optional specific calendar ID (overrides default)

        Returns:
            List of calendar event dicts with start, end, summary

        Raises:
            GoogleCalendarAPIError: If API call fails
            GoogleCalendarTimeoutError: If API call times out
        """
        service = self._get_service()

        # Use provided calendar_id or default
        effective_calendar_id = calendar_id if calendar_id else self.calendar_id

        # Build datetime boundaries (all day boundaries)
        time_min = datetime.combine(date_start, time.min).isoformat() + "Z"
        time_max = datetime.combine(date_end + timedelta(days=1), time.min).isoformat() + "Z"

        try:
            # Run API call in executor to avoid blocking
            loop = asyncio.get_event_loop()
            request = service.events().list(
                calendarId=effective_calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime",
            )

            result = await asyncio.wait_for(
                loop.run_in_executor(None, request.execute), timeout=10.0
            )

            events = result.get("items", [])
            logger.info(f"Fetched {len(events)} events from Google Calendar")
            return events

        except asyncio.TimeoutError:
            logger.warning("Google Calendar API call timed out")
            raise GoogleCalendarTimeoutError("Google Calendar API request timed out (>10s)")
        except HttpError as e:
            if e.resp.status == 401:
                logger.error(f"Google Calendar authentication failed: {e}")
                raise GoogleCalendarAuthError(f"Invalid credentials or access denied: {e}")
            elif e.resp.status == 429:
                logger.warning(f"Google Calendar API rate limit hit: {e}")
                raise GoogleCalendarAPIError(f"Rate limit exceeded: {e}")
            else:
                logger.error(f"Google Calendar API error: {e}")
                raise GoogleCalendarAPIError(f"API error ({e.resp.status}): {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching calendar events: {e}")
            raise GoogleCalendarAPIError(f"Unexpected error: {e}")

    async def get_available_slots(
        self,
        date_start: date,
        date_end: date,
        business_hours: tuple[time, time] = (time(8, 0), time(13, 0)),
        slot_duration_minutes: int = 60,
        timezone_str: str = "America/Argentina/Buenos_Aires",
    ) -> list[dict]:
        """Get available appointment slots from Google Calendar.

        Filters calendar events and generates free slots within business hours.

        Args:
            date_start: Start date for slot generation
            date_end: End date for slot generation
            business_hours: (start_time, end_time) tuple for clinic hours
            slot_duration_minutes: Duration of each slot (default 60 min)
            timezone_str: Clinic timezone for time calculations

        Returns:
            List of available slots with date, start_time, end_time

        Raises:
            GoogleCalendarAPIError: If calendar fetch fails
        """
        # Fetch events with retries
        events = await self._fetch_with_retry(date_start, date_end)

        # Import slot generator
        from src.services.slot_generator import SlotGenerator

        # Generate available slots
        slots = SlotGenerator.generate_available_slots(
            calendar_events=events,
            date_range=(date_start, date_end),
            business_hours=business_hours,
            slot_duration_minutes=slot_duration_minutes,
            timezone_str=timezone_str,
        )

        logger.info(f"Generated {len(slots)} available slots")
        return slots

    async def get_all_slots(
        self,
        date_start: date,
        date_end: date,
        database_appointments: list[dict] = None,
        business_hours: tuple[time, time] = (time(8, 0), time(13, 0)),
        slot_duration_minutes: int = 60,
        timezone_str: str = "America/Argentina/Buenos_Aires",
        calendar_id: str = None,
    ) -> list[dict]:
        """Get ALL appointment slots (available + booked).

        Returns slots with availability status from both Google Calendar and database.

        Args:
            date_start: Start date for slot generation
            date_end: End date for slot generation
            database_appointments: List of appointments from database
            business_hours: (start_time, end_time) tuple for clinic hours
            slot_duration_minutes: Duration of each slot (default 60 min)
            timezone_str: Clinic timezone for time calculations
            calendar_id: Optional specific calendar ID (overrides default)

        Returns:
            List of all slots with date, start_time, end_time, is_booked flag

        Raises:
            GoogleCalendarAPIError: If calendar fetch fails
        """
        # Use provided calendar_id or default
        effective_calendar_id = calendar_id if calendar_id else self.calendar_id

        # Fetch events with retries
        events = await self._fetch_with_retry(date_start, date_end, calendar_id=effective_calendar_id)

        # Import slot generator
        from src.services.slot_generator import SlotGenerator

        # Generate all slots (booked + available)
        slots = SlotGenerator.generate_all_slots(
            calendar_events=events,
            database_appointments=database_appointments or [],
            date_range=(date_start, date_end),
            business_hours=business_hours,
            slot_duration_minutes=slot_duration_minutes,
            timezone_str=timezone_str,
        )

        available = sum(1 for s in slots if not s['is_booked'])
        booked = sum(1 for s in slots if s['is_booked'])
        logger.info(f"Generated {len(slots)} total slots ({available} available, {booked} booked)")
        return slots

    async def _fetch_with_retry(self, date_start: date, date_end: date, calendar_id: str = None) -> list[dict]:
        """Fetch calendar events with exponential backoff retry logic.

        Args:
            date_start: Start date
            date_end: End date
            calendar_id: Optional specific calendar ID

        Returns:
            List of calendar events

        Raises:
            GoogleCalendarAPIError: If all retries fail and it's not a transient error
        """
        last_error = None

        for attempt in range(self.MAX_RETRIES):
            try:
                return await self.get_calendar_events(date_start, date_end, calendar_id=calendar_id)
            except GoogleCalendarTimeoutError as e:
                last_error = e
                if attempt < self.MAX_RETRIES - 1:
                    delay = self.RETRY_DELAYS[attempt]
                    logger.warning(f"Timeout, retrying in {delay}s (attempt {attempt + 1}/{self.MAX_RETRIES})")
                    await asyncio.sleep(delay)
            except GoogleCalendarAuthError:
                # Don't retry auth errors
                raise
            except GoogleCalendarAPIError as e:
                # Check if it's a transient error (rate limit)
                if "Rate limit" in str(e):
                    last_error = e
                    if attempt < self.MAX_RETRIES - 1:
                        delay = self.RETRY_DELAYS[attempt]
                        logger.warning(f"Rate limited, retrying in {delay}s (attempt {attempt + 1}/{self.MAX_RETRIES})")
                        await asyncio.sleep(delay)
                    else:
                        raise
                else:
                    raise

        # All retries exhausted
        if last_error:
            raise last_error
        raise GoogleCalendarAPIError("Failed to fetch calendar events after retries")

    async def create_event(
        self,
        summary: str,
        date_start: date,
        time_start: time,
        time_end: time,
        description: str = None,
        timezone: str = "America/Argentina/Buenos_Aires",
        calendar_id: str = None,
    ) -> dict:
        """Create an event in Google Calendar.

        Args:
            summary: Event title/summary
            date_start: Event date
            time_start: Event start time
            time_end: Event end time
            description: Optional event description
            timezone: Timezone for the event
            calendar_id: Optional specific calendar ID (overrides default)

        Returns:
            Created event dict with id, summary, start, end

        Raises:
            GoogleCalendarAPIError: If event creation fails
        """
        service = self._get_service()

        # Use provided calendar_id or default
        effective_calendar_id = calendar_id if calendar_id else self.calendar_id

        # Build datetime objects
        dt_start = datetime.combine(date_start, time_start)
        dt_end = datetime.combine(date_start, time_end)

        logger.info(
            f"🔧 Building event: summary='{summary}', "
            f"start={dt_start.isoformat()}, end={dt_end.isoformat()}, "
            f"timezone={timezone}, calendar_id={effective_calendar_id}"
        )

        event = {
            "summary": summary,
            "start": {
                "dateTime": dt_start.isoformat(),
                "timeZone": timezone,
            },
            "end": {
                "dateTime": dt_end.isoformat(),
                "timeZone": timezone,
            },
        }

        if description:
            event["description"] = description
            logger.info(f"📝 Event description: {description[:100]}")

        try:
            logger.info(f"🚀 Sending event creation request to Google Calendar API...")
            loop = asyncio.get_event_loop()
            request = service.events().insert(calendarId=effective_calendar_id, body=event)

            result = await asyncio.wait_for(
                loop.run_in_executor(None, request.execute), timeout=10.0
            )

            event_id = result.get('id')
            event_status = result.get('status')
            html_link = result.get('htmlLink', 'N/A')
            logger.info(
                f"✅ Event created successfully! "
                f"ID: {event_id}, Status: {event_status}, "
                f"Summary: {summary}, Link: {html_link}"
            )
            return result

        except asyncio.TimeoutError:
            logger.error(f"⏱️ Google Calendar API call timed out after 10s")
            raise GoogleCalendarTimeoutError("Event creation timed out")
        except HttpError as e:
            if e.resp.status == 401:
                logger.error(f"🔒 Google Calendar authentication failed (401): {e}")
                raise GoogleCalendarAuthError(f"Invalid credentials: {e}")
            elif e.resp.status == 403:
                logger.error(f"🚫 Google Calendar permission denied (403): {e}")
                raise GoogleCalendarAPIError(f"Permission denied: {e}")
            elif e.resp.status == 404:
                logger.error(f"❓ Google Calendar not found (404): {e}")
                raise GoogleCalendarAPIError(f"Calendar not found: {e}")
            else:
                logger.error(f"⚠️ Google Calendar API error ({e.resp.status}): {e}")
                raise GoogleCalendarAPIError(f"Event creation failed: {e}")
        except Exception as e:
            logger.error(f"💥 Unexpected error creating event: {type(e).__name__}: {e}", exc_info=True)
            raise GoogleCalendarAPIError(f"Unexpected error: {e}")
