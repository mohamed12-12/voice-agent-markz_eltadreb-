# Gemini LiveKit Voice Agent

A lightweight, high-performance voice agent powered by Google's Gemini Realtime API and LiveKit. This agent is designed for natural, low-latency Arabic voice interactions.

## Features
- **Native Audio**: Uses `gemini-2.5-flash-native-audio-preview` for end-to-end voice processing.
- **Multilingual Support**: Optimized for Arabic conversations.
- **Low Latency**: Built on LiveKit Agents framework for seamless WebRTC communication.
- **Pure Voice**: No database or complex logging overhead—just a focused voice interaction layer.

## Prerequisites
- Python 3.10 or higher.
- A LiveKit Cloud project or a self-hosted LiveKit server.
- A Google Gemini API Key with access to the Realtime/Preview models.

## Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd Gemini-LiveKit
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:
   Copy `.env.example` to `.env` and fill in your credentials:
   ```bash
   cp .env.example .env
   ```
   Required variables:
   - `GOOGLE_API_KEY`: Your Gemini API key.
   - `LIVEKIT_URL`: Your LiveKit server URL (e.g., `wss://your-project.livekit.cloud`).
   - `LIVEKIT_API_KEY`: Your LiveKit API key.
   - `LIVEKIT_API_SECRET`: Your LiveKit API secret.

## Running the Agent

### Development Mode
To run the agent with local testing/sandbox:
```bash
python main.py dev
```

### Console Mode
To test the agent directly in your terminal (using your system's default microphone and speakers):
```bash
python main.py console
```

## Prompt Configuration
You can customize the agent's personality and instructions in `prompt.py`. The current configuration is optimized for Arabic voice interaction.

## License
MIT
