import json
import logging
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from seriousdb import main
from seriousdb.cache import Cache
from seriousdb.logging_config import configure_logging


class LoggingConfigTests(unittest.TestCase):
    """Tests for the central logging configuration in logging_config.py."""

    def setUp(self):
        # Clear any handlers attached by previous tests so basicConfig
        # can take effect cleanly in each test.
        logging.getLogger().handlers.clear()

    @patch.dict(os.environ, {}, clear=True)
    def test_configure_logging_default_level(self):
        """When LOG_LEVEL is unset, the root logger should default to INFO."""
        os.environ.pop("LOG_LEVEL", None)
        configure_logging()
        self.assertEqual(logging.getLogger().level, logging.INFO)

    @patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"})
    def test_configure_logging_custom_level(self):
        """LOG_LEVEL=DEBUG should set the root logger to DEBUG."""
        configure_logging()
        self.assertEqual(logging.getLogger().level, logging.DEBUG)

    @patch.dict(os.environ, {"LOG_LEVEL": "INVALID_LEVEL"})
    def test_configure_logging_invalid_level_logs_warning(self):
        """An invalid LOG_LEVEL should fall back to INFO and log a warning."""
        # assertLogs captures the warning that configure_logging() emits
        # after calling basicConfig().
        with self.assertLogs("seriousdb.logging_config", level="WARNING") as cm:
            configure_logging()

        self.assertEqual(logging.getLogger().level, logging.INFO)
        self.assertTrue(any("not a valid log level" in log for log in cm.output))


class CacheLoggingTests(unittest.TestCase):
    """Tests that Cache operations emit the expected log records."""

    def test_insert_unavailable_logs_error(self):
        """insert() on an uninitialised cache should log ERROR and raise HTTPException."""
        cache = Cache()
        with self.assertLogs("seriousdb.cache", level="ERROR") as cm:
            with self.assertRaises(HTTPException):
                cache.insert("k", "v")
        self.assertTrue(any("Database unavailable" in log for log in cm.output))

    def test_select_unavailable_logs_error(self):
        """select() on an uninitialised cache should log ERROR and raise HTTPException."""
        cache = Cache()
        with self.assertLogs("seriousdb.cache", level="ERROR") as cm:
            with self.assertRaises(HTTPException):
                cache.select("some_key")
        self.assertTrue(any("Database unavailable" in log for log in cm.output))

    def test_key_not_found_logs_debug(self):
        """Querying a missing key should log DEBUG and raise HTTPException(404)."""
        cache = Cache()
        cache.db = {}
        with self.assertLogs("seriousdb.cache", level="DEBUG") as cm:
            with self.assertRaises(HTTPException):
                cache.select("missing_key")
        self.assertTrue(any("Key not found" in log for log in cm.output))

    def test_load_new_database_logs_info(self):
        """Loading from a non-existent path should create a new DB and log INFO."""
        tmpdir = TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        db_file = str(Path(tmpdir.name) / ".sdb")

        cache = Cache()
        with self.assertLogs("seriousdb.cache", level="INFO") as cm:
            cache.load(db_file)
        self.assertTrue(any("creating a new database" in log for log in cm.output))

    def test_load_corrupt_database_logs_warning(self):
        """Loading a corrupt JSON file should log WARNING and recover."""
        tmpdir = TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        db_file = str(Path(tmpdir.name) / ".sdb")

        # Write invalid JSON to simulate a corrupt database file.
        Path(db_file).write_text("NOT VALID JSON {{{")

        cache = Cache()
        with self.assertLogs("seriousdb.cache", level="WARNING") as cm:
            cache.load(db_file)

        self.assertTrue(any("Corrupt database file" in log for log in cm.output))
        # After recovery the cache should have the default data.
        self.assertEqual(cache.db, {"default": "default"})
        # The original corrupt file should have been renamed.
        self.assertTrue(
            any(p.name.startswith(".sdb.corrupt-") for p in Path(tmpdir.name).iterdir())
        )


class ExceptionHandlerLoggingTests(unittest.TestCase):
    """Tests for the global exception handler in main.py."""

    @patch.object(Cache, "select", side_effect=RuntimeError("Unexpected DB failure"))
    def test_global_exception_handler_logs_traceback_without_leaking(self, _mock):
        """Unhandled exceptions should be logged with a stack trace but
        the response must NOT expose internal error details to the client."""
        with TestClient(
            main.app,
            raise_server_exceptions=False,
        ) as client:
            with self.assertLogs("seriousdb.main", level="ERROR") as cm:
                response = client.get("/db", params={"key": "test"})

        # --- response is a safe, generic 500 ---
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"message": "Internal Server Error."})

        # --- the log contains the error message ---
        self.assertTrue(any("Unexpected application error" in log for log in cm.output))

        # --- the log contains a full stack trace ---
        self.assertTrue(any("Traceback" in log for log in cm.output))

        # --- internal details are NOT leaked to the client ---
        self.assertNotIn("Unexpected DB failure", response.text)


if __name__ == "__main__":
    unittest.main()
