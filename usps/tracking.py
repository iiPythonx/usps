# Copyright (c) 2024 iiPython

# Modules
import atexit
from datetime import datetime
from dataclasses import dataclass

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.firefox.options import Options

# Exceptions
class NonExistantPackage(Exception):
    pass

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

# Mappings
USPS_STEP_DETAIL_MAPPING = {
    "usps picked up item": "Picked Up",
    "usps awaiting item": "Awaiting Item",
    "arrived at usps regional origin facility": "At Facility"
}

# Main class
class USPSTracking():
    def __init__(self) -> None:
        options = Options()
        options.add_argument("--headless")

        self.instance = webdriver.Firefox(options)
        atexit.register(self.instance.quit)

    def __map_step_details(self, details: str) -> str:
        details = details.split(", ")[-1].lower()
        return " ".join([
            word.capitalize() for word in USPS_STEP_DETAIL_MAPPING.get(details, details).split(" ")
        ])
    
    def __sanitize(self, text: str) -> str:
        lines = text.split("\n")
        return " ".join(lines[:(2 if "\t" in lines[0] else 1)]).replace("\t", "").strip()

    def track_package(self, tracking_number: str) -> Package:
        self.instance.get(f"https://tools.usps.com/go/TrackConfirmAction?qtc_tLabels1={tracking_number}")
        WebDriverWait(self.instance, 5).until(expected_conditions.presence_of_element_located((By.CLASS_NAME, "tracking-number")))

        # Check header for possible issues
        if self.instance.find_elements(By.CLASS_NAME, "red-banner"):
            raise NonExistantPackage

        # Start fetching data
        has_delivery_date = self.instance.find_elements(By.CLASS_NAME, "day")
        month, year = "", ""
        if has_delivery_date:
            month, year = self.instance.find_element(By.CLASS_NAME, "month_year").text.split("\n")

        # Handle fetching the current step
        external_shipment = self.instance.find_elements(By.CLASS_NAME, "preshipment-status")
        if not external_shipment:

            # Catch services like Amazon, where the status is still not in the element
            # like it is with normal in-network packages.
            external_shipment = self.instance.find_elements(By.CLASS_NAME, "shipping-partner-status")

        # If this is an external shipment, check OUTSIDE the element to find the status.
        if external_shipment:
            current_step = external_shipment[0].find_element(By.CLASS_NAME, "tb-status").text

        else:
            current_step = self.instance.find_element(By.CLASS_NAME, "current-step").find_element(By.CLASS_NAME, "tb-status").text

        # Click "See All Tracking History"
        if self.instance.find_elements(By.CSS_SELECTOR, ".tb-step.collapsed"):
            WebDriverWait(self.instance, 5).until(expected_conditions.presence_of_element_located((By.CLASS_NAME, "expand-collapse-history")))

        see_all_button = self.instance.find_elements(By.CLASS_NAME, "expand-collapse-history")
        if see_all_button:
            see_all_button[0].click()

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
                    self.__map_step_details(step.find_element(By.CLASS_NAME, "tb-status-detail").get_attribute("innerText")),  # type: ignore
                    step.find_element(By.CLASS_NAME, "tb-location").get_attribute("innerText").strip(),  # type: ignore
                    datetime.strptime(
                        self.__sanitize(step.find_element(By.CLASS_NAME, "tb-date").get_attribute("innerText")),  # type: ignore
                        "%B %d, %Y, %I:%M %p"
                    )
                )
                for step in self.instance.find_elements(By.CLASS_NAME, "tb-step")
                if "toggle-history-container" not in step.get_attribute("class")  # type: ignore
            ]
        )

tracking = USPSTracking()
