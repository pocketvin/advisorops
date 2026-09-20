from datetime import datetime, time, timezone
from typing import Optional, Tuple
from zoneinfo import ZoneInfo

BUSINESS_TZ = ZoneInfo("Asia/Shanghai")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=BUSINESS_TZ)
    return parsed.astimezone(timezone.utc)


def to_iso(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def business_day_window(now: Optional[datetime] = None) -> Tuple[datetime, datetime]:
    current = (now or utc_now()).astimezone(BUSINESS_TZ)
    local_start = datetime.combine(current.date(), time.min, tzinfo=BUSINESS_TZ)
    local_end = datetime.combine(current.date(), time.max, tzinfo=BUSINESS_TZ)
    return local_start.astimezone(timezone.utc), local_end.astimezone(timezone.utc)
