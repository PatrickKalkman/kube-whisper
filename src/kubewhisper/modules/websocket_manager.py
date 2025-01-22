import json
import websockets
from kubewhisper.modules.logging import log_info, log_ws_event
from kubewhisper.utils.utils import base64_encode_audio


class WebSocketManager:
    def __init__(self, openai_api_key, realtime_api_url):
        self.openai_api_key = openai_api_key
        self.realtime_api_url = realtime_api_url
        self.websocket = None

    async def connect(self):
        """Establish WebSocket connection"""
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "OpenAI-Beta": "realtime=v1",
        }

        self.websocket = await websockets.connect(
            self.realtime_api_url,
            additional_headers=headers,
            close_timeout=120,
            ping_interval=30,
            ping_timeout=10,
        )
        log_info("✅ Connected to the server.")
        return self.websocket

    async def initialize_session(self, session_config):
        """Initialize the WebSocket session with configuration"""
        session_update = {"type": "session.update", "session": session_config}
        log_ws_event("Outgoing", session_update)
        await self.send_message(session_update)

    async def send_message(self, message):
        """Send a message through the WebSocket"""
        if not self.websocket:
            raise ConnectionError("WebSocket not connected")
        await self.websocket.send(json.dumps(message))

    async def receive_message(self):
        """Receive a message from the WebSocket"""
        if not self.websocket:
            raise ConnectionError("WebSocket not connected")
        message = await self.websocket.recv()
        return json.loads(message)

    async def send_audio_data(self, audio_data):
        """Send audio data through the WebSocket"""
        if audio_data and len(audio_data) > 0:
            base64_audio = base64_encode_audio(audio_data)
            if base64_audio:
                audio_event = {
                    "type": "input_audio_buffer.append",
                    "audio": base64_audio,
                }
                log_ws_event("Outgoing", audio_event)
                await self.send_message(audio_event)

    async def send_user_input(self, user_input):
        """Send user text input"""
        event = {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": user_input}],
            },
        }
        await self.send_message(event)
        await self.send_message({"type": "response.create"})

    async def send_function_call_output(self, call_id, output):
        """Send function call output"""
        function_call_output = {
            "type": "conversation.item.create",
            "item": {
                "type": "function_call_output",
                "call_id": call_id,
                "output": json.dumps(output),
            },
        }
        log_ws_event("Outgoing", function_call_output)
        await self.send_message(function_call_output)
        await self.send_message({"type": "response.create"})

    async def send_error_message(self, error_message):
        """Send error message"""
        error_item = {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": error_message}],
            },
        }
        log_ws_event("Outgoing", error_item)
        await self.send_message(error_item)

    async def close(self):
        """Close the WebSocket connection"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
