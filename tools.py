import os
import re
from datetime import datetime, timezone
from livekit.agents import Agent, function_tool, RunContext
import httplib2
from google_auth_httplib2 import AuthorizedHttp
from googleapiclient.discovery import build
from google.oauth2 import service_account


DEFAULT_PROGRAM = "برنامج التمريض"


def _get_sheets_service():
    # Resolve absolute path to credentials file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    default_creds = os.path.join(current_dir, "service_account.json")
    creds_file = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", default_creds)
    
    # Validation
    if not os.path.exists(creds_file):
        raise FileNotFoundError(f"Credentials file not found at: {creds_file}")

    creds = service_account.Credentials.from_service_account_file(
        creds_file,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    http = AuthorizedHttp(
        creds,
        http=httplib2.Http(timeout=30, proxy_info=None),
    )
    return build("sheets", "v4", http=http, cache_discovery=False)


def _normalize_name(name: str) -> str:
    return " ".join(str(name).strip().split())


def _normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", str(phone))
    if digits.startswith("20") and len(digits) == 12:
        digits = "0" + digits[2:]
    if digits.startswith("2") and len(digits) == 11:
        digits = "0" + digits[1:]
    return digits


def _clean_phone_for_match(phone: str) -> str:
    return _normalize_phone(phone).lstrip("0")


def _has_triple_name(name: str) -> bool:
    parts = [part for part in _normalize_name(name).split(" ") if part]
    return len(parts) >= 3


def _is_valid_egypt_mobile(phone: str) -> bool:
    normalized = _normalize_phone(phone)
    return len(normalized) == 11 and normalized.startswith("01")

@function_tool
async def knowledge_lookup(ctx: RunContext, query: str) -> str:
    """Query the knowledge base for training programs, courses, and general information."""
    try:
        # Priority 1: Check Local Knowledge Base file first (fastest and most reliable for core info)
        base_path = os.path.dirname(__file__)
        kb_path = os.path.join(base_path, "KNOWLEDGE_BASE.md")
        local_info = ""
        if os.path.exists(kb_path):
            with open(kb_path, 'r', encoding='utf-8') as f:
                local_info = f.read()
        
        # Priority 2: Google Sheets (for dynamic updates if configured)
        sheet_info = ""
        try:
            service = _get_sheets_service()
            spreadsheet_id = os.environ.get("SPREADSHEET_ID")
            sheet_name = os.environ.get("SHEET_NAME", "الورقة1")
            if spreadsheet_id:
                result = service.spreadsheets().values().get(
                    spreadsheetId=spreadsheet_id,
                    range=f"{sheet_name}!A:C"
                ).execute()
                rows = result.get("values", [])
                if rows:
                    sheet_info = "\nDynamic Sheet Info:\n" + "\n".join(" | ".join(row) for row in rows)
        except:
            pass # Fallback to local only

        if not local_info and not sheet_info:
            return "Knowledge base is currently unavailable."

        return f"CRITICAL INFO (Ground Truth):\n{local_info}\n{sheet_info}"
    except Exception as e:
        return f"Error accessing knowledge base: {str(e)}"

@function_tool
async def save_lead_to_sheets(
    ctx: RunContext,
    name: str,
    phone: str,
    program: str = DEFAULT_PROGRAM,
    notes: str = ""
) -> str:
    """
    Save the caller lead to Google Sheets immediately after collecting valid data.
    Use this as soon as you have:
    - a clear full triple client name
    - a clear Egyptian mobile number of 11 digits starting with 01
    Program is optional and defaults to the nursing program.
    """
    try:
        spreadsheet_id = os.environ.get("SPREADSHEET_ID")
        if not spreadsheet_id:
            raise ValueError("Missing SPREADSHEET_ID environment variable.")

        normalized_name = _normalize_name(name)
        normalized_phone = _normalize_phone(phone)
        normalized_program = _normalize_name(program) or DEFAULT_PROGRAM
        normalized_notes = str(notes).strip()

        if not _has_triple_name(normalized_name):
            return "لا تحفظ البيانات قبل الحصول على الاسم الثلاثي كاملًا."

        if not _is_valid_egypt_mobile(normalized_phone):
            return "لا تحفظ البيانات قبل الحصول على رقم موبايل واضح من 11 رقم يبدأ بـ 01."

        print("\n" + "="*40)
        print(f"🚀 TOOL CALLED: save_lead_to_sheets")
        print(f"   Name: {normalized_name}")
        print(f"   Phone: {normalized_phone}")
        print(f"   Program: {normalized_program}")
        print("="*40 + "\n")

        service = _get_sheets_service()
        timestamp = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M") 
        
        # Smart sheet name detection
        sheet_name = os.environ.get("SHEET_NAME", "agentdata").strip()
        
        # Column layout: A name | B phone | C summary | D status
        col_c_summary = (
            f"Student: {normalized_name}\n"
            f"Interest: {normalized_program}\n"
            f"Notes: {normalized_notes}"
        )
        
        # --- SMART UPDATE LOGIC ---
        existing_row_index = None
        try:
            search_result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!B:B"
            ).execute()
            phone_list = search_result.get("values", [])
            
            match_target = _clean_phone_for_match(normalized_phone)
            for i, row in enumerate(phone_list):
                if row:
                    clean_sheet_phone = _clean_phone_for_match(str(row[0]))
                    if clean_sheet_phone == match_target:
                        existing_row_index = i + 1
                        break
        except Exception as e:
            print(f"DEBUG: Search error (might be empty sheet): {e}")
            pass 

        if existing_row_index:
            col_d_status = f"Captured: {timestamp}\nUPDATED_LEAD"
            update_body = {
                "values": [[normalized_name, normalized_phone, col_c_summary, col_d_status]]
            }
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!A{existing_row_index}:D{existing_row_index}",
                valueInputOption="USER_ENTERED",
                body=update_body
            ).execute()
            print(f"✅ SUCCESSFULLY UPDATED ROW {existing_row_index}")
            return f"Data for {normalized_name} was updated successfully in the sheet."
        else:
            col_d_status = f"Captured: {timestamp}\nNEW_LEAD"
            body = {
                "values": [[normalized_name, normalized_phone, col_c_summary, col_d_status]]
            }
            service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!A:D",
                valueInputOption="USER_ENTERED",
                body=body
            ).execute()
            print(f"✅ SUCCESSFULLY SAVED NEW LEAD: {normalized_name}")
            return f"Lead for {normalized_name} has been saved to the sheet successfully."

    except Exception as e:
        print(f"❌ CRITICAL ERROR IN TOOL: {e}")
        # Local fallback
        try:
            import csv
            cur_dir = os.path.dirname(os.path.abspath(__file__))
            with open(os.path.join(cur_dir, "leads_backup.csv"), "a", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
                writer.writerow([
                    _normalize_name(name),
                    _normalize_phone(phone),
                    f"PROG: {_normalize_name(program) or DEFAULT_PROGRAM} | {str(notes).strip()}",
                    f"TIME: {timestamp}",
                    "FALLBACK",
                ])
            return "I've saved your data securely."
        except:
            pass
        return f"Sheet save error: {str(e)}"


@function_tool
async def save_captured_lead(
    ctx: RunContext,
    name: str,
    phone: str,
    notes: str = ""
) -> str:
    """
    Simple lead-save tool for voice mode.
    Call this immediately after the customer gives a valid triple name and a valid 11-digit Egyptian mobile number.
    Program is automatically set to the nursing program.
    """
    return await save_lead_to_sheets(
        ctx=ctx,
        name=name,
        phone=phone,
        program=DEFAULT_PROGRAM,
        notes=notes,
    )

@function_tool
async def human_transfer(ctx: RunContext, reason: str) -> str:
    """Transfer the call to a human operator when requested or in case of complex issues."""
    print(f"TRANSFER REQUESTED: {reason}")
    # In a real LiveKit implementation, this might trigger a SIP transfer or a webhook.
    # For now, we return a confirmation message that the agent can say.
    return "Initiating transfer to the support team..."

class CarimAgent(Agent):
    def __init__(self, instructions: str):
        super().__init__(
            instructions=instructions,
            tools=[knowledge_lookup, save_lead_to_sheets, save_captured_lead, human_transfer],
            turn_handling={
                "interruption": {
                    "enabled": True,
                }
            },
        )
