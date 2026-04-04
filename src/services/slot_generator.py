"""Slot generation logic for appointment booking feature."""
from datetime import date, time, datetime, timedelta
from typing import Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


class SlotGenerator:
    """Generate available appointment slots from Google Calendar events."""

    @staticmethod
    def generate_available_slots(
        calendar_events: list[dict],
        date_range: tuple[date, date],
        business_hours: tuple[time, time] = (time(8, 0), time(13, 0)),
        slot_duration_minutes: int = 60,
    ) -> list[dict]:
        """Generate available appointment slots.

        Filters calendar events and creates free time slots within business hours,
        Monday through Friday, excluding already-booked times.

        Args:
            calendar_events: List of calendar event dicts (from Google Calendar API)
                           Each event should have 'start' and 'end' with 'dateTime' or 'date' keys
            date_range: (start_date, end_date) tuple for slot generation period
            business_hours: (start_time, end_time) tuple for clinic hours (default 08:00-13:00)
            slot_duration_minutes: Duration of each slot in minutes (default 60)

        Returns:
            List of available slots, each a dict with:
            - date: date object
            - start_time: time object
            - end_time: time object
        """
        date_start, date_end = date_range
        business_start, business_end = business_hours

        # Parse booked times from calendar events
        booked_times = SlotGenerator._parse_booked_times(calendar_events)

        available_slots = []
        current_date = date_start

        # Iterate through date range
        while current_date <= date_end:
            # Only generate slots for Monday-Friday (0=Monday, 6=Sunday)
            if current_date.weekday() < 5:  # 0-4 = Mon-Fri
                # Generate hourly slots for this date within business hours
                slot_start = business_start
                while slot_start < business_end:
                    slot_end_time = SlotGenerator._add_minutes(slot_start, slot_duration_minutes)

                    # Check if slot end exceeds business hours
                    if slot_end_time > business_end:
                        break

                    # Check if this slot is booked
                    slot_datetime_start = datetime.combine(current_date, slot_start)
                    slot_datetime_end = datetime.combine(current_date, slot_end_time)

                    if not SlotGenerator._is_slot_booked(
                        slot_datetime_start, slot_datetime_end, booked_times
                    ):
                        # Slot is available
                        available_slots.append(
                            {
                                "date": current_date,
                                "start_time": slot_start,
                                "end_time": slot_end_time,
                            }
                        )

                    slot_start = slot_end_time

            current_date += timedelta(days=1)

        logger.info(f"Generated {len(available_slots)} available slots for {date_start} to {date_end}")
        return available_slots

    @staticmethod
    def _parse_booked_times(calendar_events: list[dict]) -> list[tuple[datetime, datetime]]:
        """Extract booked time ranges from Google Calendar events.

        Args:
            calendar_events: List of calendar event dicts from Google Calendar API

        Returns:
            List of (start_datetime, end_datetime) tuples
        """
        booked_times = []

        for event in calendar_events:
            try:
                # Handle both dateTime (with timezone) and date (all-day) formats
                start_info = event.get("start", {})
                end_info = event.get("end", {})

                if "dateTime" in start_info:
                    # Timed event - parse datetime
                    start_str = start_info["dateTime"]
                    end_str = end_info["dateTime"]

                    # Handle timezone-aware datetime strings
                    if "+" in start_str or start_str.endswith("Z"):
                        # Parse ISO 8601 format with timezone
                        start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                        end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                        # Convert to naive datetime (UTC)
                        start_dt = start_dt.replace(tzinfo=None)
                        end_dt = end_dt.replace(tzinfo=None)
                    else:
                        start_dt = datetime.fromisoformat(start_str)
                        end_dt = datetime.fromisoformat(end_str)

                    booked_times.append((start_dt, end_dt))
                elif "date" in start_info:
                    # All-day event - skip (full day is blocked)
                    start_date = datetime.strptime(start_info["date"], "%Y-%m-%d")
                    booked_times.append((start_date, start_date + timedelta(days=1)))
            except (KeyError, ValueError) as e:
                logger.warning(f"Failed to parse calendar event: {e}, event={event}")
                continue

        logger.debug(f"Parsed {len(booked_times)} booked time ranges from calendar")
        return booked_times

    @staticmethod
    def _is_slot_booked(
        slot_start: datetime, slot_end: datetime, booked_times: list[tuple[datetime, datetime]]
    ) -> bool:
        """Check if a time slot overlaps with any booked times.

        Args:
            slot_start: Slot start datetime
            slot_end: Slot end datetime
            booked_times: List of (start, end) booked time ranges

        Returns:
            True if slot overlaps with any booked time
        """
        for booked_start, booked_end in booked_times:
            # Check overlap: slot_start < booked_end AND slot_end > booked_start
            if slot_start < booked_end and slot_end > booked_start:
                return True
        return False

    @staticmethod
    def _add_minutes(t: time, minutes: int) -> time:
        """Add minutes to a time object.

        Args:
            t: Time object
            minutes: Minutes to add

        Returns:
            New time object
        """
        dt = datetime.combine(date.today(), t)
        new_dt = dt + timedelta(minutes=minutes)
        return new_dt.time()
