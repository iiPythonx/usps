# Copyright (c) 2024 iiPython

# Modules
from datetime import datetime

# Actual utilities
def pluralize(item: int) -> str:
    return "s" if item > 1 else ""

def get_delta(time: datetime) -> str:
    delta = datetime.now() - time

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
        return f"{delta.days} day{pluralize(delta.days)} ago ({time})"

    elif delta_hours:
        return f"{delta_hours} hour{pluralize(delta_hours)} ago ({time})"

    elif delta_minutes:
        return f"{delta_minutes} minute{pluralize(delta_minutes)} ago ({time})"

    else:
        return f"{delta.seconds} second{pluralize(delta.seconds)} ago ({time})"
