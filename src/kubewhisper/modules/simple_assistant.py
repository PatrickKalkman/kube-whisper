import asyncio
import speech_recognition as sr
from websockets.exceptions import ConnectionClosedError
import websockets
from kubewhisper.modules.logging import log_ws_event, log_warning, logger
from kubewhisper.modules.websocket_manager import WebSocketManager
from kubewhisper.modules.tools import function_map as base_function_map, tools as base_tools
from kubewhisper.modules.kubernetes_tools import function_map as k8s_function_map, tools as k8s_tools
from kubewhisper.modules.async_microphone import AsyncMicrophone
from .event_handler import EventHandler

# Combine function maps and tools
function_map = {**base_function_map, **k8s_function_map}
tools = base_tools + k8s_tools

SESSION_INSTRUCTIONS = (
    "You are Kuby, a helpful assistant. Respond to Pat. "
    "Keep all of your responses short. Say things like: "
    "'Task complete', 'There was an error', 'I need more information'."
)
PREFIX_PADDING_MS = 300
SILENCE_THRESHOLD = 0.5
SILENCE_DURATION_MS = 700


class SimpleAssistant:
    def __init__(self, openai_api_key, realtime_api_url):
        self.prompts = []
        self.mic = AsyncMicrophone()
        self.exit_event = asyncio.Event()
        self.ws_manager = WebSocketManager(openai_api_key, realtime_api_url)
        self.event_handler = EventHandler(self.mic, self.ws_manager, function_map)
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()

    async def run(self):
        while True:
            try:
                await self.ws_manager.connect()

                session_config = {
                    "modalities": ["text", "audio"],
                    "instructions": SESSION_INSTRUCTIONS,
                    "voice": "sage",
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": SILENCE_THRESHOLD,
                        "prefix_padding_ms": PREFIX_PADDING_MS,
                        "silence_duration_ms": SILENCE_DURATION_MS,
                    },
                    "tools": tools,
                }

                await self.ws_manager.initialize_session(session_config)
                ws_task = asyncio.create_task(self.process_ws_messages())

                logger.info("Conversation started. Speak freely, and the assistant will respond.")
                if self.prompts:
                    await self.send_initial_prompts()
                else:
                    self.mic.start_recording()
                    logger.info("Recording started. Listening for speech...")

                await self.send_audio_loop()
                await ws_task
                break

            except ConnectionClosedError as e:
                if "keepalive ping timeout" in str(e):
                    logger.warning("WebSocket connection lost due to keepalive ping timeout. Reconnecting...")
                    await asyncio.sleep(1)
                    continue
                else:
                    logger.exception("WebSocket connection closed unexpectedly.")
                    break
            except Exception as e:
                logger.exception(f"An unexpected error occurred: {e}")
                break
            finally:
                self.mic.stop_recording()
                self.mic.close()
                await self.ws_manager.close()

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

    async def process_ws_messages(self):
        while True:
            try:
                event = await self.ws_manager.receive_message()
                log_ws_event("Incoming", event)
                await self.event_handler.handle_event(event)
            except websockets.ConnectionClosed:
                log_warning("⚠️ WebSocket connection lost.")
                break

    async def send_user_input(self, user_input):
        await self.ws_manager.send_user_input(user_input)
        print("Sent input to assistant.")

    async def send_initial_prompts(self):
        for prompt in self.prompts:
            await self.send_user_input(prompt)

    async def send_audio_loop(self):
        try:
            while not self.exit_event.is_set():
                await asyncio.sleep(0.1)  # Small delay to accumulate audio data
                if not self.mic.is_receiving:
                    audio_data = self.mic.get_audio_data()
                    if audio_data and len(audio_data) > 0:
                        await self.ws_manager.send_audio_data(audio_data)
                    else:
                        logger.debug("No audio data to send")
                else:
                    await asyncio.sleep(0.1)  # Wait while receiving assistant response
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received. Closing the connection.")
        finally:
            self.exit_event.set()
            self.mic.stop_recording()
            self.mic.close()
            await self.ws_manager.close()
