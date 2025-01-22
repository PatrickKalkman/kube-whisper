import base64
from datetime import datetime
import json
from kubewhisper.modules.logging import logger

RUN_TIME_TABLE_LOG_JSON = "runtime_time_table.jsonl"


def log_runtime(function_or_name: str, duration: float):
    """Log the runtime of a function to a JSONL file."""
    jsonl_file = RUN_TIME_TABLE_LOG_JSON
    time_record = {
        "timestamp": datetime.now().isoformat(),
        "function": function_or_name,
        "duration": f"{duration:.4f}",
    }
    with open(jsonl_file, "a") as file:
        json.dump(time_record, file)
        file.write("\n")

    logger.info(f"⏰ {function_or_name}() took {duration:.4f} seconds")


def base64_encode_audio(audio_bytes):
    """Encode audio bytes to base64 string."""
    return base64.b64encode(audio_bytes).decode("utf-8")
