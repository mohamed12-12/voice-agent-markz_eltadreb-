import os
from flask import Flask, render_template, jsonify, request
from livekit import api
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Load credentials from .env
LIVEKIT_API_KEY = os.getenv('LIVEKIT_API_KEY')
LIVEKIT_API_SECRET = os.getenv('LIVEKIT_API_SECRET')
LIVEKIT_URL = os.getenv('LIVEKIT_URL')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/getToken')
def get_token():
    room_name = request.args.get('roomName', 'demo-room')
    participant_name = request.args.get('participantName', 'Client-Guest')
    
    if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
        return jsonify({'error': 'LiveKit credentials not configured'}), 500

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
    app.run(host='0.0.0.0', port=5000, debug=True)
