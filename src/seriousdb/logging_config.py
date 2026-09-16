import logging
import sys

from .config import LOG_LEVEL


def configure_logging() -> None:
    logging.basicConfig(
        level=LOG_LEVEL.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
        force=True,
    )
