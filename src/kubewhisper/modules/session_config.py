from kubewhisper.modules.config import Config


class SessionConfig:
    def __init__(self, tools):
        self.config = {
            "modalities": ["text", "audio"],
            "instructions": Config.SESSION_INSTRUCTIONS,
            "voice": "coral",
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16",
            "turn_detection": {
                "type": "server_vad",
                "threshold": Config.SILENCE_THRESHOLD,
                "prefix_padding_ms": Config.PREFIX_PADDING_MS,
                "silence_duration_ms": Config.SILENCE_DURATION_MS,
            },
            "tools": tools,
        }
