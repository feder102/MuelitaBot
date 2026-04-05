#!/usr/bin/env python3
"""List all calendars accessible to the service account."""
import base64
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Read credentials from .env
with open('.env', 'r') as f:
    env_content = f.read()

lines = env_content.split('\n')
for line in lines:
    if line.startswith('GOOGLE_CALENDAR_CREDENTIALS_B64='):
        b64_data = line.split('=', 1)[1].strip()
        break

# Decode credentials
creds_json = base64.b64decode(b64_data).decode()
creds_dict = json.loads(creds_json)

# Create credentials
SCOPES = ["https://www.googleapis.com/auth/calendar"]
credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)

# Build service
service = build("calendar", "v3", credentials=credentials)

print(f"Service Account: {creds_dict['client_email']}")
print("=" * 60)

try:
    print("Listing all calendars accessible to the service account...")
    calendar_list = service.calendarList().list().execute()
    
    calendars = calendar_list.get('items', [])
    
    print(f"\n✅ Found {len(calendars)} calendars:")
    print("=" * 60)
    
    for i, cal in enumerate(calendars, 1):
        print(f"\n{i}. {cal.get('summary', 'No name')}")
        print(f"   ID: {cal.get('id')}")
        print(f"   Access Role: {cal.get('accessRole', 'unknown')}")
        print(f"   Primary: {cal.get('primary', False)}")
        print(f"   Timezone: {cal.get('timeZone', 'unknown')}")
        
        # Check if it's the calendar we're looking for
        target_id = "ae78cb2baac3e3318905a077b189140ef6226295e16f337fadb249caa483ea80@group.calendar.google.com"
        if cal.get('id') == target_id:
            print(f"   ⭐ THIS IS THE TARGET CALENDAR!")
        
except Exception as e:
    print(f"❌ Error listing calendars: {e}")

print("\n" + "=" * 60)
print("RECOMMENDATION: Use one of the calendar IDs above in your .env file")
print("Look for calendars where 'accessRole' is 'owner' or 'writer'")