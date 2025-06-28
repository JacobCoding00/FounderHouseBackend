from openai import OpenAI
import os
from elevenlabs.client import ElevenLabs
from elevenlabs import play
import json
from flask import Flask, request, jsonify, session, send_from_directory, render_template, flash, url_for, redirect
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from pathlib import Path
import random
from mutagen.mp3 import MP3, HeaderNotFoundError
import time
from io import BytesIO
from dotenv import load_dotenv
from pydub import AudioSegment
from collections.abc import Iterable
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

game = Game(socket=socketio)

@socketio.on("play_clip")
def handle_play_clip():

    # 1) broadcast the data (binary=True keeps it raw, no base64)
    socketio.emit("audio_bytes_on_connection", game.audio, broadcast=True, binary=True)

    # 2) broadcast a start time = now + PLAY_AHEAD seconds (epoch)
    socketio.emit("start_at", game.audioStartTime, broadcast=True)

def mp3_duration(gen) -> float:
    """
    Duration (seconds) of an ElevenLabs clip returned with stream=True.
    Works even if the generator interleaves empty / non-byte chunks.
    """
    raw = b"".join(ch for ch in gen if isinstance(ch, (bytes, bytearray)) and ch)
    segment = AudioSegment.from_file(BytesIO(raw), format="mp3")   # decode once
    return len(segment) / 1000.0   # Pydub len() → milliseconds


if __name__ == '__main__':
    socketio.run(app, host='127.0.0.1', port=5000, debug=True, allow_unsafe_werkzeug=True)
