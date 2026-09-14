import logging
import os
import sys

logger = logging.getLogger(__name__)


def configure_logging() -> None:
    log_level_string = os.getenv("LOG_LEVEL", "INFO").upper()

    levels = logging.getLevelNamesMapping()
    invalid_level = False

    if log_level_string in levels:
        log_level = levels[log_level_string]
    else:
        invalid_level = True
        log_level = logging.INFO

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
    )

    if invalid_level:
        logger.warning(
            "'%s' is not a valid log level. Falling back to 'INFO'.",
            log_level_string,
        )
