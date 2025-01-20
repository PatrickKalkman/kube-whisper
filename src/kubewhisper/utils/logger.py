from loguru import logger


def setup_logger():
    """Configure loguru logger."""
    logger.add(
        "kubewhisper.log", rotation="10 MB", level="INFO", format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}"
    )
    return logger
