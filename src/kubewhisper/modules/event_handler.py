import time
import base64
import json
from kubewhisper.modules.logging import log_tool_call, log_error, log_info, logger
from kubewhisper.utils.utils import log_runtime
from kubewhisper.modules.audio import play_audio


class EventHandler:
    def __init__(self, mic, ws_manager, function_map):
        self.mic = mic
        self.ws_manager = ws_manager
        self.function_map = function_map
        self.assistant_reply = ""
        self.audio_chunks = []
        self.response_in_progress = False
        self.function_call = None
        self.function_call_args = ""
        self.response_start_time = None

    async def handle_event(self, event):
        event_type = event.get("type")
        handlers = {
            "response.created": self.handle_response_created,
            "response.output_item.added": lambda: self.handle_output_item_added(event),
            "response.function_call_arguments.delta": lambda: self.handle_function_call_arguments_delta(
                event.get("delta", "")
            ),
            "response.function_call_arguments.done": lambda: self.handle_function_call(event),
            "response.text.delta": lambda: self.handle_text_delta(event.get("delta", "")),
            "response.audio.delta": lambda: self.handle_audio_delta(event["delta"]),
            "response.done": self.handle_response_done,
            "error": lambda: self.handle_error(event),
            "input_audio_buffer.speech_started": self.handle_speech_started,
            "input_audio_buffer.speech_stopped": self.handle_speech_stopped,
            "rate_limits.updated": self.handle_rate_limits_updated,
        }

        handler = handlers.get(event_type)
        if handler:
            await handler()

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

    async def handle_speech_stopped(self):
        self.mic.stop_recording()
        logger.info("Speech ended, processing...")
        self.response_start_time = time.perf_counter()
        await self.ws_manager.send_message({"type": "input_audio_buffer.commit"})

    async def handle_rate_limits_updated(self):
        self.response_in_progress = False
        self.mic.is_recording = True
        logger.info("Resumed recording after rate_limits.updated")

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
        if function_name in self.function_map:
            try:
                result = await self.function_map[function_name](**args)
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

    async def send_error_message_to_assistant(self, error_message):
        await self.ws_manager.send_error_message(error_message)
