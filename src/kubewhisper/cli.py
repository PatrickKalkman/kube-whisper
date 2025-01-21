import os
import asyncio
import json
import websockets
import base64
import sounddevice as sd
import speech_recognition as sr

# Replace with your Realtime API WebSocket URL
REALTIME_API_URL = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview"
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    print("Error: OPENAI_API_KEY not found in environment variables.")
    exit(1)


class SimpleAssistant:
    def __init__(self):
        self.audio_chunks = []
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()

    async def run(self):
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "OpenAI-Beta": "realtime=v1",
        }

        async with websockets.connect(REALTIME_API_URL, additional_headers=headers) as ws:
            print("Connected to Realtime API.")
            await self.initialize_session(ws)
            while True:
                user_input = self.get_user_voice_input()
                if not user_input:
                    print("No input detected. Try again.")
                    continue

                print(f"You: {user_input}")
                await self.send_user_input(ws, user_input)
                await self.handle_responses(ws)

    async def initialize_session(self, websocket):
        session_init = {
            "type": "session.create",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": "You are a helpful assistant that responds with voice.",
                "output_audio_format": {
                    "type": "pcm_s16le",
                    "sample_rate": 16000,
                },
            },
        }
        await websocket.send(json.dumps(session_init))
        print("Session initialized.")

    def get_user_voice_input(self):
        print("Listening for your command...")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
            try:
                audio = self.recognizer.listen(source)
                return self.recognizer.recognize_google(audio)
            except sr.UnknownValueError:
                print("Sorry, I couldn't understand that.")
                return None

    async def send_user_input(self, websocket, user_input):
        event = {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": user_input}],
            },
        }
        await websocket.send(json.dumps(event))
        await websocket.send(json.dumps({"type": "response.create"}))
        print("Sent input to assistant.")

    async def handle_responses(self, websocket):
        self.audio_chunks = []
        async for message in websocket:
            event = json.loads(message)
            event_type = event.get("type")

            if event_type == "response.audio.delta":
                chunk = base64.b64decode(event["delta"])
                self.audio_chunks.append(chunk)
            elif event_type == "response.done":
                print("\nAssistant response complete.")
                self.play_audio_response()
                break

    def play_audio_response(self):
        if not self.audio_chunks:
            print("No audio response received.")
            return

        audio_data = b"".join(self.audio_chunks)
        print("Playing response...")
        sd.play(audio_data, samplerate=16000)
        sd.wait()


if __name__ == "__main__":
    print("Starting assistant. Press Ctrl+C to quit.")
    assistant = SimpleAssistant()
    try:
        asyncio.run(assistant.run())
    except KeyboardInterrupt:
        print("\nAssistant stopped.")
