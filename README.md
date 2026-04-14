# Voice Agent - Local Run Guide

This project is a LiveKit + Gemini realtime voice agent for Arabic lead capture and Google Sheets logging.

## What Runs Locally

- `main.py`: the LiveKit worker that joins a room and runs the voice agent
- `server.py`: a small Flask app that serves the browser demo and creates LiveKit tokens
- `tools.py`: knowledge lookup, lead saving, and human transfer tools

## Prerequisites

- Python 3.11 to 3.13 recommended
- A LiveKit server or LiveKit Cloud project
- A Google AI Studio API key for Gemini realtime
- A Google service account JSON file with access to your target sheet

## Environment Setup

1. Create a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Copy the sample environment file:

```powershell
Copy-Item .env.example .env
```

4. Fill in `.env` with real values:

- `GOOGLE_API_KEY`
- `GEMINI_MODEL`
- `LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`
- `SPREADSHEET_ID`
- `SHEET_NAME`
- `GOOGLE_APPLICATION_CREDENTIALS`

5. Put your Google service account file in the project root or point `GOOGLE_APPLICATION_CREDENTIALS` to its full path.

## Run Locally

Open two terminals in this folder with the virtual environment activated.

Terminal 1:

```powershell
python main.py dev
```

Terminal 2:

```powershell
python server.py
```

Then open:

- `http://localhost:5000`

The page will request a token from the Flask server, connect to your LiveKit room, and the worker in `main.py` will join the same room as the agent.

## Quick Checks

- If the worker fails immediately, confirm your LiveKit and Google API keys in `.env`
- If you see a Gemini policy/model mismatch, set `GEMINI_MODEL=gemini-2.5-flash-native-audio-preview-12-2025`
- If Sheets writes fail, confirm the sheet is shared with the service account email
- If the browser connects but no voice is heard, make sure the worker is running and the room name matches

## Notes

- The worker code is written for `livekit-agents 1.5.x`
- `main.py` now uses `AgentSession`, which matches the installed LiveKit SDK
- `server.py` needs `flask`, which is included in `requirements.txt`
