
import random
from Agent import Agent
from pathlib import Path
import json
from elevenlabs.client import ElevenLabs
from elevenlabs import play
from openai import OpenAI
import os
from dotenv import load_dotenv
import time

load_dotenv(dotenv_path=Path("keys.env"), override=True)

clientX = OpenAI(
    base_url="https://api.x.ai/v1",
    api_key=
    os.getenv("GROK_API_KEY")
)

elevenlabs = ElevenLabs(
        api_key=os.getenv("ELEVEN_LABS_API_KEY"),
)

class Game: 
    def __init__(self) -> None:
        self.timeLeft = None
        self.left = None
        self.right = None
        self.question = None
        self.generateCelebs()
        #A left vote will decrease by -1 and increase by 1
        self.totalVotes = 0
        self.audio = None
        self.audioStartTime = None
        self.speaking = None
        
        #Creating game waits for the AI to generate ausio and text
        self.creatingGame = True
        self.generateQuestion()
        self.generateAudioContent()
        
    def generateCelebs(self) -> None:
            """
            Selects two unique celebrities from 'celebs.json' and
            initializes self.left and self.right Agent objects.
            """
            with Path("celebs.json").open("r", encoding="utf-8") as fp:
                all_celebs = json.load(fp)

            # Ensure there are at least two celebrities to pick from
            if len(all_celebs) < 2:
                raise ValueError("Not enough celebrities in 'celebs.json' to select two unique ones.")

            # Select two unique celebrities randomly
            # random.sample ensures unique selection
            chosen_celebs = random.sample(all_celebs, 2)

            # Assign to left and right agents
            # The 'name' and 'voiceId' keys match your JSON structure
            self.left = Agent(name=chosen_celebs[0]["name"], voiceId=chosen_celebs[0]["voiceId"])
            self.right = Agent(name=chosen_celebs[1]["name"], voiceId=chosen_celebs[1]["voiceId"]) 
            print(self.left.name)
    def generateQuestion(self) -> None:
        with Path("scenarios.json").open("r", encoding="utf-8") as fp:
            scenarios = json.load(fp)
            

        group = random.choice(scenarios.get("1"))
        singleton = random.choice(scenarios.get("2"))


        self.question = f"either dont switch the lever and let {group} die, or switch the lever and let {singleton} die."
        
            

    def generateAudioContent(self) -> None:
        systemPrompt = "You will be given a variation on the trolley problem, create a debate that focus on entertainment value and being hilarious between two famous people, Have a speech from each then a rebuttal from each. make sure they insult each other \n\n Formatting instructions: \n json format, with a person1: followed by first text\n person2 followed by second text\n rebuttal1 followed by first rebutttal\n rebuttal2 followed by second rebuttal \n the text should only include what each person will say, as it will be used for text to speech"
        messages = [{"role": "system", "content": systemPrompt},
                    {"role": "system",
                     "content": f"{self.question} \nperson1 is {self.left.name}, person2 is {self.right.name}"}
                    ]
        print(messages)
        
    
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
            voice_id=self.left.voiceId,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
        )

        #audio2 = elevenlabs.text_to_speech.convert(
        #    text=jsonOutput.get("person2"),
        #    voice_id=self.right.voiceId,
        #    model_id="eleven_multilingual_v2",
        #    output_format="mp3_44100_128",
        #)
        print("bingbong")

        #audio3 = elevenlabs.text_to_speech.convert(
        #    text=jsonOutput.get("rebuttal1"),
        #    voice_id=self.left.voiceId,
        #    model_id="eleven_multilingual_v2",
        #    output_format="mp3_44100_128",
        #)

        #audio4 = elevenlabs.text_to_speech.convert(
        #    text=jsonOutput.get("rebuttal2"),
        #    voice_id=self.right.voiceId,
        #    model_id="eleven_multilingual_v2",
        #    output_format="mp3_44100_128",
        #)

        audios = [audio1]#, audio2#, audio3, audio4]
        self.creatingGame = False
        person = 1

        for audio in audios:
            personFull = f"person{person}"
            print(f"{personFull} now speaking")
            if person == 1:
                self.speaking = self.left.name
                person = 2
            else:
                self.speaking = self.right.name
                person = 1

            self.audio = audio
            self.audioStartTime = time.time()
      

    def logNewVote(self, vote) -> None:
        self.totalVotes += vote

        