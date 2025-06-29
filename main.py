import base64

from openai import OpenAI
import os
from elevenlabs.client import ElevenLabs
from flask import Flask, request, jsonify, session, send_from_directory, render_template, flash, url_for, redirect, send_file
from flask_cors import CORS
# Removed: from flask_socketio import SocketIO, emit # No longer needed for REST
from pathlib import Path
from dotenv import load_dotenv
from Game import Game # Your Game class
from io import BytesIO
import threading
from elevenlabs import play

load_dotenv(dotenv_path=Path("keys.env"), override=True)

# Initialize OpenAI clients
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

clientX = OpenAI(
    base_url="https://api.x.ai/v1",
    api_key=os.getenv("GROK_API_KEY") # Ensure this is correct
)

# Initialize ElevenLabs client
elevenlabs = ElevenLabs(
    api_key=os.getenv("ELEVEN_LABS_API_KEY"),
)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'

# --- THE KEY LINE FOR CORS: Allow all origins, methods, and headers for the entire app ---
CORS(app) # This is the most permissive setting for `flask-cors`
# If you explicitly want to configure it for all routes with specific methods/headers:
# CORS(app, resources={r"/*": {"origins": "*", "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"], "allow_headers": ["Content-Type", "Authorization"]}})

# Removed: socketio = SocketIO(app, cors_allowed_origins="*")

game = None
totalViews = 0

lock = threading.Lock()

# --- Helper to initialize or get the game instance ---
# This ensures the game object is created only once on server start (or first request)
def get_game_instance():
    global game
    global lock
    # totalViews is now handled by the endpoint for polling.
    with lock:
        if game is None:
            # Pass None as the socket_placeholder since Game class no longer directly needs socketio
            game = Game()
            print("Game created (via REST init)")
    return game

# --- API Endpoints (Paths updated to match frontend) ---

# 1. GET /game/data
@app.route('/game/data', methods=['GET'])
def get_game_data():
    current_game = get_game_instance()
    # Check if game is still setting up (e.g., generating content)
    if current_game.creatingGame:
        return jsonify({"showLoadScreen": True, "question": "Loading next round..."})
    else:
        # Return current game state, including placeholder audio URLs
        return jsonify({
            "showLoadScreen": False,
            "question": current_game.question,
            "totalVotes": current_game.totalVotes, # Include current votes for persuasion bar
        })

# 2. POST /game/vote
@app.route('/game/vote', methods=['POST'])
def handle_vote():
    data = request.get_json()
    side = data.get('side')
    user = data.get('user')
    if side is None:
        return jsonify({"error": "Missing 'side' in request"}), 400

    current_game = get_game_instance()
    current_game.logNewVote(side)
    print(f"User {user} voted {side}. Total votes: {current_game.totalVotes}")
    return jsonify({"message": "Vote received", "totalVotes": current_game.totalVotes})

# 3. POST /game/emoji
@app.route('/game/emoji', methods=['POST'])
def handle_emoji():
    data = request.get_json()
    emoji = data.get('emoji')
    user = data.get('user')
    if emoji is None:
        return jsonify({"error": "Missing 'emoji' in request"}), 400

    print(f"User {user} reacted with emoji: {emoji}")
    return jsonify({"message": "Emoji reaction received"})

# 4. GET /game/views
@app.route('/game/views', methods=['GET'])
def get_view_count():
    global totalViews
    # In a pure REST setup, `totalViews` increments with each GET /game/data call
    # or whenever a new client initiates interaction. For a simple demo, this
    # is a rough estimate.
    return jsonify({"totalViews": totalViews})

# 5. GET /game/persuasion
@app.route('/game/persuasion', methods=['GET'])
def get_persuasion_votes():
    current_game = get_game_instance()
    return jsonify({"totalVotes": current_game.totalVotes})

# --- Serve static files (e.g., audio) ---
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)


@app.route('/getAudio', methods=['POST'])
def get_audio():
    current_game = get_game_instance()
    print("bignum")
    out = b"".join(
        chunk for chunk in current_game.audio
        if isinstance(chunk, (bytes, bytearray)) and chunk
    )

    return send_file(
        BytesIO(out),
        mimetype="audio/mpeg",
        as_attachment=False,
        download_name="clip.mp3"
    )


@app.route('/getSpeaker', methods=['POST'])
def getSpeaker():
    game = get_game_instance()
    if game.speaking is not None:
        return jsonify({'success': True, 'speaker': game.speaking, 'startTime': game.audioStartTime})
    else:
        return jsonify({'success': False})

# --- Main execution ---
if __name__ == '__main__':
    # Run the Flask app directly (no SocketIO)
    app.run(host='127.0.0.1', port=5000, debug=False) # debug=True can be useful during development