import click
import asyncio
from loguru import logger
from kubewhisper.core.assistant import Assistant
from kubewhisper.utils.logger import setup_logger


@click.group()
def cli():
    """KubeWhisper - Voice-controlled Kubernetes management."""
    pass


@cli.command()
def start():
    """Start the KubeWhisper assistant."""
    try:
        setup_logger()
        logger.info("Starting KubeWhisper...")

        assistant = Assistant()
        assistant.connect()
    except KeyboardInterrupt:
        logger.info("Shutting down KubeWhisper...")
        assistant.stop_event.set()
    except Exception as e:
        logger.error(f"Error running KubeWhisper: {e}")
        raise


if __name__ == "__main__":
    cli()
