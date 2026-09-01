from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from freezegun import freeze_time

from crm_be.logic.calculate.calculate_datetime import get_now


@freeze_time("2026-07-09 12:00:00")
def test_get_now_returns_datetime_instance() -> None:
    result = get_now()

    assert isinstance(result, datetime)


@freeze_time("2026-07-09 12:00:00")
def test_get_now_has_asia_tokyo_tzinfo() -> None:
    result = get_now()

    assert result.tzinfo == ZoneInfo("Asia/Tokyo")


@freeze_time("2026-07-09 12:00:00")
def test_get_now_utc_offset_is_9_hours() -> None:
    result = get_now()

    assert result.utcoffset() == timedelta(hours=9)


@freeze_time("2026-07-09 12:00:00")
def test_get_now_tzname_is_jst() -> None:
    result = get_now()

    assert result.tzname() == "JST"


@freeze_time("2026-07-09 12:00:00")
def test_get_now_converts_frozen_utc_time_to_jst() -> None:
    result = get_now()

    assert result == datetime(2026, 7, 9, 21, 0, 0, tzinfo=ZoneInfo("Asia/Tokyo"))


def test_get_now_reflects_time_progression_across_calls() -> None:
    with freeze_time("2026-07-09 12:00:00") as frozen_time:
        first = get_now()

        frozen_time.tick(delta=timedelta(seconds=1))
        second = get_now()

    assert second > first
