import logging
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient

from seriousdb import main
from seriousdb.cache import Cache
from seriousdb.logging_config import configure_logging


class LoggingConfigTests(unittest.TestCase):
    def setUp(self):
        logging.getLogger().handlers.clear()

    @patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"})
    def test_configure_logging_custom_level(self):
        configure_logging()
        self.assertEqual(logging.getLogger().level, logging.DEBUG)

    @patch.dict(os.environ, {"LOG_LEVEL": "INVALID_LEVEL"})
    def test_configure_logging_invalid_level_fallback(self):
        configure_logging()
        self.assertEqual(logging.getLogger().level, logging.INFO)

    @patch.dict(os.environ, {}, clear=True)
    def test_configure_logging_default_level(self):
        os.environ.pop("LOG_LEVEL", None)
        configure_logging()
        self.assertEqual(logging.getLogger().level, logging.INFO)


class CacheLoggingTests(unittest.TestCase):
    def test_cache_unavailable_logs_error(self):
        cache = Cache()
        with self.assertLogs("seriousdb.cache", level="ERROR") as cm:
            with self.assertRaises(Exception):
                cache.select("some_key")
        self.assertTrue(any("Database unavailable" in log for log in cm.output))

    def test_key_not_found_logs_debug(self):
        cache = Cache()
        cache.db = {}
        with self.assertLogs("seriousdb.cache", level="DEBUG") as cm:
            with self.assertRaises(Exception):
                cache.select("missing_key")
        self.assertTrue(any("Key not found" in log for log in cm.output))

    def test_load_new_database_logs_info(self):
        tmpdir = TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        db_file = str(Path(tmpdir.name) / ".sdb")

        cache = Cache()
        with self.assertLogs("seriousdb.cache", level="INFO") as cm:
            cache.load(db_file)
        self.assertTrue(any("creating a new database" in log for log in cm.output))


class ExceptionHandlerLoggingTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app, raise_server_exceptions=False)

    @patch.object(Cache, "select", side_effect=RuntimeError("Unexpected DB failure"))
    def test_global_exception_handler_logs_exception(self, mock_select):
        with self.assertLogs("seriousdb.main", level="ERROR") as cm:
            response = self.client.get("/db", params={"key": "test"})
            self.assertEqual(response.status_code, 500)
            self.assertEqual(response.json(), {"message": "Internal Server Error."})

        self.assertTrue(any("Unexpected application error" in log for log in cm.output))


if __name__ == "__main__":
    unittest.main()
