import os
import sys
from dotenv import load_dotenv

# Always load .env from the same folder as this script, regardless of CWD
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, ".env"))

# Override the credentials path to be absolute
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(SCRIPT_DIR, "service_account.json")

# ---- Direct test of the Google Sheets write logic ----
import re
from datetime import datetime, timezone
import httplib2
from google_auth_httplib2 import AuthorizedHttp
from googleapiclient.discovery import build
from google.oauth2 import service_account

def test_save_to_sheets():
    print("Testing Google Sheets connection...")
    print(f"SPREADSHEET_ID: {os.environ.get('SPREADSHEET_ID')}")
    print(f"SHEET_NAME: {os.environ.get('SHEET_NAME')}")
    print(f"CREDS_FILE: {os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', 'service_account.json')}")
    
    creds_file = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "service_account.json")
    if not os.path.exists(creds_file):
        print(f"ERROR: Credentials file '{creds_file}' not found!")
        return False

    try:
        creds = service_account.Credentials.from_service_account_file(
            creds_file,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        http = AuthorizedHttp(
            creds,
            http=httplib2.Http(timeout=30, proxy_info=None),
        )
        service = build("sheets", "v4", http=http, cache_discovery=False)
        
        spreadsheet_id = os.environ.get("SPREADSHEET_ID")
        sheet_name = os.environ.get("SHEET_NAME", "agentdata")
        timestamp = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
        
        name = "Test User كريم"
        phone = "01000000000"
        program = "التمريض"
        notes = "اختبار من الكود مباشرة"
        
        col_c = f"Student: {name}\nInterest: {program}\nNotes: {notes}"
        col_d = f"Captured: {timestamp}\nTEST_ENTRY"
        
        body = {"values": [[name, phone, col_c, col_d]]}
        result = service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A:D",
            valueInputOption="USER_ENTERED",
            body=body
        ).execute()
        
        print(f"\n✅ SUCCESS! Row saved at: {result.get('updates', {}).get('updatedRange')}")
        return True
        
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        return False

if __name__ == "__main__":
    test_save_to_sheets()
