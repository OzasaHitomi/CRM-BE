from enum import StrEnum


class ActivityType(StrEnum):
    call = "call"
    email = "email"
    visit = "visit"
    online_meeting = "online_meeting"
    other = "other"
