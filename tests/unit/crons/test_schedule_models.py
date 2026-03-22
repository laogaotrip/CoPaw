# -*- coding: utf-8 -*-
"""Unit tests for cron schedule model validation."""

from __future__ import annotations

import pytest

from copaw.app.crons.models import ScheduleSpec


def test_once_schedule_requires_at() -> None:
    with pytest.raises(ValueError, match="schedule.at is required when type=once"):
        ScheduleSpec(type="once")


def test_interval_schedule_requires_every_seconds() -> None:
    with pytest.raises(
        ValueError,
        match="schedule.every_seconds is required when type=interval",
    ):
        ScheduleSpec(type="interval")


def test_on_message_schedule_rejects_invalid_pattern() -> None:
    with pytest.raises(ValueError, match="invalid schedule.pattern regex"):
        ScheduleSpec(type="on_message", pattern="(")


def test_cron_numeric_day_of_week_is_normalized() -> None:
    spec = ScheduleSpec(type="cron", cron="0 9 * * 1")
    assert spec.cron == "0 9 * * mon"

