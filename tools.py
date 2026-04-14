import os
from datetime import datetime, timezone
from livekit.agents import Agent, function_tool, RunContext
from googleapiclient.discovery import build
from google.oauth2 import service_account

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
    return build("sheets", "v4", credentials=creds)

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
    program: str,
    notes: str = ""
) -> str:
    """
    Save a potential student's contact details (lead capture) to the database.
    Required: name, phone, program. Optional: notes (details/summary).
    """
    try:
        # --- FLEXIBLE VALIDATION ---
        # 1. Check for Name (min 2 chars)
        if len(name.strip()) < 2:
            return "Please ask the client for their name before saving."
        
        # 2. Check for Phone (min 8 digits to be safe globally)
        import re
        clean_input_phone = re.sub(r'\D', '', str(phone)).lstrip('0')
        if len(clean_input_phone) < 8:
            return "The phone number seems incomplete. Please ask for the full number."

        print("\n" + "="*40)
        print(f"🚀 TOOL CALLED: save_lead_to_sheets")
        print(f"   Name: {name}")
        print(f"   Phone: {phone}")
        print("="*40 + "\n")

        service = _get_sheets_service()
        spreadsheet_id = os.environ.get("SPREADSHEET_ID")
        timestamp = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M") 
        
        # Smart sheet name detection
        sheet_name = os.environ.get("SHEET_NAME", "agentdata")
        
        # Construct summary for Column C
        col_c_summary = f"Student: {name}\nInterest: {program}\nNotes: {notes}"
        
        # --- SMART UPDATE LOGIC ---
        existing_row_index = None
        try:
            search_result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!B:B"
            ).execute()
            phone_list = search_result.get("values", [])
            
            match_target = clean_input_phone
            for i, row in enumerate(phone_list):
                if row:
                    clean_sheet_phone = re.sub(r'\D', '', str(row[0])).lstrip('0')
                    if clean_sheet_phone == match_target:
                        existing_row_index = i + 1
                        break
        except Exception as e:
            print(f"DEBUG: Search error (might be empty sheet): {e}")
            pass 

        if existing_row_index:
            col_d_status = f"Captured: {timestamp}\nUPDATED_LEAD"
            update_body = {"values": [[name, phone, col_c_summary, col_d_status]]}
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!A{existing_row_index}:D{existing_row_index}",
                valueInputOption="USER_ENTERED",
                body=update_body
            ).execute()
            print(f"✅ SUCCESSFULLY UPDATED ROW {existing_row_index}")
            return f"Data for {name} was updated successfully in the sheet."
        else:
            col_d_status = f"Captured: {timestamp}\nNEW_LEAD"
            body = {"values": [[name, phone, col_c_summary, col_d_status]]}
            service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!A:D",
                valueInputOption="USER_ENTERED",
                body=body
            ).execute()
            print(f"✅ SUCCESSFULLY SAVED NEW LEAD: {name}")
            return f"Lead for {name} has been saved to the sheet successfully."

    except Exception as e:
        print(f"❌ CRITICAL ERROR IN TOOL: {e}")
        # Local fallback
        try:
            import csv
            cur_dir = os.path.dirname(os.path.abspath(__file__))
            with open(os.path.join(cur_dir, "leads_backup.csv"), "a", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
                writer.writerow([name, phone, f"PROG: {program} | {notes}", f"TIME: {timestamp}", "FALLBACK"])
            return "I've saved your data securely."
        except:
            pass
        return f"Sheet save error: {str(e)}"

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
            tools=[knowledge_lookup, save_lead_to_sheets, human_transfer]
        )
