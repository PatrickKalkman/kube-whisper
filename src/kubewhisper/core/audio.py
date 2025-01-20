import sounddevice as sd
import numpy as np
import queue
from loguru import logger


class AsyncMicrophone:
    def __init__(self, sample_rate=16000, channels=1, buffer_duration_ms=1000):
        self.sample_rate = sample_rate
        self.channels = channels
        self.buffer_size = int(sample_rate * buffer_duration_ms / 1000)  # Calculate buffer size for 100ms
        self.audio_queue = queue.Queue()
        self.is_recording = False
        self.is_receiving = False
        self.stream = None
        self.current_buffer = []

    def audio_callback(self, indata, frames, time, status):
        if status:
            logger.warning(f"Audio callback status: {status}")
        if self.is_recording and not self.is_receiving:
            try:
                # Normalize audio data
                normalized = np.mean(indata, axis=1) if indata.ndim > 1 else indata
                self.current_buffer.append(normalized)

                # If we have collected enough data (100ms worth)
                if sum(len(chunk) for chunk in self.current_buffer) >= self.buffer_size:
                    combined = np.concatenate(self.current_buffer)
                    self.audio_queue.put(combined.astype(np.float32))
                    self.current_buffer = []  # Reset buffer
                    logger.debug(f"Buffered audio chunk: {len(combined)} samples")
            except Exception as e:
                logger.error(f"Error in audio callback: {e}")

    def start_recording(self):
        try:
            if not self.is_recording:
                self.is_recording = True
                self.stream = sd.InputStream(
                    samplerate=self.sample_rate, channels=self.channels, callback=self.audio_callback
                )
                self.stream.start()
                logger.info("Started audio recording")
                logger.info("Listening for commands... (Ctrl+C to exit)")
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            raise

    def get_audio_data(self):
        try:
            chunks = []
            # Get all available chunks from the queue
            while not self.audio_queue.empty():
                chunk = self.audio_queue.get_nowait()
                chunks.append(chunk)

            if chunks:
                combined = np.concatenate(chunks)
                # Convert to 16-bit PCM
                scaled = np.int16(combined * 32767)
                return scaled.tobytes()
            return None
        except Exception as e:
            logger.error(f"Error getting audio data: {e}")
            return None

    def stop_recording(self):
        self.is_recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            logger.info("Stopped audio recording")

    def start_receiving(self):
        self.is_receiving = True
        logger.info("Started receiving assistant response")

    def stop_receiving(self):
        self.is_receiving = False
        logger.info("Stopped receiving assistant response")

    def close(self):
        if self.stream:
            self.stream.close()
