# -*- coding: utf-8 -*-
"""Tests for per-user scheduled analysis dispatch in the Scheduler."""

import sys
import threading
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

# Pre-import the submodules so patch() can resolve them
import src.services.user_schedule_service as _uss_mod  # noqa: F401
import src.storage as _storage_mod  # noqa: F401


# ---------------------------------------------------------------------------
# Minimal schedule stub (same pattern as test_scheduler_background.py)
# ---------------------------------------------------------------------------

class _FakeJob:
    def __init__(self, schedule_module):
        self._schedule_module = schedule_module
        self.next_run = datetime(2026, 1, 1, 18, 0, 0)
        self.at_time = None

    @property
    def day(self):
        return self

    def at(self, value):
        self.at_time = value
        hour, minute = [int(part) for part in value.split(":")]
        self.next_run = datetime(2026, 1, 1, hour, minute, 0)
        return self

    def do(self, fn):
        self.job_func = fn
        self._schedule_module.jobs.append(self)
        return self


class _FakeScheduleModule:
    def __init__(self):
        self.jobs = []

    def every(self):
        return _FakeJob(self)

    def get_jobs(self):
        return list(self.jobs)

    def run_pending(self):
        return None

    def cancel_job(self, job):
        self.jobs.remove(job)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def scheduler():
    """Create a Scheduler instance with a fake schedule module."""
    fake_schedule = _FakeScheduleModule()
    with patch.dict(sys.modules, {"schedule": fake_schedule}):
        from src.scheduler import Scheduler
        sched = Scheduler(schedule_time="18:00")
        yield sched


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_dispatch_calls_get_due_users(scheduler):
    mock_service = MagicMock()
    mock_service.get_due_users.return_value = []

    with patch("src.scheduler.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 4, 11, 9, 15, 0)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        with patch.object(
            _uss_mod, "UserScheduleService", return_value=mock_service,
        ):
            with patch.object(_storage_mod, "DatabaseManager") as mock_db:
                mock_db.get_instance.return_value._SessionLocal = MagicMock()
                scheduler._dispatch_user_scheduled_analyses()

    mock_service.get_due_users.assert_called_once_with("09:15")


def test_dispatch_dedup_same_minute(scheduler):
    mock_service = MagicMock()
    mock_service.get_due_users.return_value = []

    with patch("src.scheduler.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 4, 11, 9, 15, 0)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        with patch.object(
            _uss_mod, "UserScheduleService", return_value=mock_service,
        ):
            with patch.object(_storage_mod, "DatabaseManager") as mock_db:
                mock_db.get_instance.return_value._SessionLocal = MagicMock()

                # First call
                scheduler._dispatch_user_scheduled_analyses()
                # Second call same minute -- should be deduped
                scheduler._dispatch_user_scheduled_analyses()

    assert mock_service.get_due_users.call_count == 1


def test_dispatch_different_minute_not_deduped(scheduler):
    mock_service = MagicMock()
    mock_service.get_due_users.return_value = []

    with patch("src.scheduler.datetime") as mock_dt:
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        with patch.object(
            _uss_mod, "UserScheduleService", return_value=mock_service,
        ):
            with patch.object(_storage_mod, "DatabaseManager") as mock_db:
                mock_db.get_instance.return_value._SessionLocal = MagicMock()

                mock_dt.now.return_value = datetime(2026, 4, 11, 9, 15, 0)
                scheduler._dispatch_user_scheduled_analyses()

                mock_dt.now.return_value = datetime(2026, 4, 11, 9, 16, 0)
                scheduler._dispatch_user_scheduled_analyses()

    assert mock_service.get_due_users.call_count == 2


def test_dispatch_starts_thread_for_due_user(scheduler):
    user_info = {
        "user_id": "abcd1234-0000-0000-0000-000000000000",
        "email": "test@example.com",
        "settings": {},
        "stock_codes": ["600519"],
    }
    mock_service = MagicMock()
    mock_service.get_due_users.return_value = [user_info]

    threads_started = []

    def fake_thread(*args, **kwargs):
        t = MagicMock()
        threads_started.append(kwargs)
        return t

    with patch("src.scheduler.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 4, 11, 9, 15, 0)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        with patch.object(
            _uss_mod, "UserScheduleService", return_value=mock_service,
        ):
            with patch.object(_storage_mod, "DatabaseManager") as mock_db:
                mock_db.get_instance.return_value._SessionLocal = MagicMock()

                with patch("src.scheduler.threading.Thread", side_effect=fake_thread):
                    scheduler._dispatch_user_scheduled_analyses()

    assert len(threads_started) == 1
    assert threads_started[0]["daemon"] is True
    assert "abcd1234" in threads_started[0]["name"]


def test_run_user_analysis_with_notification_success(scheduler):
    mock_service = MagicMock()
    mock_service.run_user_analysis.return_value = {
        "analyzed": 2,
        "total": 3,
    }
    user_info = {
        "user_id": "abcd1234-0000-0000-0000-000000000000",
        "email": "test@example.com",
    }

    # Should not raise
    scheduler._run_user_analysis_with_notification(mock_service, user_info)
    mock_service.run_user_analysis.assert_called_once_with(
        "abcd1234-0000-0000-0000-000000000000"
    )


def test_run_user_analysis_with_notification_failure(scheduler):
    mock_service = MagicMock()
    mock_service.run_user_analysis.side_effect = RuntimeError("boom")
    user_info = {
        "user_id": "abcd1234-0000-0000-0000-000000000000",
        "email": "test@example.com",
    }

    # Should not raise -- exception is caught internally
    scheduler._run_user_analysis_with_notification(mock_service, user_info)


def test_dispatch_handles_db_error_gracefully(scheduler):
    """If DatabaseManager is unavailable, dispatch logs and continues."""
    with patch("src.scheduler.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 4, 11, 9, 15, 0)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        with patch.object(_storage_mod, "DatabaseManager") as mock_db:
            mock_db.get_instance.side_effect = RuntimeError("no db")

            # Should not raise
            scheduler._dispatch_user_scheduled_analyses()
