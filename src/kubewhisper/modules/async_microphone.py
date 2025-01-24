import pyaudio
import queue
import logging
from typing import Optional, Tuple


class AudioConfig:
    """Configuration constants for audio recording"""

    CHUNK_SIZE: int = 1024
    FORMAT: int = pyaudio.paInt16
    CHANNELS: int = 1
    SAMPLE_RATE: int = 24000


class MicrophoneState:
    """Enum-like class for microphone states"""

    IDLE = "idle"
    RECORDING = "recording"
    RECEIVING = "receiving"


class AsyncMicrophone:
    """Asynchronous microphone handler for recording audio streams.

    Manages audio input stream and provides methods for controlling recording state.
    """

    def __init__(self) -> None:
        """Initialize the microphone with PyAudio and setup the audio stream."""
        self._pyaudio = pyaudio.PyAudio()
        self._stream = self._pyaudio.open(
            format=AudioConfig.FORMAT,
            channels=AudioConfig.CHANNELS,
            rate=AudioConfig.SAMPLE_RATE,
            input=True,
            frames_per_buffer=AudioConfig.CHUNK_SIZE,
            stream_callback=self._audio_callback,
        )
        self._audio_queue: queue.Queue[bytes] = queue.Queue()
        self._state: str = MicrophoneState.IDLE
        logging.info("AsyncMicrophone initialized")

    def _audio_callback(self, in_data: bytes, frame_count: int, time_info: dict, status: int) -> Tuple[None, int]:
        """PyAudio callback function for handling incoming audio data.

        Args:
            in_data: Raw audio data
            frame_count: Number of frames
            time_info: Dictionary with timing information
            status: Status flags

        Returns:
            Tuple of (None, pyaudio.paContinue) to continue streaming
        """
        if self._state == MicrophoneState.RECORDING:
            self._audio_queue.put(in_data)
        return (None, pyaudio.paContinue)

    def start_recording(self) -> None:
        """Start recording audio from the microphone."""
        if self._state != MicrophoneState.RECORDING:
            self._state = MicrophoneState.RECORDING
            logging.info("Started recording")

    def stop_recording(self) -> None:
        """Stop recording audio from the microphone."""
        if self._state == MicrophoneState.RECORDING:
            self._state = MicrophoneState.IDLE
            logging.info("Stopped recording")

    def start_receiving(self) -> None:
        """Switch to receiving mode (stops recording)."""
        if self._state != MicrophoneState.RECEIVING:
            self._state = MicrophoneState.RECEIVING
            logging.info("Started receiving assistant response")

    def stop_receiving(self) -> None:
        """Stop receiving mode and return to idle state."""
        try:
            if self._state == MicrophoneState.RECEIVING:
                self._state = MicrophoneState.IDLE
                logging.info("Stopped receiving assistant response")
            else:
                logging.debug("Already not receiving, no action taken")
        except Exception as e:
            logging.error(f"Error stopping receiving: {str(e)}")
            raise

    def get_audio_data(self) -> Optional[bytes]:
        """Retrieve all accumulated audio data from the queue.

        Returns:
            Combined audio data as bytes, or None if no data available
        """
        data = b""
        while not self._audio_queue.empty():
            data += self._audio_queue.get()
        return data if data else None

    def close(self) -> None:
        """Clean up resources and close the audio stream."""
        try:
            self._stream.stop_stream()
            self._stream.close()
            self._pyaudio.terminate()
            logging.info("AsyncMicrophone closed")
        except Exception as e:
            logging.error(f"Error closing microphone: {str(e)}")
            raise

    @property
    def state(self) -> str:
        """Get the current state of the microphone.

        Returns:
            Current state as a string (IDLE, RECORDING, or RECEIVING)
        """
        return self._state
