# Copyright (c) 2024 iiPython

# Modules
import os
import re
from datetime import datetime
from dataclasses import dataclass

from requests import Session

# Typing
@dataclass
class Step:
    details:    str
    location:   str
    time:       datetime | None

@dataclass
class Package:
    expected:       list[datetime] | None
    last_status:    str | None
    state:          str
    steps:          list[Step]
    service:        str | None

# Global exceptions
class StatusNotAvailable(Exception):
    pass

# Stop stats tracking by Selenium
# Could also just manually specify geckodriver path but eh
os.environ["SE_AVOID_STATS"] = "true"

# Constants
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.3"

SESSION = Session()
SESSION.headers.update({
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-US,en;q=0.5",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Sec-GPC": "1",
    "User-Agent": USER_AGENT,
})

# Handle actual tracking
from .ups import UPSTracking    # noqa: E402
from .usps import USPSTracking  # noqa: E402

UPS_PACKAGE_REGEX = re.compile(r"^1Z[A-Z0-9]{6}[0-9]{10}$")

def get_service(tracking_number: str) -> str:
    if re.match(UPS_PACKAGE_REGEX, tracking_number):
        return "UPS"

    return "USPS"

def track_package(tracking_number: str) -> Package:
    return {"UPS": UPSTracking, "USPS": USPSTracking}[get_service(tracking_number)].track_package(tracking_number)
