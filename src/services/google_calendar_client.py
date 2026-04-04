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

    SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
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
        self, date_start: date, date_end: date
    ) -> list[dict]:
        """Fetch raw events from Google Calendar API.

        Args:
            date_start: Start date for event search
            date_end: End date for event search

        Returns:
            List of calendar event dicts with start, end, summary

        Raises:
            GoogleCalendarAPIError: If API call fails
            GoogleCalendarTimeoutError: If API call times out
        """
        service = self._get_service()

        # Build datetime boundaries (all day boundaries)
        time_min = datetime.combine(date_start, time.min).isoformat() + "Z"
        time_max = datetime.combine(date_end + timedelta(days=1), time.min).isoformat() + "Z"

        try:
            # Run API call in executor to avoid blocking
            loop = asyncio.get_event_loop()
            request = service.events().list(
                calendarId=self.calendar_id,
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
    ) -> list[dict]:
        """Get available appointment slots from Google Calendar.

        Filters calendar events and generates free slots within business hours.

        Args:
            date_start: Start date for slot generation
            date_end: End date for slot generation
            business_hours: (start_time, end_time) tuple for clinic hours
            slot_duration_minutes: Duration of each slot (default 60 min)

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
        )

        logger.info(f"Generated {len(slots)} available slots")
        return slots

    async def _fetch_with_retry(self, date_start: date, date_end: date) -> list[dict]:
        """Fetch calendar events with exponential backoff retry logic.

        Args:
            date_start: Start date
            date_end: End date

        Returns:
            List of calendar events

        Raises:
            GoogleCalendarAPIError: If all retries fail and it's not a transient error
        """
        last_error = None

        for attempt in range(self.MAX_RETRIES):
            try:
                return await self.get_calendar_events(date_start, date_end)
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
