import sounddevice as sd
from queue import Queue
from loguru import logger


class VoiceRecorder:
    def __init__(self, sample_rate: int = 16000, chunk_duration: float = 0.1):
        """Initialize voice recorder with specified parameters."""
        self.sample_rate = sample_rate
        self.chunk_samples = int(sample_rate * chunk_duration)
        self.audio_queue = Queue()
        self.is_recording = False
        self.stream = None

    def audio_callback(self, indata, frames, time, status):
        """Callback function for audio stream."""
        if status:
            logger.warning(f"Audio callback status: {status}")
        if self.is_recording:
            self.audio_queue.put(indata.copy())

    def start_recording(self):
        """Start recording audio."""
        try:
            self.is_recording = True
            self.stream = sd.InputStream(
                samplerate=self.sample_rate, channels=1, callback=self.audio_callback, blocksize=self.chunk_samples
            )
            self.stream.start()
            logger.info("Started audio recording")
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            raise

    def stop_recording(self):
        """Stop recording audio."""
        if self.stream:
            self.is_recording = False
            self.stream.stop()
            self.stream.close()
            logger.info("Stopped audio recording")
