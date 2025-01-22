import base64
import os
import asyncio
import json
import time
import websockets
from datetime import datetime
import speech_recognition as sr
from kubewhisper.modules.logging import log_tool_call, log_error, log_info, log_warning
from kubewhisper.modules.logging import logger, log_ws_event
from kubewhisper.modules.tools import function_map as base_function_map, tools as base_tools
from kubewhisper.modules.kubernetes_tools import function_map as k8s_function_map, tools as k8s_tools
from websockets.exceptions import ConnectionClosedError
from kubewhisper.modules.async_microphone import AsyncMicrophone
from kubewhisper.modules.audio import play_audio

# Combine function maps and tools
function_map = {**base_function_map, **k8s_function_map}
tools = base_tools + k8s_tools

SESSION_INSTRUCTIONS = (
    "You are Ada, a helpful assistant. Respond to Pat. "
    "Keep all of your responses ultra short. Say things like: "
    "'Task complete', 'There was an error', 'I need more information'."
)
PREFIX_PADDING_MS = 300
SILENCE_THRESHOLD = 0.5
SILENCE_DURATION_MS = 700
RUN_TIME_TABLE_LOG_JSON = "runtime_time_table.jsonl"
# Replace with your Realtime API WebSocket URL
REALTIME_API_URL = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview"
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    print("Error: OPENAI_API_KEY not found in environment variables.")
    exit(1)


def log_runtime(function_or_name: str, duration: float):
    jsonl_file = RUN_TIME_TABLE_LOG_JSON
    time_record = {
        "timestamp": datetime.now().isoformat(),
        "function": function_or_name,
        "duration": f"{duration:.4f}",
    }
    with open(jsonl_file, "a") as file:
        json.dump(time_record, file)
        file.write("\n")

    logger.info(f"⏰ {function_or_name}() took {duration:.4f} seconds")


def base64_encode_audio(audio_bytes):
    return base64.b64encode(audio_bytes).decode("utf-8")


class SimpleAssistant:
    def __init__(self):
        self.prompts = []
        self.audio_chunks = []
        self.mic = AsyncMicrophone()
        self.exit_event = asyncio.Event()

        # Initialize state variables
        self.assistant_reply = ""
        self.audio_chunks = []
        self.response_in_progress = False
        self.function_call = None
        self.function_call_args = ""
        self.response_start_time = None

    async def run(self):
        while True:
            try:
                headers = {
                    "Authorization": f"Bearer {API_KEY}",
                    "OpenAI-Beta": "realtime=v1",
                }

                async with websockets.connect(
                    REALTIME_API_URL,
                    additional_headers=headers,
                    close_timeout=120,
                    ping_interval=30,
                    ping_timeout=10,
                ) as ws:
                    log_info("✅ Connected to the server.", style="bold green")
                    await self.initialize_session(ws)
                    ws_task = asyncio.create_task(self.process_ws_messages(ws))

                    logger.info("Conversation started. Speak freely, and the assistant will respond.")
                    if self.prompts:
                        await self.send_initial_prompts(ws)
                    else:
                        self.mic.start_recording()
                        logger.info("Recording started. Listening for speech...")

                    await self.send_audio_loop(ws)

                    logger.info("before await ws_task")

                    await ws_task

                    logger.info("await ws_task complete")
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

    async def initialize_session(self, websocket):
        session_update = {
            "type": "session.update",
            "session": {
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
            },
        }
        log_ws_event("Outgoing", session_update)
        await websocket.send(json.dumps(session_update))

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

    async def process_ws_messages(self, websocket):
        while True:
            try:
                message = await websocket.recv()
                event = json.loads(message)
                log_ws_event("Incoming", event)
                await self.handle_event(event, websocket)
            except websockets.ConnectionClosed:
                log_warning("⚠️ WebSocket connection lost.")
                break

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

    async def send_error_message_to_assistant(self, error_message, websocket):
        error_item = {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": error_message}],
            },
        }
        log_ws_event("Outgoing", error_item)
        await websocket.send(json.dumps(error_item))

    async def handle_response_done(self):
        if self.response_start_time is not None:
            response_end_time = time.perf_counter()
            response_duration = response_end_time - self.response_start_time
            log_runtime("realtime_api_response", response_duration)
            self.response_start_time = None

        log_info("Assistant response complete.", style="bold blue")
        if self.audio_chunks:
            audio_data = b"".join(self.audio_chunks)
            logger.info(f"Sending {len(audio_data)} bytes of audio data to play_audio()")
            await play_audio(audio_data)
            logger.info("Finished play_audio()")
        self.assistant_reply = ""
        self.audio_chunks = []
        logger.info("Calling stop_receiving()")
        self.mic.stop_receiving()

    async def handle_event(self, event, websocket):
        event_type = event.get("type")
        if event_type == "response.created":
            self.mic.start_receiving()
            self.response_in_progress = True
        elif event_type == "response.output_item.added":
            await self.handle_output_item_added(event)
        elif event_type == "response.function_call_arguments.delta":
            self.function_call_args += event.get("delta", "")
        elif event_type == "response.function_call_arguments.done":
            await self.handle_function_call(event, websocket)
        elif event_type == "response.text.delta":
            delta = event.get("delta", "")
            self.assistant_reply += delta
            print(f"Assistant: {delta}", end="", flush=True)
        elif event_type == "response.audio.delta":
            self.audio_chunks.append(base64.b64decode(event["delta"]))
        elif event_type == "response.done":
            await self.handle_response_done()
        elif event_type == "error":
            await self.handle_error(event, websocket)
        elif event_type == "input_audio_buffer.speech_started":
            logger.info("Speech detected, listening...")
        elif event_type == "input_audio_buffer.speech_stopped":
            await self.handle_speech_stopped(websocket)
        elif event_type == "rate_limits.updated":
            self.response_in_progress = False
            self.mic.is_recording = True
            logger.info("Resumed recording after rate_limits.updated")

    async def handle_output_item_added(self, event):
        item = event.get("item", {})
        if item.get("type") == "function_call":
            self.function_call = item
            self.function_call_args = ""

    async def handle_function_call(self, event, websocket):
        if self.function_call:
            function_name = self.function_call.get("name")
            call_id = self.function_call.get("call_id")
            logger.info(f"Function call: {function_name} with args: {self.function_call_args}")
            try:
                args = json.loads(self.function_call_args) if self.function_call_args else {}
            except json.JSONDecodeError:
                args = {}
            await self.execute_function_call(function_name, call_id, args, websocket)

    async def execute_function_call(self, function_name, call_id, args, websocket):
        if function_name in function_map:
            try:
                result = await function_map[function_name](**args)
                log_tool_call(function_name, args, result)
            except Exception as e:
                error_message = f"Error executing function '{function_name}': {str(e)}"
                log_error(error_message)
                result = {"error": error_message}
                await self.send_error_message_to_assistant(error_message, websocket)
        else:
            error_message = f"Function '{function_name}' not found. Add to function_map in tools.py."
            log_error(error_message)
            result = {"error": error_message}
            await self.send_error_message_to_assistant(error_message, websocket)

        function_call_output = {
            "type": "conversation.item.create",
            "item": {
                "type": "function_call_output",
                "call_id": call_id,
                "output": json.dumps(result),
            },
        }
        log_ws_event("Outgoing", function_call_output)
        await websocket.send(json.dumps(function_call_output))
        await websocket.send(json.dumps({"type": "response.create"}))

        # Reset function call state
        self.function_call = None
        self.function_call_args = ""

    async def handle_error(self, event, websocket):
        error_message = event.get("error", {}).get("message", "")
        log_error(f"Error: {error_message}")
        if "buffer is empty" in error_message:
            logger.info("Received 'buffer is empty' error, no audio data sent.")
        elif "Conversation already has an active response" in error_message:
            logger.info("Received 'active response' error, adjusting response flow.")
            self.response_in_progress = True
        else:
            logger.error(f"Unhandled error: {error_message}")

    async def handle_speech_stopped(self, websocket):
        self.mic.stop_recording()
        logger.info("Speech ended, processing...")
        self.response_start_time = time.perf_counter()
        await websocket.send(json.dumps({"type": "input_audio_buffer.commit"}))

    async def send_audio_loop(self, websocket):
        try:
            while not self.exit_event.is_set():
                await asyncio.sleep(0.1)  # Small delay to accumulate audio data
                if not self.mic.is_receiving:
                    audio_data = self.mic.get_audio_data()
                    if audio_data and len(audio_data) > 0:
                        base64_audio = base64_encode_audio(audio_data)
                        if base64_audio:
                            audio_event = {
                                "type": "input_audio_buffer.append",
                                "audio": base64_audio,
                            }
                            log_ws_event("Outgoing", audio_event)
                            await websocket.send(json.dumps(audio_event))
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
            await websocket.close()


def main():
    log_info("Starting assistant. Press Ctrl+C to quit.")
    assistant = SimpleAssistant()
    try:
        asyncio.run(assistant.run())
    except KeyboardInterrupt:
        print("\nAssistant stopped.")


if __name__ == "__main__":
    main()
