# Copyright (c) 2024 iiPython

# Modules
import re
from datetime import datetime
from dataclasses import dataclass

# Typing
@dataclass
class Step:
    details: str
    location: str
    time: datetime

@dataclass
class Package:
    expected: list[datetime] | None
    last_status: str
    state: str
    steps: list[Step]

# Constants
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.1"

# Handle actual tracking
from .ups import UPSTracking  # noqa: E402
from .usps import USPSTracking  # noqa: E402

UPS_PACKAGE_REGEX = re.compile(r"1Z[A-Z0-9]{6}[0-9]{2}[0-9]{7}[0-9]")

def get_service(tracking_number: str) -> str:
    return "UPS" if re.match(UPS_PACKAGE_REGEX, tracking_number) else "USPS"

def track_package(tracking_number: str) -> Package:
    return (UPSTracking if get_service(tracking_number) == "UPS" else USPSTracking).track_package(tracking_number)
