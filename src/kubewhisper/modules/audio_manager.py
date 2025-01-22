import base64
from kubewhisper.modules.logging import logger
from kubewhisper.modules.async_microphone import AsyncMicrophone
from kubewhisper.modules.audio import play_audio


class AudioManager:
    def __init__(self):
        self.mic = AsyncMicrophone()
        self.audio_chunks = []
        self.is_receiving = False

    def start_recording(self):
        """Start recording audio from microphone"""
        self.mic.start_recording()
        logger.info("Recording started. Listening for speech...")

    def stop_recording(self):
        """Stop recording audio from microphone"""
        self.mic.stop_recording()

    def start_receiving(self):
        """Start receiving assistant response"""
        self.mic.start_receiving()
        self.is_receiving = True

    def stop_receiving(self):
        """Stop receiving assistant response"""
        self.mic.stop_receiving()
        self.is_receiving = False

    def get_audio_data(self):
        """Get recorded audio data from microphone"""
        return self.mic.get_audio_data()

    def add_audio_chunk(self, chunk):
        """Add an audio chunk from assistant response"""
        decoded_chunk = base64.b64decode(chunk)
        self.audio_chunks.append(decoded_chunk)

    async def play_response(self):
        """Play accumulated audio response"""
        if self.audio_chunks:
            audio_data = b"".join(self.audio_chunks)
            logger.info(f"Sending {len(audio_data)} bytes of audio data to play_audio()")
            await play_audio(audio_data)
            logger.info("Finished play_audio()")
            self.audio_chunks = []  # Clear chunks after playing

    def close(self):
        """Close the microphone connection"""
        self.mic.close()
