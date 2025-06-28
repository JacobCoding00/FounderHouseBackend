from openai import OpenAI
import os
from elevenlabs.client import ElevenLabs
from flask import Flask, request, jsonify, session, send_from_directory, render_template, flash, url_for, redirect
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from pathlib import Path
from dotenv import load_dotenv
from Game import Game

load_dotenv(dotenv_path=Path("keys.env"), override=True)

client = OpenAI(
    api_key= os.getenv("OPENAI_API_KEY")
)

clientX = OpenAI(
    base_url="https://api.x.ai/v1",
    api_key=
    os.getenv("GROK_API_KEY")
)

elevenlabs = ElevenLabs(
        api_key=os.getenv("ELEVEN_LABS_API_KEY"),
)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

game = None

@socketio.on('connect')
def handleConnection():
    global totalViews
    if totalViews == 0:
        global game
        game = Game(socketio)


    totalViews += 1
    socketio.emit("concurrentViews",  {"totalViews": totalViews})
    print("Yep increase them views brev")

@socketio.on("play_clip")
def handle_play_clip():
    # 1) broadcast the data (binary=True keeps it raw, no base64)
    socketio.emit("audio_bytes_on_connection", game.audio)

    # 2) broadcast a start time = now + PLAY_AHEAD seconds (epoch)
    socketio.emit("start_at", game.audioStartTime)

@socketio.on('vote')
def handleVote(data):
    side = data.get('side')
    user = data.get('user')
    game.logNewVote(side)
    print(game.totalVotes)
    socketio.emit("persuasionBarVotes", {"totalVotes": game.totalVotes})


if __name__ == '__main__':
    socketio.run(app, host='127.0.0.1', port=5000, debug=True, allow_unsafe_werkzeug=True)
