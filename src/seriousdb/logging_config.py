import logging
import os
import sys

logger = logging.getLogger(__name__)


def configure_logging() -> None:
    log_level_string = os.getenv("LOG_LEVEL", "INFO").upper()

    levels = logging.getLevelNamesMapping()
    log_level = levels.get(log_level_string, logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
    )

    if log_level_string not in levels:
        logger.warning(
            "'%s' is not a valid log level. Falling back to 'INFO'.",
            log_level_string,
        )
