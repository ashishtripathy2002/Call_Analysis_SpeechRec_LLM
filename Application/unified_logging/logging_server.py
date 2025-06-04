"""Server side of logger."""

import argparse
from pathlib import Path

import zmq
from config_types import LoggingConfigs
from loguru import logger


def set_logging_configs(logging_configs: LoggingConfigs) -> None:
    """Configure logger."""
    logger.remove()

    logger.add(
        logging_configs.log_file_name,
        rotation=logging_configs.log_rotation,  # Rotate at 00:00
        compression=logging_configs.log_compression,  # Compress rotated files
        format=logging_configs.server_log_format,
        level=logging_configs.min_log_level,
        enqueue=True,  # Thread-safe logging
        backtrace=True,  # Detailed error traces
        diagnose=True,  # Enable exception diagnostics
    )


def start_logging_server(logging_configs: LoggingConfigs) -> None:
    """Log Server Action."""
    socket = zmq.Context().socket(zmq.SUB)
    socket.bind(f"tcp://127.0.0.1:{logging_configs.log_server_port}")
    socket.subscribe("")

    while True:
        try:
            ret_val = socket.recv_multipart()
            log_level_name, message = ret_val

            log_level_name = log_level_name.decode("utf8").strip()
            message = message.decode("utf8").strip()

            logger.log(log_level_name, message)

        except Exception:  # noqa: BLE001
            logger.exception("Got an exception when logging: ")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config_file_path",
        default=str(Path.cwd() / "Application" / "unified_logging" / "configs.toml"),
        help="Path to the logging configuration file",
    )
    args = parser.parse_args()

    CONFIG_FILE_NAME = Path(args.config_file_path)
    logging_configs = LoggingConfigs.load_from_path(CONFIG_FILE_NAME)
    set_logging_configs(logging_configs)
    start_logging_server(logging_configs)
