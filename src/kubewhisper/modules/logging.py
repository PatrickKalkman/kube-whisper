from loguru import logger

# Configure loguru
logger.remove()  # Remove default handler
logger.add(
    sink=lambda msg: print(msg),
    format="<level>{time:HH:mm:ss}</level> | {message}",
    colorize=True,
    level="INFO"
)


# Function to log WebSocket events
def log_ws_event(direction, event):
    event_type = event.get("type", "Unknown")
    event_emojis = {
        "session.update": "🛠️",
        "session.created": "🔌",
        "session.updated": "🔄",
        "input_audio_buffer.append": "🎤",
        "input_audio_buffer.commit": "✅",
        "input_audio_buffer.speech_started": "🗣️",
        "input_audio_buffer.speech_stopped": "🤫",
        "input_audio_buffer.cleared": "🧹",
        "input_audio_buffer.committed": "📨",
        "conversation.item.create": "📥",
        "conversation.item.delete": "🗑️",
        "conversation.item.truncate": "✂️",
        "conversation.item.created": "📤",
        "conversation.item.deleted": "🗑️",
        "conversation.item.truncated": "✂️",
        "response.create": "➡️",
        "response.created": "📝",
        "response.output_item.added": "➕",
        "response.output_item.done": "✅",
        "response.text.delta": "✍️",
        "response.text.done": "📝",
        "response.audio.delta": "🔊",
        "response.audio.done": "🔇",
        "response.done": "✔️",
        "response.cancel": "⛔",
        "response.function_call_arguments.delta": "📥",
        "response.function_call_arguments.done": "📥",
        "rate_limits.updated": "⏳",
        "error": "❌",
        "conversation.item.input_audio_transcription.completed": "📝",
        "conversation.item.input_audio_transcription.failed": "⚠️",
    }
    emoji = event_emojis.get(event_type, "❓")
    icon = "⬆️ - Out" if direction == "Outgoing" else "⬇️ - In"
    color = "<cyan>" if direction == "Outgoing" else "<green>"
    logger.info(f"{color}{emoji} {icon} {event_type}</cyan>")


def log_tool_call(function_name, args, result):
    logger.info(f"<magenta>🛠️ Calling function: {function_name} with args: {args}</magenta>")
    logger.info(f"<yellow>🛠️ Function call result: {result}</yellow>")


def log_error(message):
    logger.error(f"<red>{message}</red>")


def log_info(message, style="white"):
    logger.info(f"<{style}>{message}</{style}>")


def log_warning(message):
    logger.warning(f"<yellow>{message}</yellow>")
