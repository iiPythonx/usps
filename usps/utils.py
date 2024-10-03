# Copyright (c) 2024 iiPython

# Modules
from time import localtime
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta, timezone

# Timezones
TIMEZONE_MAPPING = {
    "AL": ZoneInfo("US/Central"),
    "AK": ZoneInfo("US/Alaska"),    # Also HST
    "AZ": ZoneInfo("US/Mountain"),
    "AR": ZoneInfo("US/Central"),
    "CA": ZoneInfo("US/Pacific"),
    "CO": ZoneInfo("US/Mountain"),
    "CT": ZoneInfo("US/Eastern"),
    "DE": ZoneInfo("US/Eastern"),
    "FL": ZoneInfo("US/Eastern"),   # Also CST
    "GA": ZoneInfo("US/Eastern"),
    "HI": ZoneInfo("US/Hawaii"),
    "ID": ZoneInfo("US/Mountain"),  # Also PST
    "IL": ZoneInfo("US/Central"),
    "IN": ZoneInfo("US/Eastern"),   # Also CST
    "IA": ZoneInfo("US/Central"),
    "KS": ZoneInfo("US/Central"),   # Also MST
    "KY": ZoneInfo("US/Eastern"),   # Also CST
    "LA": ZoneInfo("US/Central"),
    "ME": ZoneInfo("US/Eastern"),
    "MD": ZoneInfo("US/Eastern"),
    "MA": ZoneInfo("US/Eastern"),
    "MI": ZoneInfo("US/Eastern"),   # Also CST
    "MN": ZoneInfo("US/Central"),
    "MS": ZoneInfo("US/Central"),
    "MO": ZoneInfo("US/Central"),
    "MT": ZoneInfo("US/Mountain"),
    "NE": ZoneInfo("US/Central"),   # Also MST
    "NV": ZoneInfo("US/Pacific"),   # Also MST
    "NH": ZoneInfo("US/Eastern"),
    "NJ": ZoneInfo("US/Eastern"),
    "NM": ZoneInfo("US/Mountain"),
    "NY": ZoneInfo("US/Eastern"),
    "NC": ZoneInfo("US/Eastern"),
    "ND": ZoneInfo("US/Central"),   # Also MST
    "OH": ZoneInfo("US/Eastern"),
    "OK": ZoneInfo("US/Central"),
    "OR": ZoneInfo("US/Pacific"),   # My hometown was MST lmao
    "PA": ZoneInfo("US/Eastern"),
    "RI": ZoneInfo("US/Eastern"),
    "SC": ZoneInfo("US/Eastern"),
    "SD": ZoneInfo("US/Central"),   # 50/50 with MST
    "TN": ZoneInfo("US/Central"),   # Also EST
    "TX": ZoneInfo("US/Central"),   # Also MST
    "UT": ZoneInfo("US/Mountain"),
    "VT": ZoneInfo("US/Eastern"),
    "VA": ZoneInfo("US/Eastern"),
    "WA": ZoneInfo("US/Pacific"),
    "WV": ZoneInfo("US/Eastern"),
    "WI": ZoneInfo("US/Central"),
    "WY": ZoneInfo("US/Mountain")
}
LOCAL_TIMEZONE = timezone(timedelta(seconds = localtime().tm_gmtoff))

# Actual utilities
def pluralize(item: int) -> str:
    return "s" if item > 1 else ""

def get_delta(location: str, time: datetime) -> str:

    # Calculate the timezone for the given location
    state = location.encode().replace(b"\xc2\xa0", b" ").split(b" ")[1].decode()
    if state in TIMEZONE_MAPPING:
        time = time.replace(tzinfo = TIMEZONE_MAPPING[state]).astimezone(LOCAL_TIMEZONE)

    delta = datetime.now(timezone(timedelta(seconds = localtime().tm_gmtoff))) - time

    # Figure out delta
    delta_minutes = delta.seconds // 60
    delta_hours = delta_minutes // 60

    # Make sure we don't go negative
    if any([
        delta.days < 0,
        delta_hours < 0,
        delta_minutes < 0
    ]):
        return str(time)

    # Process each item
    if delta.days:
        return f"{delta.days} day{pluralize(delta.days)} ago\t({time})"

    elif delta_hours:
        return f"{delta_hours} hour{pluralize(delta_hours)} ago\t({time})"

    elif delta_minutes:
        return f"{delta_minutes} minute{pluralize(delta_minutes)} ago\t({time})"

    else:
        return f"{delta.seconds} second{pluralize(delta.seconds)} ago\t({time})"
