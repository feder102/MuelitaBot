#!/usr/bin/env python3
"""Check what events exist in Google Calendar."""
import asyncio
from datetime import date, timedelta
from src.config import settings
from src.services.google_calendar_client import GoogleCalendarClient

async def main():
    print("\n" + "="*80)
    print("CHECKING GOOGLE CALENDAR EVENTS")
    print("="*80 + "\n")

    try:
        # Show config
        print(f"📋 Calendar ID: {settings.google_calendar_id}\n")

        # Initialize client
        creds = settings.google_calendar_credentials
        client = GoogleCalendarClient(
            credentials_dict=creds,
            calendar_id=settings.google_calendar_id
        )

        # Fetch events
        print("📅 Fetching events for tomorrow...")
        tomorrow = date.today() + timedelta(days=1)
        next_week = tomorrow + timedelta(days=7)

        events = await client.get_calendar_events(tomorrow, next_week)

        if not events:
            print(f"❌ No events found in calendar from {tomorrow} to {next_week}")
        else:
            print(f"✅ Found {len(events)} events:\n")
            for i, event in enumerate(events, 1):
                summary = event.get('summary', 'N/A')
                start = event.get('start', {}).get('dateTime', event.get('start', {}).get('date', 'N/A'))
                status = event.get('status', 'N/A')
                event_id = event.get('id', 'N/A')

                print(f"{i}. {summary}")
                print(f"   Start: {start}")
                print(f"   Status: {status}")
                print(f"   ID: {event_id}\n")

    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
