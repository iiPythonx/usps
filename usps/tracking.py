# Copyright (c) 2024 iiPython

# Modules
from datetime import datetime
from dataclasses import dataclass

from requests import Session
from bs4 import BeautifulSoup, Tag
from rich.status import Status

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.firefox.options import Options

from usps.storage import security

# Exceptions
class NonExistentPackage(Exception):
    pass

class MissingElement(Exception):
    pass

class InvalidElementType(Exception):
    pass

class NoTextInElement(Exception):
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

# Constants
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0"
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
    "accepted at usps origin facility": "Accepted",
    "arrived at usps facility": "At Facility",
    "departed usps facility": "Left Facility"
}

# BS4 wrappers
def get_text(element: Tag | None = None, alt: bool = False) -> str:
    if element is None:
        raise MissingElement

    if alt is True:
        text = element.find(text = True, recursive = False)
        if text is None:
            raise NoTextInElement

        return str(text)

    return element.text

# Main class
class USPSTracking:
    def __init__(self) -> None:
        self.session = Session()
        self.cookies = security.load() or {}

    @staticmethod
    def __map_step_details(details: str) -> str:
        if "expected delivery" in details.lower():
            return "Delivering"

        details = details.split(", ")[-1].lower()
        return USPS_STEP_DETAIL_MAPPING.get(details, " ".join([
            word.capitalize() for word in details.split(" ")
        ]))

    @staticmethod
    def __sanitize(text: str) -> str:
        lines = text.split("\n")
        return " ".join(lines[:(2 if "\t" in lines[0] else 1)]).replace("\t", "").strip()

    def __generate_security(self, url: str) -> str:
        with Status("[cyan]Generating cookies...", spinner = "arc"):
            options = Options()
            options.add_argument("--headless")
            instance = webdriver.Firefox(options = options)
            instance.get(url)

            # Wait until we can confirm the JS has loaded the new page
            WebDriverWait(instance, 5).until(
                expected_conditions.presence_of_element_located((By.CLASS_NAME, "tracking-number"))
            )

            self.cookies = {c["name"]: c["value"] for c in instance.get_cookies()}
            security.save(self.cookies)

            # Return page source (saves us a request)
            html = instance.page_source
            instance.quit()
            return html

    def track_package(self, tracking_number: str) -> Package:
        url = f"https://tools.usps.com/go/TrackConfirmAction?qtc_tLabels1={tracking_number}"

        # Load data from page
        if not self.cookies:

            # Handle generating cookies
            page = BeautifulSoup(self.__generate_security(url), "html.parser")

        else:
            page = BeautifulSoup(
                self.session.get(url, cookies = self.cookies, headers = {"User-Agent": USER_AGENT}).text,
                "html.parser"
            )
            if "originalHeaders" in str(page):
                page = BeautifulSoup(self.__generate_security(url), "html.parser")

        # Handle element searching
        def find_object(class_name: str, parent: Tag | None = None) -> Tag | None:
            element = (parent or page).find(attrs = {"class": class_name})
            if element is None:
                return element

            if not isinstance(element, Tag):
                raise InvalidElementType(class_name)

            return element

        # Check header for possible issues
        if find_object("red-banner"):
            raise NonExistentPackage

        # Start fetching data
        has_delivery_date = find_object("day")
        month, year = "", ""
        if has_delivery_date:
            month, year = get_text(find_object("month_year")).split("\n")[0].strip().split(" ")

        # Handle fetching the current step
        if find_object("preshipment-status") or find_object("shipping-partner-status"):
            current_step = get_text(find_object("tb-status"))

        else:
            current_step = get_text(find_object("tb-status", find_object("current-step")))

        # Figure out delivery times
        times = get_text(find_object("time"), alt = True).split(" and ") if has_delivery_date else []

        # Fetch steps
        steps = []
        for step in page.find_all(attrs = {"class": "tb-step"}):
            if "toggle-history-container" not in step["class"]:
                location = find_object("tb-location", step)
                if location is not None:
                    location = get_text(location).strip()

                steps.append(Step(
                    self.__map_step_details(get_text(find_object("tb-status-detail", step))),
                    location or "UNKNOWN LOCATION",
                    datetime.strptime(
                        self.__sanitize(get_text(find_object("tb-date", step))),
                        "%B %d, %Y, %I:%M %p"
                    )
                ))

        # Bundle together
        return Package(

            # Estimated delivery
            [
                datetime.strptime(
                    f"{get_text(find_object('date')).zfill(2)} {month} {year} {time.strip()}",
                    "%d %B %Y %I:%M%p"
                )
                for time in times
            ] if has_delivery_date else None,

            # Last status "banner"
            get_text(find_object("banner-content")).strip(),

            # Current state based on current step
            current_step,

            # Step data
            steps
        )

tracking = USPSTracking()
