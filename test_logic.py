import os
import asyncio
import datetime
from dotenv import load_dotenv
from main import AssistantFunctionContext

load_dotenv()

async def test():
    fnc = AssistantFunctionContext()
    
    print("--- 📚 Test Knowledge Lookup ---")
    res = await fnc.knowledge_lookup(query="pricing")
    print(f"Result (first 100 chars): {res[:100]}...")
    
    print("\n--- 📝 Test Sheets Credentials ---")
    if os.path.exists("service_account.json"):
        print("✅ service_account.json exists")
        spreadsheet_id = os.getenv("SPREADSHEET_ID")
        sheet_name = os.getenv("SHEET_NAME")
        print(f"Spreadsheet ID: {spreadsheet_id}")
        print(f"Sheet Name: {sheet_name}")
    else:
        print("❌ ERROR: service_account.json NOT FOUND in root!")

if __name__ == "__main__":
    asyncio.run(test())
