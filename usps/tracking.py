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
    expected: list[datetime] | None
    last_status: str
    state: str
    steps: list[Step]

# Mappings
USPS_STEP_DETAIL_MAPPING = {
    "usps picked up item": "Picked Up",
    "usps awaiting item": "Awaiting Item",
    "arrived at usps regional origin facility": "At Facility",
    "arrived at usps regional facility": "At Facility",
    "departed usps regional facility": "Left Facility",
    "departed post office": "Left Office",
    "usps in possession of item": "Possessed",
    "arrived at post office": "At Office",
    "out for delivery": "Delivering",
    "in transit to next facility": "In Transit",
    "arriving on time": "Package On Time",
    "accepted at usps origin facility": "Accepted"
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
        if "between" in details.lower():
            return "Delivering"

        details = details.split(", ")[-1].lower()
        return USPS_STEP_DETAIL_MAPPING.get(details, " ".join([
            word.capitalize() for word in details.split(" ")
        ]))
    
    def __sanitize(self, text: str) -> str:
        lines = text.split("\n")
        return " ".join(lines[:(2 if "\t" in lines[0] else 1)]).replace("\t", "").strip()

    def __generate_security(self, url: str) -> str:
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

            html = instance.page_source  # This saves us a request
            instance.quit()
            return html

    def track_package(self, tracking_number: str) -> Package:
        url = f"https://tools.usps.com/go/TrackConfirmAction?qtc_tLabels1={tracking_number}"

        # Load data from page
        if not self.cookies:

            # Handle generating cookies / headers
            page = BeautifulSoup(self.__generate_security(url), "html.parser")

        else:
            page = BeautifulSoup(
                self.session.get(url, cookies = self.cookies, headers = self.headers).text,
                "html.parser"
            )
            if "originalHeaders" in str(page):
                page = BeautifulSoup(self.__generate_security(url), "html.parser")

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

        # Figure out delivery times
        if has_delivery_date:
            times = page.find(attrs = {"class": "time"}).find(text = True, recursive = False).split(" and ")

        # Fetch steps
        steps = []
        for step in page.find_all(attrs = {"class": "tb-step"}):
            if "toggle-history-container" not in step["class"]:
                location = step.find(attrs = {"class": "tb-location"})
                if location is not None:
                    location = location.text.strip()

                steps.append(Step(
                    self.__map_step_details(step.find(attrs = {"class": "tb-status-detail"}).text),
                    location or "UNKNOWN LOCATION",
                    datetime.strptime(
                        self.__sanitize(step.find(attrs = {"class": "tb-date"}).text),
                        "%B %d, %Y, %I:%M %p"
                    )
                ))

        # Bundle together
        return Package(

            # Estimated delivery
            [
                datetime.strptime(f"{page.find(attrs = {'class': 'date'}).text.zfill(2)} {month} {year} {time}", "%d %B %Y %I:%M%p")
                for time in times
            ] if has_delivery_date else None,

            # Last status "banner"
            page.find(attrs = {"class": "banner-content"}).text.strip(),

            # Current state based on current step
            current_step,

            # Step data
            steps
        )

tracking = USPSTracking()
