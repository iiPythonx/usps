# Copyright (c) 2024 iiPython

# Modules
import os
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
    last_status: str | None
    state: str
    steps: list[Step]
    service: str | None

# Global exceptions
class StatusNotAvailable(Exception):
    pass

# Stop stats tracking by Selenium
# Could also just manually specify geckodriver path but eh
os.environ["SE_AVOID_STATS"] = "true"

# Constants
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.3"

# Handle actual tracking
from .ups import UPSTracking  # noqa: E402
from .usps import USPSTracking  # noqa: E402

UPS_PACKAGE_REGEX = re.compile(r"1Z[A-Z0-9]{6}[0-9]{10}")

def get_service(tracking_number: str) -> str:
    return "UPS" if re.match(UPS_PACKAGE_REGEX, tracking_number) else "USPS"

def track_package(tracking_number: str) -> Package:
    return (UPSTracking if get_service(tracking_number) == "UPS" else USPSTracking).track_package(tracking_number)
