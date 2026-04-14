import os
from dotenv import load_dotenv
from google import genai

load_dotenv()  # Load .env file

# Temporary hardcode to test - remove after
API_KEY = os.environ.get("GOOGLE_API_KEY") or "AIzaSyDyQO-C70pbzfmD4rMOn2OpP2-NDoE4CFM"

client = genai.Client(api_key=API_KEY)

print("Available realtime models:")
for model in client.models.list():
    if hasattr(model, 'supported_actions') and "bidiGenerateContent" in model.supported_actions:
        print(f"  ✅ {model.name}")