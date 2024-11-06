# Copyright (c) 2024 iiPython

# Modules
from datetime import datetime

from requests import Session
from bs4 import BeautifulSoup, Tag
from rich.status import Status

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.firefox.options import Options

from usps.storage import security
from usps.tracking import USER_AGENT, Package, Step, StatusNotAvailable

# Handle status mappings
USPS_STEP_DETAIL_MAPPING = {
    "usps picked up item": "Picked Up",
    "usps awaiting item": "Awaiting Item",
    "arrived at usps facility": "At Facility",
    "arrived at usps origin facility": "At Facility",
    "arrived at usps regional origin facility": "At Facility",
    "arrived at usps regional facility": "At Facility",
    "arrived at usps regional destination facility": "At Facility",
    "departed usps facility": "Left Facility",
    "departed usps regional facility": "Left Facility",
    "departed post office": "Left Office",
    "usps in possession of item": "Possessed",
    "arrived at post office": "At Office",
    "out for delivery": "Delivering",
    "awaiting delivery": "Delayed  ",
    "in transit to next facility": "In Transit",
    "arriving on time": "Package On Time",
    "accepted at usps origin facility": "Accepted",
    "accepted at usps destination facility": "Accepted",
    "package acceptance pending": "Arrived",
    "garage / other door / other location at address": "Delivered",
    "left with individual": "Delivered",
    "redelivery scheduled for next business day": "Rescheduled",
    "available for pickup": "Available", 
    "reminder to schedule redelivery of your item": "Reminder"
}

# Exceptions
class MissingElement(Exception):
    pass

class InvalidElementType(Exception):
    pass

class NoTextInElement(Exception):
    pass

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
    _session: Session | None = None
    _cookies: dict = {}

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

    @staticmethod
    def __newline_grab(text: str, index: int) -> str:
        return [item.strip() for item in text.split("\n") if item.strip()][index - 1]

    @classmethod
    def __generate_security(cls, url: str) -> str:
        with Status("[cyan]Generating cookies...", spinner = "arc"):
            options = Options()
            options.add_argument("--headless")

            # Setup profile with user agent
            profile = webdriver.FirefoxProfile()
            profile.set_preference("general.useragent.override", USER_AGENT)
    
            # Handle instance creation
            options.profile = profile
            instance = webdriver.Firefox(options = options)
            instance.get(url)

            # Wait until we can confirm the JS has loaded the new page
            WebDriverWait(instance, 5).until(
                expected_conditions.presence_of_element_located((By.CLASS_NAME, "tracking-number"))
            )

            cls._cookies = {c["name"]: c["value"] for c in instance.get_cookies()}
            security.save(cls._cookies)

            # Return page source (saves us a request)
            html = instance.page_source
            instance.quit()
            return html

    @classmethod
    def track_package(cls, tracking_number: str) -> Package:
        if cls._session is None:
            cls._session = Session()
            cls._cookies = security.load()

        url = f"https://tools.usps.com/go/TrackConfirmAction?qtc_tLabels1={tracking_number}"

        # Load data from page
        if not cls._cookies:

            # Handle generating cookies
            page = BeautifulSoup(cls.__generate_security(url), "html.parser")

        else:
            page = BeautifulSoup(
                cls._session.get(url, cookies = cls._cookies, headers = {"User-Agent": USER_AGENT}).text,
                "html.parser"
            )
            if "originalHeaders" in str(page):
                page = BeautifulSoup(cls.__generate_security(url), "html.parser")

        # Handle element searching
        def find_object(class_name: str, parent: Tag | None = None) -> Tag | None:
            element = (parent or page).find(attrs = {"class": class_name})
            if element is None:
                return element

            if not isinstance(element, Tag):
                raise InvalidElementType(class_name)

            return element

        # Start fetching data
        has_delivery_date = find_object("day")
        month, year = "", ""
        if has_delivery_date:
            month, year = get_text(find_object("month_year")).split("\n")[0].strip().split(" ")

        # Handle fetching the current step
        try:
            if any(find_object(x) for x in ["preshipment-status", "shipping-partner-status", "delivery-attempt-status", "addressee-unknown-status"]):
                current_step = get_text(find_object("tb-status"))

            else:
                current_step = get_text(find_object("tb-status", find_object("current-step")))

        except MissingElement:

            # If the steps aren't listed, assume there's an error message
            raise StatusNotAvailable(get_text(find_object("banner-header", find_object("red-banner"))).strip())

        # Figure out delivery times
        times = get_text(find_object("time"), alt = True).split(" and ") if has_delivery_date else []

        # Fetch steps
        steps = []
        for step in page.find_all(attrs = {"class": "tb-step"}):
            if "toggle-history-container" not in step["class"]:
                location = find_object("tb-location", step)
                if location is not None:
                    location, location_data = "", [line.strip() for line in get_text(location).strip().split("\n") if line.strip()]
                    if len(location_data) > 1:
                        location = f"{location_data[1]} {location_data[2]} {location_data[3]}"

                    elif location_data:
                        location = location_data[0]

                step_detail = get_text(find_object("tb-status-detail", step))
                match step_detail.lower():
                    case "reminder to schedule redelivery of your item":
                        location = "SCHEDULE REDELIVERY"

                date_time = cls.__sanitize(get_text(find_object("tb-date", step)))
                steps.append(Step(
                    cls.__map_step_details(step_detail),
                    location or "",
                    datetime.strptime(
                        date_time,
                        "%B %d, %Y, %I:%M %p" if ":" in date_time else "%B %d, %Y"
                    )
                ))

        # Fetch postal product
        product_info = find_object("product_info")
        postal_product = cls.__newline_grab(get_text(product_info), 2) if product_info is not None else None
        if postal_product and ":" in postal_product:
            postal_product = None

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
            steps,

            # "Postal Product"
            postal_product
        )
