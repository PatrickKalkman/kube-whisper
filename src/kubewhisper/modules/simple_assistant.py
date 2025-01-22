import asyncio
import json
import time
import base64
import speech_recognition as sr
from websockets.exceptions import ConnectionClosedError
import websockets
from kubewhisper.modules.logging import log_ws_event, log_tool_call, log_error, log_info, log_warning
from kubewhisper.modules.logging import logger
from kubewhisper.utils.utils import log_runtime
from kubewhisper.modules.websocket_manager import WebSocketManager
from kubewhisper.modules.tools import function_map as base_function_map, tools as base_tools
from kubewhisper.modules.kubernetes_tools import function_map as k8s_function_map, tools as k8s_tools
from kubewhisper.modules.async_microphone import AsyncMicrophone
from kubewhisper.modules.audio import play_audio

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
        self.audio_chunks = []
        self.mic = AsyncMicrophone()
        self.exit_event = asyncio.Event()
        self.ws_manager = WebSocketManager(openai_api_key, realtime_api_url)

        self.assistant_reply = ""
        self.audio_chunks = []
        self.response_in_progress = False
        self.function_call = None
        self.function_call_args = ""
        self.response_start_time = None

    async def run(self):
        while True:
            try:
                await self.ws_manager.connect()

                session_config = {
                    "modalities": ["text", "audio"],
                    "instructions": SESSION_INSTRUCTIONS,
                    "voice": "alloy",
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
                await self.handle_event(event)
            except websockets.ConnectionClosed:
                log_warning("⚠️ WebSocket connection lost.")
                break

    async def send_user_input(self, user_input):
        await self.ws_manager.send_user_input(user_input)
        print("Sent input to assistant.")

    async def send_error_message_to_assistant(self, error_message):
        await self.ws_manager.send_error_message(error_message)

    async def handle_response_done(self):
        if self.response_start_time is not None:
            response_end_time = time.perf_counter()
            response_duration = response_end_time - self.response_start_time
            log_runtime("realtime_api_response", response_duration)
            self.response_start_time = None

        log_info("Assistant response complete.")
        if self.audio_chunks:
            audio_data = b"".join(self.audio_chunks)
            logger.info(f"Sending {len(audio_data)} bytes of audio data to play_audio()")
            await play_audio(audio_data)
            logger.info("Finished play_audio()")
        self.assistant_reply = ""
        self.audio_chunks = []
        logger.info("Calling stop_receiving()")
        self.mic.stop_receiving()

    async def handle_response_created(self):
        self.mic.start_receiving()
        self.response_in_progress = True

    async def handle_text_delta(self, delta):
        self.assistant_reply += delta
        print(f"Assistant: {delta}", end="", flush=True)

    async def handle_audio_delta(self, delta):
        self.audio_chunks.append(base64.b64decode(delta))

    async def handle_function_call_arguments_delta(self, delta):
        self.function_call_args += delta

    async def handle_speech_started(self):
        logger.info("Speech detected, listening...")

    async def handle_rate_limits_updated(self):
        self.response_in_progress = False
        self.mic.is_recording = True
        logger.info("Resumed recording after rate_limits.updated")

    async def handle_event(self, event):
        event_type = event.get("type")
        handlers = {
            "response.created": lambda: self.handle_response_created(),
            "response.output_item.added": lambda: self.handle_output_item_added(event),
            "response.function_call_arguments.delta": lambda: self.handle_function_call_arguments_delta(event.get("delta", "")),
            "response.function_call_arguments.done": lambda: self.handle_function_call(event),
            "response.text.delta": lambda: self.handle_text_delta(event.get("delta", "")),
            "response.audio.delta": lambda: self.handle_audio_delta(event["delta"]),
            "response.done": lambda: self.handle_response_done(),
            "error": lambda: self.handle_error(event),
            "input_audio_buffer.speech_started": lambda: self.handle_speech_started(),
            "input_audio_buffer.speech_stopped": lambda: self.handle_speech_stopped(),
            "rate_limits.updated": lambda: self.handle_rate_limits_updated()
        }

        handler = handlers.get(event_type)
        if handler:
            await handler()

    async def handle_output_item_added(self, event):
        item = event.get("item", {})
        if item.get("type") == "function_call":
            self.function_call = item
            self.function_call_args = ""

    async def handle_function_call(self, event):
        if self.function_call:
            function_name = self.function_call.get("name")
            call_id = self.function_call.get("call_id")
            logger.info(f"Function call: {function_name} with args: {self.function_call_args}")
            try:
                args = json.loads(self.function_call_args) if self.function_call_args else {}
            except json.JSONDecodeError:
                args = {}
            await self.execute_function_call(function_name, call_id, args)

    async def execute_function_call(self, function_name, call_id, args):
        if function_name in function_map:
            try:
                result = await function_map[function_name](**args)
                log_tool_call(function_name, args, result)
            except Exception as e:
                error_message = f"Error executing function '{function_name}': {str(e)}"
                log_error(error_message)
                result = {"error": error_message}
                await self.send_error_message_to_assistant(error_message)
        else:
            error_message = f"Function '{function_name}' not found. Add to function_map in tools.py."
            log_error(error_message)
            result = {"error": error_message}
            await self.send_error_message_to_assistant(error_message)

        await self.ws_manager.send_function_call_output(call_id, result)

        # Reset function call state
        self.function_call = None
        self.function_call_args = ""

    async def handle_error(self, event):
        error_message = event.get("error", {}).get("message", "")
        log_error(f"Error: {error_message}")
        if "buffer is empty" in error_message:
            logger.info("Received 'buffer is empty' error, no audio data sent.")
        elif "Conversation already has an active response" in error_message:
            logger.info("Received 'active response' error, adjusting response flow.")
            self.response_in_progress = True
        else:
            logger.error(f"Unhandled error: {error_message}")

    async def handle_speech_stopped(self):
        self.mic.stop_recording()
        logger.info("Speech ended, processing...")
        self.response_start_time = time.perf_counter()
        await self.ws_manager.send_message({"type": "input_audio_buffer.commit"})

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
