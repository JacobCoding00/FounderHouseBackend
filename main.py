from openai import OpenAI
from elevenlabs.client import ElevenLabs
from elevenlabs import play
import json
from flask import Flask, request, jsonify, session, send_from_directory, render_template, flash, url_for, redirect
from flask_cors import CORS
from pathlib import Path
import random
from mutagen.mp3 import MP3
import time
from io import BytesIO
from dotenv import load_dotenv
from flask_socketio import SocketIO, emit, join_room, leave_room

load_dotenv()

app = Flask(__name__)

app.config['SECRET_KEY'] = 'supersecretkey'
CORS(app)


socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/config/view/generateConversation', methods=['GET'])
def generateConversation():
    systemPrompt = "You will be given a variation on the trolley problem, create a debate that focus on entertainment value and being hilarious between two famous people, Have a speech from each then a rebuttal from each. make sure they insult each other \n\n Formatting instructions: \n json format, with a person1: followed by first text\n person2 followed by second text\n rebuttal1 followed by first rebutttal\n rebuttal2 followed by second rebuttal \n the text should only include what each person will say, as it will be used for text to speech"

    with Path("/scenarios.json").open("r", encoding="utf-8") as fp:
        scenarios = json.load(fp)  # data is now a dict / list matching the JSON

    group = random.choice(scenarios.get("1"))
    singleton = random.choice(scenarios.get("2"))
    person1 = "Neil Degrasse Tyson"
    person2 = "Jeremy Clarkson"

    prompt = f"either dont switch the lever and let {group} die, or switch the lever and let {singleton} die.\nperson1 is {person1}, person2 is {person2}"



    messages = [{"role": "system", "content": systemPrompt},
                {"role": "system",
                 "content": prompt}
                ]

    completion = clientX.chat.completions.create(
        model="grok-3-mini",
        messages=messages,
        temperature=1,
    )

    output = completion.choices[0].message.content
    jsonOutput = json.loads(output)

    audio1 = elevenlabs.text_to_speech.convert(
        text=jsonOutput.get("person1"),
        voice_id="bhHp3QpEswU7MPJwQhel",
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )

    audio2 = elevenlabs.text_to_speech.convert(
        text=jsonOutput.get("person2"),
        voice_id="PtaCevw2ZQ5izoAWXzIy",
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )

    audio3 = elevenlabs.text_to_speech.convert(
        text=jsonOutput.get("rebuttal1"),
        voice_id="bhHp3QpEswU7MPJwQhel",
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )

    audio4 = elevenlabs.text_to_speech.convert(
        text=jsonOutput.get("rebuttal2"),
        voice_id="PtaCevw2ZQ5izoAWXzIy",
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )

    play(audio1)
    print("audio 1 playing")
    time.sleep(MP3(BytesIO(audio1)).info.length)
    play(audio2)
    time.sleep(MP3(BytesIO(audio2)).info.length)
    play(audio3)
    time.sleep(MP3(BytesIO(audio3)).info.length)
    play(audio4)
    time.sleep(MP3(BytesIO(audio4)).info.length)

if __name__ == '__main__':
    socketio.run(app, host='127.0.0.1', port=5000, debug=True, allow_unsafe_werkzeug=True)