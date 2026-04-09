import os
import asyncio
import warnings
import datetime
import platform
from typing import Annotated
from dotenv import load_dotenv

# --- CRITICAL FIX: Windows WMI Timeout Monkeypatch ---
# This prevents the "TimeoutError: [WinError 258]" when aiohttp/platform tries to query WMI on Windows.
if platform.system() == "Windows":
    _original_uname = platform.uname
    def _mock_uname():
        # Return a mock uname_result to avoid triggering WMI
        from collections import namedtuple
        UnameResult = namedtuple("uname_result", "system node release version machine processor")
        # Use environment variables for the node name to avoid recursion with platform.node()
        node_name = os.environ.get("COMPUTERNAME", "Windows-Host")
        return UnameResult("Windows", node_name, "10", "10.0.0", "AMD64", "Intel64 Family 6 Model 158 Stepping 10, GenuineIntel")
    platform.uname = _mock_uname

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic._internal._fields")

from livekit import agents, rtc
from livekit.agents import JobContext, WorkerOptions, AgentSession, voice, llm
from livekit.plugins import google
from google.oauth2 import service_account
from googleapiclient.discovery import build

from prompt import PROMPT

load_dotenv()

class AssistantFunctionContext:
    @llm.function_tool(description="Search the knowledge base for training programs, prices, and details.")
    async def knowledge_lookup(self, query: str) -> str:
        """Searches the KNOWLEDGE_BASE.md file and returns the content."""
        print(f"🔍 Searching knowledge for: {query}")
        try:
            # We ignore the query and return the whole file as it is a small KB
            # This ensures the agent has full context.
            with open("KNOWLEDGE_BASE.md", "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Knowledge error: {str(e)}"

    @llm.function_tool(description="Save lead name, phone, and interest to Google Sheets.")
    async def save_lead_to_sheets(self, 
                                  name: str, 
                                  phone: str, 
                                  interest: str) -> str:
        """Appends one row with lead details to the configured Google Sheet."""
        print(f"📝 Saving lead: {name}, {phone}, {interest}")
        try:
            spreadsheet_id = os.getenv("SPREADSHEET_ID")
            if not spreadsheet_id:
                return "error: SPREADSHEET_ID not set in environment"
                
            scopes = ["https://www.googleapis.com/auth/spreadsheets"]
            creds = service_account.Credentials.from_service_account_file(
                "service_account.json", scopes=scopes
            )
            service = build("sheets", "v4", credentials=creds)
            sheet_name = os.getenv("SHEET_NAME", "Leads")
            
            timestamp = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
            summary = (
                f"Student: {name}\n"
                f"Interest: {interest}\n"
                f"Captured: {timestamp}\n"
                f"NEW_LEAD"
            )
            
            values = [[name, phone, summary, "NEW_LEAD"]]
            service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!A:D",
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body={"values": values}
            ).execute()
            return "saved"
        except Exception as e:
            print(f"❌ Sheets Error: {e}")
            return f"error: {str(e)}"

    @llm.function_tool(description="Transfer the call to a human manager or specific department.")
    async def human_transfer(self, reason: str) -> str:
        """Simulates a call transfer to a human agent."""
        print(f"📞 Transferring to human. Reason: {reason}")
        # In a real LiveKit setup, you might use SIP or a specific signal.
        # Here we just acknowledge the transfer.
        return "Transferring you to a human manager now. Please stay on the line."

async def entrypoint(ctx: JobContext):
    try:
        print("🔌 Connecting to room...")
        await ctx.connect()

        print("🤖 Initializing Gemini Realtime model...")
        # FIX: Updated to current 2026 production model: Gemini 3.1 Flash Live
        model = google.beta.realtime.RealtimeModel(
            model="gemini-2.5-flash-native-audio-preview-12-2025",
            voice="Puck",
            temperature=0.6,
        )

        fnc_ctx = AssistantFunctionContext()

        print("🧠 Creating agent...")
        agent = voice.Agent(
            instructions=PROMPT,
            llm=model,
            min_endpointing_delay=1.0,
            allow_interruptions=True
        )

        print("🎙️ Starting session...")
        session = AgentSession(
            llm=model,
            vad=None,
            turn_detection="realtime_llm",
            tools=llm.find_function_tools(fnc_ctx),
        )

        await session.start(agent, room=ctx.room)

        print("✅ Agent running...")

        while ctx.room.connection_state == rtc.ConnectionState.CONN_CONNECTED:
            await asyncio.sleep(1)

    except Exception as e:
        import traceback
        print("❌ ERROR:", e)
        traceback.print_exc()

    finally:
        print("🔌 Disconnected")


if __name__ == "__main__":
    print("🚀 Starting LiveKit Worker...")
    agents.cli.run_app(
        WorkerOptions(entrypoint_fnc=entrypoint)
    )
