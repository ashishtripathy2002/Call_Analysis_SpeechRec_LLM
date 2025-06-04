"""Unified Logger Client Part."""
from __future__ import (
    annotations,
)

from typing import TYPE_CHECKING

import zmq
from zmq.log.handlers import PUBHandler

if TYPE_CHECKING:
    from config_types import LoggingConfigs
    from loguru import Logger


def setup_network_logger_client(
    logging_configs: LoggingConfigs, logger: Logger,
) -> None:
    """Client logger setup."""
    zmq_socket = zmq.Context().socket(zmq.PUB)

    zmq_socket.connect(f"tcp://127.0.0.1:{logging_configs.log_server_port}")
    handler = PUBHandler(zmq_socket)

    # remove the previous settings so that it does not print in stderr and only to file
    logger.remove()
    logger.add(
        handler,
        format=logging_configs.client_log_format,
        enqueue=True,
        level=logging_configs.min_log_level,
        backtrace=True,  # Detailed error traces
        diagnose=True,  # Enable exception diagnostics
    )
