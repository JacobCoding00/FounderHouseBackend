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

@app.route('/config/view/generateConversation', methods=['GET'])
def generateConversation():
    systemPrompt = "You will be given a variation on the trolley problem, create a debate that focus on entertainment value and being hilarious between two famous people, Have a speech from each then a rebuttal from each. make sure they insult each other \n\n Formatting instructions: \n json format, with a person1: followed by first text\n person2 followed by second text\n rebuttal1 followed by first rebutttal\n rebuttal2 followed by second rebuttal \n the text should only include what each person will say, as it will be used for text to speech"

    with Path("scenarios.json").open("r", encoding="utf-8") as fp:
        scenarios = json.load(fp)

    with Path("celebs.json").open("r", encoding="utf-8") as fp:
        people = json.load(fp)

    group = random.choice(scenarios.get("1"))
    singleton = random.choice(scenarios.get("2"))
    person1 = random.choice(people)
    person2 = random.choice(people)
    while True:
        if person2 == person1:
            person2 = random.choice(people)
            break

    prompt = f"either dont switch the lever and let {group} die, or switch the lever and let {singleton} die.\nperson1 is {person1.get('name')}, person2 is {person2.get('name')}"



    messages = [{"role": "system", "content": systemPrompt},
                {"role": "system",
                 "content": prompt}
                ]

    completion = clientX.chat.completions.create(
        model="grok-3-mini",
        messages=messages,
        temperature=1,
    )
    print("Text generation complete")

    output = completion.choices[0].message.content
    jsonOutput = json.loads(output)

    audio1 = elevenlabs.text_to_speech.convert(
        text=jsonOutput.get("person1"),
        voice_id=person1.get('voiceId'),
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )

    audio2 = elevenlabs.text_to_speech.convert(
        text=jsonOutput.get("person2"),
        voice_id=person2.get('voiceId'),
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",

    )

    audio3 = elevenlabs.text_to_speech.convert(
        text=jsonOutput.get("rebuttal1"),
        voice_id=person1.get('voiceId'),
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )

    audio4 = elevenlabs.text_to_speech.convert(
        text=jsonOutput.get("rebuttal2"),
        voice_id=person2.get('voiceId'),
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )

    final_bytes = concat_elevenlabs_mp3(audio1, audio2, audio3, audio4)

    play(final_bytes)

def to_bytes(obj):
    """Accept bytes, bytearray, file-like, or generator of chunks."""
    if isinstance(obj, (bytes, bytearray)):
        return obj
    if hasattr(obj, "read"):          # file-like
        return obj.read()
    if isinstance(obj, Iterable):     # generator/iterator of chunks
        return b"".join(obj)
    raise TypeError("Unsupported audio container")

def concat_elevenlabs_mp3(*clips):
    segments = [
        AudioSegment.from_file(BytesIO(to_bytes(c)), format="mp3")
        for c in clips
    ]
    combined = segments[0]
    for seg in segments[1:]:
        combined += seg               # concatenate
    buf = BytesIO()
    combined.export(buf, format="mp3", bitrate="128k")
    return buf.getvalue()

def mp3_duration(gen) -> float:
    """
    Duration (seconds) of an ElevenLabs clip returned with stream=True.
    Works even if the generator interleaves empty / non-byte chunks.
    """
    raw = b"".join(ch for ch in gen if isinstance(ch, (bytes, bytearray)) and ch)
    segment = AudioSegment.from_file(BytesIO(raw), format="mp3")   # decode once
    return len(segment) / 1000.0   # Pydub len() → milliseconds


#if __name__ == '__main__':
#    socketio.run(app, host='127.0.0.1', port=5000, debug=True, allow_unsafe_werkzeug=True)


while True:
    systemPrompt = "You will be given a variation on the trolley problem, create a debate that focus on entertainment value and being hilarious between two famous people, Have a speech from each then a rebuttal from each. make sure they insult each other \n\n Formatting instructions: \n json format, with a person1: followed by first text\n person2 followed by second text\n rebuttal1 followed by first rebutttal\n rebuttal2 followed by second rebuttal \n the text should only include what each person will say, as it will be used for text to speech"

    with Path("scenarios.json").open("r", encoding="utf-8") as fp:
        scenarios = json.load(fp)

    with Path("celebs.json").open("r", encoding="utf-8") as fp:
        people = json.load(fp)

    group = random.choice(scenarios.get("1"))
    singleton = random.choice(scenarios.get("2"))
    peopleSample = random.sample(people, 2)
    person1 = peopleSample[0]
    person2 = peopleSample[1]

    prompt = f"either dont switch the lever and let {group} die, or switch the lever and let {singleton} die.\nperson1 is {person1.get('name')}, person2 is {person2.get('name')}"

    messages = [{"role": "system", "content": systemPrompt},
                {"role": "system",
                 "content": prompt}
                ]

    completion = clientX.chat.completions.create(
        model="grok-3-mini",
        messages=messages,
        temperature=1,
    )
    print("Text generation complete")

    output = completion.choices[0].message.content
    jsonOutput = json.loads(output)

    audio1 = elevenlabs.text_to_speech.convert(
        text=jsonOutput.get("person1"),
        voice_id=person1.get('voiceId'),
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )

    audio2 = elevenlabs.text_to_speech.convert(
        text=jsonOutput.get("person2"),
        voice_id=person2.get('voiceId'),
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )
    print("bingbong")

    audio3 = elevenlabs.text_to_speech.convert(
        text=jsonOutput.get("rebuttal1"),
        voice_id=person1.get('voiceId'),
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )

    audio4 = elevenlabs.text_to_speech.convert(
        text=jsonOutput.get("rebuttal2"),
        voice_id=person2.get('voiceId'),
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )

    print(f"{person1.get('name')} now speaking")
    play(audio1)
    print(f"{person2.get('name')} now speaking")
    play(audio2)
    print(f"{person1.get('name')} now speaking")
    play(audio3)
    print(f"{person2.get('name')} now speaking")
    play(audio4)
