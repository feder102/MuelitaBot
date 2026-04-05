#!/usr/bin/env python3
"""Test script to verify Google Calendar access."""
import base64
import json
import asyncio
from datetime import date, time, datetime, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Read credentials from .env
with open('.env', 'r') as f:
    env_content = f.read()

lines = env_content.split('\n')
for line in lines:
    if line.startswith('GOOGLE_CALENDAR_CREDENTIALS_B64='):
        b64_data = line.split('=', 1)[1].strip()
        break

for line in lines:
    if line.startswith('GOOGLE_CALENDAR_ID='):
        calendar_id = line.split('=', 1)[1].strip()
        break

print(f"Testing access to calendar: {calendar_id}")

# Decode credentials
creds_json = base64.b64decode(b64_data).decode()
creds_dict = json.loads(creds_json)

# Create credentials
SCOPES = ["https://www.googleapis.com/auth/calendar"]
credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)

# Build service
service = build("calendar", "v3", credentials=credentials)

async def test_calendar_access():
    """Test if we can access the calendar."""
    try:
        print("\n=== TEST 1: Get calendar info ===")
        calendar = service.calendars().get(calendarId=calendar_id).execute()
        print(f"✅ Calendar found: {calendar.get('summary', 'No summary')}")
        print(f"   ID: {calendar.get('id')}")
        print(f"   Timezone: {calendar.get('timeZone')}")
        
    except HttpError as e:
        print(f"❌ Error getting calendar: {e}")
        if e.resp.status == 403:
            print("   → Permission denied. The service account needs to be added to the calendar.")
            print(f"   → Add this email as editor: {creds_dict['client_email']}")
        elif e.resp.status == 404:
            print("   → Calendar not found. Check the calendar ID.")
        return False
    
    try:
        print("\n=== TEST 2: List events (next 7 days) ===")
        time_min = datetime.utcnow().isoformat() + "Z"
        time_max = (datetime.utcnow() + timedelta(days=7)).isoformat() + "Z"
        
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            maxResults=5,
            singleEvents=True,
            orderBy="startTime"
        ).execute()
        
        events = events_result.get('items', [])
        print(f"✅ Found {len(events)} events in next 7 days")
        for event in events[:3]:
            start = event['start'].get('dateTime', event['start'].get('date'))
            print(f"   • {event.get('summary', 'No title')} - {start}")
        
    except HttpError as e:
        print(f"❌ Error listing events: {e}")
        return False
    
    try:
        print("\n=== TEST 3: Create a test event ===")
        test_event = {
            'summary': 'Test Event from Service Account',
            'description': 'This is a test event to verify write access.',
            'start': {
                'dateTime': (datetime.utcnow() + timedelta(hours=1)).isoformat() + 'Z',
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': (datetime.utcnow() + timedelta(hours=2)).isoformat() + 'Z',
                'timeZone': 'UTC',
            },
        }
        
        created_event = service.events().insert(
            calendarId=calendar_id,
            body=test_event
        ).execute()
        
        print(f"✅ Test event created successfully!")
        print(f"   Event ID: {created_event.get('id')}")
        print(f"   HTML Link: {created_event.get('htmlLink')}")
        
        # Clean up: delete the test event
        print("\n=== Cleaning up: Deleting test event ===")
        service.events().delete(
            calendarId=calendar_id,
            eventId=created_event.get('id')
        ).execute()
        print("✅ Test event deleted")
        
    except HttpError as e:
        print(f"❌ Error creating event: {e}")
        if e.resp.status == 403:
            print("   → Write permission denied. Service account needs 'Make changes to events' permission.")
        return False
    
    return True

if __name__ == "__main__":
    print(f"Service Account: {creds_dict['client_email']}")
    print(f"Calendar ID: {calendar_id}")
    print("=" * 60)
    
    success = asyncio.run(test_calendar_access())
    
    if success:
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print(f"The service account has proper access to calendar: {calendar_id}")
    else:
        print("\n" + "=" * 60)
        print("❌ TESTS FAILED")
        print("Check the error messages above and fix the permissions.")