# Copyright (c) 2024 iiPython

# Modules
from datetime import datetime

from rich.status import Status
from selectolax.lexbor import LexborHTMLParser

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.firefox.options import Options

from usps.storage import security
from usps.tracking import (
    SESSION, USER_AGENT,
    Package, Step, StatusNotAvailable
)

# Handle status mappings
USPS_STEP_DETAIL_MAPPING = {
    "usps picked up item":                              "Picked Up",
    "usps awaiting item":                               "Awaiting Item",
    "arrived at usps facility":                         "At Facility",
    "arrived at usps origin facility":                  "At Facility",
    "arrived at usps regional origin facility":         "At Facility",
    "arrived at usps regional facility":                "At Facility",
    "arrived at usps regional destination facility":    "At Facility",
    "departed usps facility":                           "Left Facility",
    "departed usps regional facility":                  "Left Facility",
    "departed post office":                             "Left Office",
    "usps in possession of item":                       "Possessed",
    "arrived at post office":                           "At Office",
    "out for delivery":                                 "Delivering",
    "awaiting delivery":                                "Delayed  ",        # Yes, the spacing is intentional
    "in transit to next facility":                      "In Transit",
    "arriving on time":                                 "Package On Time",
    "accepted at usps origin facility":                 "Accepted",
    "accepted at usps destination facility":            "Accepted",
    "package acceptance pending":                       "Arrived",
    "garage / other door / other location at address":  "Delivered",
    "left with individual":                             "Delivered",
    "redelivery scheduled for next business day":       "Rescheduled",
    "available for pickup":                             "Available", 
    "reminder to schedule redelivery of your item":     "Reminder",
    "arriving late":                                    "Arriving Late"
}

# Main class
class USPSTracking:
    _cookies: dict = {}

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
        if not cls._cookies:
            cls._cookies = security.load()

        url = f"https://tools.usps.com/go/TrackConfirmAction?qtc_tLabels1={tracking_number}"

        # Load data from page
        if not cls._cookies:
            tree = LexborHTMLParser(cls.__generate_security(url))

        else:
            response = SESSION.get(url, cookies = cls._cookies).text
            tree = LexborHTMLParser(response if "originalHeaders" not in response else cls.__generate_security(url))

        if not tree.any_css_matches((  # pyright: ignore
            ".preshipment-status", ".shipping-partner-status", ".delivery-attempt-status", ".addressee-unknown-status", ".current-step"
        )):
            raise StatusNotAvailable(tree.css_first(".red-banner > .banner-header").text())

        # Start fetching data
        has_estimated_date = tree.css_matches(".date")
        month, year = tree.css_first(".month_year").text().split("\n")[0].strip().split(" ") if has_estimated_date else ["", ""]

        # Figure out delivery times
        times = tree.css_first(".time").text(deep = False, strip = True).split(" and ") if has_estimated_date else []

        # Fetch steps
        steps = []
        for step in tree.css(".tb-step:not(.toggle-history-container)"):
            time = " ".join(line.strip() for line in step.css_first(".tb-date").text().split("\n")[:2] if line.strip())

            location = None
            if step.css_matches(".tb-location"):
                location = step.css_first(".tb-location").text(strip = True)

            details = step.css_first(".tb-status-detail").text()
            if details.lower() == "reminder to schedule redelivery of your item":
                location = "SCHEDULE REDELIVERY"

            steps.append(Step(
                USPS_STEP_DETAIL_MAPPING.get(details.split(", ")[-1].lower(), "Unknown")
                        if "expected delivery" not in details.lower() else "Delivering",
                location or "",
                datetime.strptime(
                    time,
                    "%B %d, %Y, %I:%M %p" if ":" in time else "%B %d, %Y"
                )
            ))

        postal_product = tree.css_first(".product_info > li:first-child")
        if postal_product is not None:
            postal_product = postal_product.text(strip = True).split(":")[1]

        return Package(
            [
                datetime.strptime(
                    f"{tree.css_first('.date').text().zfill(2)} {month} {year} {time.strip()}",
                    "%d %B %Y %I:%M%p"
                )
                for time in times
            ] if has_estimated_date else None,
            tree.css_first(".banner-content").text(strip = True),
            tree.css_first(".tb-status").text(),
            steps,
            postal_product
        )
