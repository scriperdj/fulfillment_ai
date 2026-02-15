"""Unit tests for src/logging/logger.py."""

import json
import logging

import pytest

from src.logging.logger import (
    JSONFormatter,
    correlation_id_ctx,
    get_correlation_id,
    get_logger,
    set_correlation_id,
)


class TestJSONFormatter:
    """Tests for the JSONFormatter class."""

    def _make_record(self, msg="test message", level=logging.INFO, name="test.module"):
        logger = logging.getLogger(name)
        record = logger.makeRecord(
            name=name,
            level=level,
            fn="test.py",
            lno=1,
            msg=msg,
            args=(),
            exc_info=None,
        )
        return record

    def test_output_is_valid_json(self):
        """Formatter should produce valid JSON."""
        fmt = JSONFormatter()
        record = self._make_record()
        output = fmt.format(record)
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_contains_required_fields(self):
        """Output should contain timestamp, level, module, message."""
        fmt = JSONFormatter()
        record = self._make_record(msg="hello world", name="src.ml.inference")
        parsed = json.loads(fmt.format(record))
        assert "timestamp" in parsed
        assert parsed["level"] == "INFO"
        assert parsed["module"] == "src.ml.inference"
        assert parsed["message"] == "hello world"

    def test_level_names(self):
        """Different log levels should be represented by name."""
        fmt = JSONFormatter()
        for level, name in [
            (logging.DEBUG, "DEBUG"),
            (logging.WARNING, "WARNING"),
            (logging.ERROR, "ERROR"),
            (logging.CRITICAL, "CRITICAL"),
        ]:
            record = self._make_record(level=level)
            parsed = json.loads(fmt.format(record))
            assert parsed["level"] == name

    def test_extra_context_fields(self):
        """Extra fields passed on the record should appear in output."""
        fmt = JSONFormatter()
        record = self._make_record()
        record.order_id = "ORD-123"
        record.batch_job_id = "abc-uuid"
        parsed = json.loads(fmt.format(record))
        assert parsed["order_id"] == "ORD-123"
        assert parsed["batch_job_id"] == "abc-uuid"

    def test_correlation_id_included_when_set(self):
        """Correlation ID should appear in log when set in context."""
        fmt = JSONFormatter()
        with correlation_id_ctx("req-42"):
            record = self._make_record()
            parsed = json.loads(fmt.format(record))
        assert parsed["correlation_id"] == "req-42"

    def test_correlation_id_absent_when_not_set(self):
        """Correlation ID should not appear when not set."""
        # Reset to None explicitly
        set_correlation_id(None)
        # Directly set to None via the ContextVar
        from src.logging.logger import _correlation_id
        _correlation_id.set(None)

        fmt = JSONFormatter()
        record = self._make_record()
        parsed = json.loads(fmt.format(record))
        assert "correlation_id" not in parsed

    def test_exception_info_included(self):
        """Exception info should be included when present."""
        fmt = JSONFormatter()
        try:
            raise ValueError("boom")
        except ValueError:
            import sys
            record = self._make_record()
            record.exc_info = sys.exc_info()
        parsed = json.loads(fmt.format(record))
        assert "exception" in parsed
        assert "ValueError" in parsed["exception"]


class TestCorrelationID:
    """Tests for correlation ID utilities."""

    def test_set_and_get(self):
        """set_correlation_id should be retrievable via get_correlation_id."""
        cid = set_correlation_id("abc-123")
        assert cid == "abc-123"
        assert get_correlation_id() == "abc-123"

    def test_auto_generate(self):
        """set_correlation_id with no arg should auto-generate a hex ID."""
        cid = set_correlation_id()
        assert cid is not None
        assert len(cid) == 16  # uuid hex[:16]

    def test_context_manager_sets_and_resets(self):
        """correlation_id_ctx should set ID inside and reset after."""
        from src.logging.logger import _correlation_id
        _correlation_id.set(None)

        with correlation_id_ctx("ctx-123") as cid:
            assert cid == "ctx-123"
            assert get_correlation_id() == "ctx-123"

        # After exiting context, should be reset to None
        assert get_correlation_id() is None

    def test_context_manager_auto_generates(self):
        """correlation_id_ctx with no arg should auto-generate."""
        with correlation_id_ctx() as cid:
            assert cid is not None
            assert len(cid) == 16


class TestGetLogger:
    """Tests for the get_logger factory."""

    def test_returns_logger(self):
        """get_logger should return a logging.Logger instance."""
        logger = get_logger("test.module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"

    def test_has_json_handler(self):
        """Logger should have a handler with JSONFormatter."""
        # Use unique name to avoid handler reuse
        logger = get_logger("test.json_handler_check")
        assert len(logger.handlers) >= 1
        assert any(isinstance(h.formatter, JSONFormatter) for h in logger.handlers)

    def test_no_duplicate_handlers(self):
        """Calling get_logger twice for same name should not duplicate handlers."""
        name = "test.no_dup"
        # Clear any existing handlers
        existing = logging.getLogger(name)
        existing.handlers.clear()

        logger1 = get_logger(name)
        count1 = len(logger1.handlers)
        logger2 = get_logger(name)
        count2 = len(logger2.handlers)
        assert count1 == count2

    def test_propagate_is_false(self):
        """Logger should not propagate to root logger."""
        logger = get_logger("test.no_propagate")
        assert logger.propagate is False

    def test_log_output_is_json(self, capsys):
        """Actual log output should be valid JSON."""
        name = "test.output_json"
        existing = logging.getLogger(name)
        existing.handlers.clear()

        logger = get_logger(name)
        logger.info("hello from test", extra={"order_id": "X-1"})

        captured = capsys.readouterr()
        # stdout should contain JSON
        line = captured.out.strip()
        parsed = json.loads(line)
        assert parsed["message"] == "hello from test"
        assert parsed["order_id"] == "X-1"
