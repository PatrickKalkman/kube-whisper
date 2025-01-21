import pyaudio
import queue
from loguru import logger

CHUNK_SIZE = 1024
SAMPLE_RATE = 24000
FORMAT = pyaudio.paInt16

class AsyncMicrophone:
    def __init__(self):
        self.audio = pyaudio.PyAudio()
        self.mic_queue = queue.Queue()
        self.audio_buffer = bytearray()
        self.is_recording = False
        self.is_receiving = False
        self.stream = None
        
    def audio_callback(self, in_data, frame_count, time_info, status):
        if status:
            logger.warning(f"Audio callback status: {status}")
        if self.is_recording and not self.is_receiving:
            self.mic_queue.put(in_data)
        return (None, pyaudio.paContinue)

    def start_recording(self):
        try:
            if not self.is_recording:
                self.is_recording = True
                self.stream = self.audio.open(
                    format=FORMAT,
                    channels=1,
                    rate=SAMPLE_RATE,
                    input=True,
                    stream_callback=self.audio_callback,
                    frames_per_buffer=CHUNK_SIZE
                )
                self.stream.start_stream()
                logger.info("Started audio recording")
                logger.info("Listening for commands... (Ctrl+C to exit)")
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            raise

    def get_audio_data(self):
        try:
            if not self.mic_queue.empty():
                return self.mic_queue.get_nowait()
            return None
        except Exception as e:
            logger.error(f"Error getting audio data: {e}")
            return None

    def stop_recording(self):
        self.is_recording = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            logger.info("Stopped audio recording")

    def close(self):
        self.stop_recording()
        if self.audio:
            self.audio.terminate()
