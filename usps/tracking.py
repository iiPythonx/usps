# type: ignore
# Copyright (c) 2024 iiPython

# Modules
from datetime import datetime
from dataclasses import dataclass

from requests import Session
from bs4 import BeautifulSoup
from rich.status import Status

from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.firefox.options import Options

from usps.storage import security

# Exceptions
class NonExistantPackage(Exception):
    pass

# Typing
@dataclass
class Step:
    details: str
    location: str
    time: datetime

@dataclass
class Package:
    expected: datetime | None
    last_status: str
    state: str
    steps: list[Step]

# Mappings
USPS_STEP_DETAIL_MAPPING = {
    "usps picked up item": "Picked Up",
    "usps awaiting item": "Awaiting Item",
    "arrived at usps regional origin facility": "At Facility",
    "departed usps regional facility": "Left Facility",
    "departed post office": "Left Office"
}

# Main class
class USPSTracking():
    def __init__(self) -> None:
        self.session = Session()
        self.headers, self.cookies = {}, {}

        # Fetch existing security data
        security_data = security.load()
        if security_data:
            self.headers, self.cookies = security_data["headers"], security_data["cookies"]

    def __map_step_details(self, details: str) -> str:
        details = details.split(", ")[-1].lower()
        return USPS_STEP_DETAIL_MAPPING.get(details, " ".join([
            word.capitalize() for word in details.split(" ")
        ]))
    
    def __sanitize(self, text: str) -> str:
        lines = text.split("\n")
        return " ".join(lines[:(2 if "\t" in lines[0] else 1)]).replace("\t", "").strip()

    def __generate_security(self, url: str) -> None:
        with Status("[cyan]Generating cookies...", spinner = "arc"):
            options = Options()
            options.add_argument("--headless")
            instance = webdriver.Firefox(options = options)
            instance.get(url)

            # Wait until we can confirm the JS has loaded the new page
            WebDriverWait(instance, 5).until(expected_conditions.presence_of_element_located((By.CLASS_NAME, "tracking-number")))
            for request in instance.requests:
                if request.url == url:
                    self.headers = request.headers
                    self.cookies = {c["name"]: c["value"] for c in instance.get_cookies()}
                    security.save({"headers": dict(self.headers), "cookies": self.cookies})
                    break

            instance.quit()

    def track_package(self, tracking_number: str) -> Package:
        url = f"https://tools.usps.com/go/TrackConfirmAction?qtc_tLabels1={tracking_number}"

        # Handle generating cookies / headers
        if not self.cookies:
            self.__generate_security(url)

        # Load data from page
        page = BeautifulSoup(
            self.session.get(url, cookies = self.cookies, headers = self.headers).text,
            "html.parser"
        )
        if "originalHeaders" in str(page):
            self.__generate_security(url)
            page = BeautifulSoup(
                self.session.get(url, cookies = self.cookies, headers = self.headers).text,
                "html.parser"
            )

        # Check header for possible issues
        if page.find(attrs = {"class": "red-banner"}):
            raise NonExistantPackage

        # Start fetching data
        has_delivery_date = page.find(attrs = {"class": "day"})
        month, year = "", ""
        if has_delivery_date:
            month, year = page.find(attrs = {"class": "month_year"}).text.split("\n")[0].strip().split(" ")

        # Handle fetching the current step
        external_shipment = page.find(attrs = {"class": "preshipment-status"})
        if not external_shipment:

            # Catch services like Amazon, where the status is still not in the element
            # like it is with normal in-network packages.
            external_shipment = page.find(attrs = {"class": "shipping-partner-status"})

        # If this is an external shipment, check OUTSIDE the element to find the status.
        if external_shipment:
            current_step = external_shipment.find(attrs = {"class": "tb-status"}).text

        else:
            current_step = page.find(attrs = {"class": "current-step"}).find(attrs = {"class": "tb-status"}).text

        # Bundle together
        return Package(

            # Estimated delivery
            datetime.strptime(" ".join([
                page.find(attrs = {"class": "date"}).text.zfill(2),
                month,
                year,
                page.find(attrs = {"class": "time"}).find(text = True, recursive = False)
            ]), "%d %B %Y %I:%M%p") if has_delivery_date else None,

            # Last status "banner"
            page.find(attrs = {"class": "banner-content"}).text.strip(),

            # Current state based on current step
            current_step,

            # Fetch ALL steps
            [
                Step(
                    self.__map_step_details(step.find(attrs = {"class": "tb-status-detail"}).text),
                    step.find(attrs = {"class": "tb-location"}).text.strip(),
                    datetime.strptime(
                        self.__sanitize(step.find(attrs = {"class": "tb-date"}).text),
                        "%B %d, %Y, %I:%M %p"
                    )
                )
                for step in page.find_all(attrs = {"class": "tb-step"})
                if "toggle-history-container" not in step["class"]
            ]
        )

tracking = USPSTracking()
