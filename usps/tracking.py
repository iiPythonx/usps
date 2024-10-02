# Copyright (c) 2024 iiPython

# Modules
import atexit
from datetime import datetime
from dataclasses import dataclass

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

# Typing
@dataclass
class Step:
    Details: str
    Location: str
    Time: datetime

@dataclass
class Package:
    ExpectedDelivery: datetime | None
    LastStatus: str
    State: str
    Steps: list[Step]

# Main class
class USPSTracking():
    def __init__(self) -> None:
        self.instance = webdriver.Firefox()
        atexit.register(self.instance.quit)

    def track_package(self, tracking_number: str) -> Package:
        self.instance.get(f"https://tools.usps.com/go/TrackConfirmAction?qtc_tLabels1={tracking_number}")
        WebDriverWait(self.instance, 5).until(expected_conditions.presence_of_element_located((By.CLASS_NAME, "tracking-number")))

        # Start fetching data
        has_delivery_date = self.instance.find_elements(By.CLASS_NAME, "day")
        month, year = "", ""
        if has_delivery_date:
            month, year = self.instance.find_element(By.CLASS_NAME, "month_year").text.split("\n")

        # Handle fetching the current step
        preshipment = self.instance.find_elements(By.CLASS_NAME, "preshipment-status")
        if preshipment:
            current_step = preshipment[0].find_element(By.CLASS_NAME, "tb-status").text

        else:
            current_step = self.instance.find_element(By.CLASS_NAME, "current-step").find_element(By.CLASS_NAME, "tb-status").text

        # Bundle together
        return Package(

            # Estimated delivery
            datetime.strptime(" ".join([
                self.instance.find_element(By.CLASS_NAME, "date").text.zfill(2),
                month,
                year,
                self.instance.find_element(By.CLASS_NAME, "time").text
            ]), "%d %B %Y %I:%M%p") if has_delivery_date else None,

            # Last status "banner"
            self.instance.find_element(By.CLASS_NAME, "banner-content").text,

            # Current state based on current step
            current_step,

            # Fetch ALL steps
            [
                Step(
                    step.find_element(By.CLASS_NAME, "tb-status-detail").text,
                    step.find_element(By.CLASS_NAME, "tb-location").text.strip(),
                    datetime.strptime(step.find_element(By.CLASS_NAME, "tb-date").text, "%B %d, %Y, %I:%M %p")
                )
                for step in self.instance.find_elements(By.CLASS_NAME, "tb-step")
            ]
        )

tracking = USPSTracking()
