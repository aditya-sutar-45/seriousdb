import logging
import os


def configure_logging() -> None:
    log_level_string = os.getenv("LOG_LEVEL", "INFO").upper()

    levels = logging.getLevelNamesMapping()
    if log_level_string in levels:
        log_level = levels[log_level_string]
    else:
        print(
            f"WARNING '{log_level_string}' is not a valid log level. Falling back to 'INFO'."
        )
        log_level = logging.INFO

    logging.basicConfig(
        level=log_level, format="[%(asctime)s] %(levelname)s [%(name)s] %(message)s"
    )
