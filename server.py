import asyncio
import os
from flask import Flask, render_template, jsonify, request
from livekit import api
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)

app = Flask(__name__)

# Load credentials from .env
LIVEKIT_API_KEY = os.getenv('LIVEKIT_API_KEY')
LIVEKIT_API_SECRET = os.getenv('LIVEKIT_API_SECRET')
LIVEKIT_URL = os.getenv('LIVEKIT_URL')
AGENT_NAME = os.getenv('AGENT_NAME', 'carim-agent')


def _get_livekit_api_url(url: str) -> str:
    if url.startswith("wss://"):
        return "https://" + url[len("wss://"):]
    if url.startswith("ws://"):
        return "http://" + url[len("ws://"):]
    return url


async def _ensure_room_exists(lkapi: api.LiveKitAPI, room_name: str) -> None:
    rooms = await lkapi.room.list_rooms(api.ListRoomsRequest(names=[room_name]))
    if rooms.rooms:
        print(f"Room ready: {room_name}")
        return

    await lkapi.room.create_room(
        api.CreateRoomRequest(
            name=room_name,
            empty_timeout=60 * 10,
            max_participants=10,
        )
    )
    print(f"Created room: {room_name}")


async def _ensure_agent_dispatch(room_name: str) -> None:
    async with api.LiveKitAPI(
        url=_get_livekit_api_url(LIVEKIT_URL),
        api_key=LIVEKIT_API_KEY,
        api_secret=LIVEKIT_API_SECRET,
    ) as lkapi:
        await _ensure_room_exists(lkapi, room_name)
        dispatches = await lkapi.agent_dispatch.list_dispatch(room_name)
        if any(d.agent_name == AGENT_NAME for d in dispatches):
            print(f"Dispatch ready for agent '{AGENT_NAME}' in room '{room_name}'")
            return

        await lkapi.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                room=room_name,
                agent_name=AGENT_NAME,
                metadata='{"source":"web-demo"}',
            )
        )
        print(f"Created dispatch for agent '{AGENT_NAME}' in room '{room_name}'")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/getToken')
def get_token():
    room_name = request.args.get('roomName', 'demo-room')
    participant_name = request.args.get('participantName', 'Client-Guest')
    
    if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
        return jsonify({'error': 'LiveKit credentials not configured'}), 500
    if not LIVEKIT_URL:
        return jsonify({'error': 'LiveKit URL not configured'}), 500

    try:
        asyncio.run(_ensure_agent_dispatch(room_name))
    except Exception as e:
        return jsonify({'error': f'Failed to dispatch agent: {str(e)}'}), 500

    token = api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET) \
        .with_identity(participant_name) \
        .with_name(participant_name) \
        .with_grants(api.VideoGrants(
            room_join=True,
            room=room_name,
        ))
    
    return jsonify({
        'token': token.to_jwt(),
        'url': LIVEKIT_URL
    })

if __name__ == '__main__':
    # Run on port 5000
    print(f"Starting Demo Server on http://localhost:5000")
    print(f"To share with client, run: ngrok http 5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
