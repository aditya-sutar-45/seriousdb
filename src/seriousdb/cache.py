import json
import logging
import os
import time
from threading import Lock
from fastapi import HTTPException

logger = logging.getLogger(__name__)

DEFAULT_DB = {"default": "default"}


class Cache:
    def __init__(self):
        self.filename = None
        self.db = None
        self.lock = Lock()

    def insert(self, key: str, value: str):
        with self.lock:
            if self.db is None:
                logger.error("Database unavailable: %s", self.filename)
                raise HTTPException(
                    status_code=500,
                    detail=f"Database file {self.filename} could not be opened and loaded",
                )
            self.db[key] = value
        return value

    def select(self, key: str):
        with self.lock:
            if self.db is None:
                logger.error("Database unavailable: %s", self.filename)
                raise HTTPException(
                    status_code=500,
                    detail=f"Database file {self.filename} could not be opened and loaded",
                )
            val = self.db.get(key, None)
        if val is None:
            logger.debug("Key not found: %s", key)
            raise HTTPException(status_code=404, detail=f"No value set for key {key}")
        return val

    def delete(self, key: str):
        with self.lock:
            if self.db is None:
                logger.error("Database unavailable: %s", self.filename)
                raise HTTPException(
                    status_code=500,
                    detail=f"Database file {self.filename} could not be opened and loaded",
                )
            val = self.db.pop(key, None)
        if val is None:
            logger.debug("Key not found: %s", key)
            raise HTTPException(status_code=404, detail=f"No value set for key {key}")
        return val

    def load(self, filename: str):
        with self.lock:
            if not os.path.isfile(filename):
                logger.info(
                    "Database file %s does not exist; creating a new database", filename
                )
                self.db = _write_default(filename)
            else:
                try:
                    with open(filename, "rb") as f:
                        self.db = json.loads(f.read().decode())
                        logger.info("Loaded database from %s", filename)
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    backup = f"{filename}.corrupt-{int(time.time())}"
                    os.replace(filename, backup)
                    logger.warning(
                        "Corrupt database file %s (%s); moved to %s and starting fresh",
                        filename,
                        e,
                        backup,
                    )
                    self.db = _write_default(filename)
            self.filename = filename

    def flush(self):
        with self.lock:
            if self.db is None:
                logger.error("Database unavailable: %s", self.filename)
                return
            with open(self.filename, "wb+") as f:
                f.write(json.dumps(self.db).encode())


def _write_default(filename: str) -> dict:
    with open(filename, "wb") as f:
        f.write(json.dumps(DEFAULT_DB).encode())
    return dict(DEFAULT_DB)
