import os
import json
import base64
import socket
import websocket
import threading
from loguru import logger
from dotenv import load_dotenv
from .kubernetes import KubernetesManager
from .audio import AsyncMicrophone

load_dotenv()

class Assistant:
    def __init__(self):
        self.k8s = KubernetesManager()
        self.mic = AsyncMicrophone()
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        self.commands = {
            "get_pods": (self.k8s.get_pod_count, "Getting pod count..."),
            "get_nodes": (self.k8s.get_node_count, "Getting node count..."),
            "cluster_status": (self.k8s.get_cluster_status, "Getting cluster status..."),
        }

        # State management
        self.stop_event = threading.Event()

    def connect(self):
        url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17"
        headers = [
            f"Authorization: Bearer {self.api_key}",
            "OpenAI-Beta: realtime=v1"
        ]
        
        try:
            ws = websocket.create_connection(url, header=headers)
            logger.info("Connected to OpenAI realtime API")
            
            # Initialize session
            self.initialize_session(ws)
            
            # Start recording
            self.mic.start_recording()
            
            # Start message processing and audio sending threads
            receive_thread = threading.Thread(target=self.process_ws_messages, args=(ws,))
            audio_thread = threading.Thread(target=self.send_audio_loop, args=(ws,))
            
            receive_thread.start()
            audio_thread.start()
            
            # Wait for stop event
            while not self.stop_event.is_set():
                threading.Event().wait(0.1)
                
            # Cleanup
            ws.close()
            receive_thread.join()
            audio_thread.join()
            
        except Exception as e:
            logger.error(f"Error in connection: {e}")
            raise

    def initialize_session(self, ws):
        session_update = {
            "type": "session.update",
            "session": {
                "instructions": """You are a Kubernetes cluster assistant. Help manage and monitor the cluster through voice commands.
                When you hear commands about pods, nodes, or cluster status, execute the appropriate function and provide clear responses.
                Keep responses concise and informative.""",
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500
                },
                "voice": "alloy",
                "temperature": 1,
                "max_response_output_tokens": 4096,
                "modalities": ["text", "audio"],
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1"
                }
            }
        }
        ws.send(json.dumps(session_update))

    async def process_ws_messages(self, websocket):
        while not self.exit_event.is_set():
            try:
                message = await websocket.recv()
                event = json.loads(message)
                await self.handle_event(event, websocket)
            except ConnectionClosedError:
                logger.warning("WebSocket connection closed")
                break
            except Exception as e:
                logger.error(f"Error processing message: {e}")

    async def handle_event(self, event, websocket):
        event_type = event.get("type")
        logger.debug(f"Received event type: {event_type}")

        if event_type == "session.created":
            logger.info("Session created successfully")
            logger.info("Ready to accept voice commands. Try saying 'How many pods are running?'")

        elif event_type == "input_audio_buffer.speech_started":
            logger.info("Speech detected, listening...")

        elif event_type == "input_audio_buffer.speech_stopped":
            logger.info("Speech ended, processing...")
            await websocket.send(json.dumps({"type": "input_audio_buffer.commit"}))

        elif event_type == "text.generation":
            text = event.get("text", "")
            logger.info(f"Understood command: {text}")
            await self.process_command(text, websocket)

        elif event_type == "error":
            error_msg = event.get("error", {}).get("message", "Unknown error")
            logger.error(f"Error from API: {error_msg}")
            if "rate limits" in error_msg.lower():
                logger.info("Waiting for rate limit to reset...")
                await asyncio.sleep(1)

        elif event_type == "audio.data":
            # Handle incoming audio response from the assistant
            audio_data = event.get("audio", {}).get("data")
            if audio_data:
                self.audio_chunks.append(base64.b64decode(audio_data))

    async def process_command(self, text, websocket):
        # Normalize text and try to match commands
        text_lower = text.lower()
        command_executed = False

        for cmd_key, (cmd_func, cmd_msg) in self.commands.items():
            if cmd_key in text_lower:
                logger.info(cmd_msg)
                try:
                    result = cmd_func()
                    response = f"Command result: {result}"
                    logger.info(response)

                    # Send response back through websocket
                    await websocket.send(json.dumps({"type": "text.generation", "text": response}))
                    command_executed = True
                    break
                except Exception as e:
                    error_msg = f"Error executing command: {str(e)}"
                    logger.error(error_msg)
                    await websocket.send(json.dumps({"type": "text.generation", "text": error_msg}))
                    command_executed = True
                    break

        if not command_executed:
            logger.info("Command not recognized")
            await websocket.send(
                json.dumps(
                    {
                        "type": "text.generation",
                        "text": "I'm sorry, I didn't understand that command. Try asking about pods or nodes.",
                    }
                )
            )

    async def send_audio_loop(self, websocket):
        while not self.exit_event.is_set():
            try:
                if not self.mic.is_receiving:
                    audio_data = self.mic.get_audio_data()
                    if audio_data:
                        base64_audio = base64.b64encode(audio_data).decode("utf-8")
                        event = {"type": "input_audio_buffer.append", "audio": base64_audio}
                        await websocket.send(json.dumps(event))
                        logger.debug("Sent audio chunk")
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Error in audio loop: {e}")
                await asyncio.sleep(1)  # Wait before retrying

    def stop(self):
        self.exit_event.set()
        self.mic.stop_recording()
        self.mic.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.stop()
