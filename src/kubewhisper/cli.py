import os
import asyncio

from kubewhisper.modules.simple_assistant import SimpleAssistant
from kubewhisper.modules.logging import log_info

REALTIME_API_URL = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview"
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    print("Error: OPENAI_API_KEY not found in environment variables.")
    exit(1)


def main():
    log_info("Starting assistant. Press Ctrl+C to quit.")
    assistant = SimpleAssistant(API_KEY, REALTIME_API_URL)
    try:
        asyncio.run(assistant.run())
    except KeyboardInterrupt:
        log_info("Assistant stopped.")


if __name__ == "__main__":
    main()
