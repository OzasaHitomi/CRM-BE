from datetime import datetime
from zoneinfo import ZoneInfo


def get_now() -> datetime:
    """
    Get the current date and time in Asia/Tokyo timezone.
    :return: datetime object with Asia/Tokyo timezone
    """
    return datetime.now(ZoneInfo("Asia/Tokyo"))
