# Copyright (c) 2024 iiPython

# Modules
from datetime import datetime, timedelta

from requests import Session

from usps.utils import LOCAL_TIMEZONE
from . import USER_AGENT, Package, Step
from .exceptions import StatusNotAvailable

# Handle mapping
UPS_CMS_MAPPINGS = {
    "cms.stapp.jan": "January",
    "cms.stapp.feb": "February",
    "cms.stapp.mar": "March",
    "cms.stapp.apr": "April",
    "cms.stapp.may": "May",
    "cms.stapp.jun": "June",
    "cms.stapp.jul": "July",
    "cms.stapp.aug": "August",
    "cms.stapp.sep": "September",
    "cms.stapp.oct": "October",
    "cms.stapp.nov": "November",
    "cms.stapp.dec": "December"
}

# Main class
class UPSTracking:
    _session: Session | None = None

    @staticmethod
    def __map_milestone_name(milestone: str) -> str:
        match milestone.lower():
            case "we have your package":
                return "Has Package"

            case _:
                return milestone

    @classmethod
    def track_package(cls, tracking_number: str) -> Package:
        if cls._session is None:
            cls._session = Session()

        if not cls._session.cookies:
            cls._session.get("https://www.ups.com/track", headers = {"User-Agent": USER_AGENT})

        response = cls._session.post(
            "https://webapis.ups.com/track/api/Track/GetStatus?loc=en_US",
            json = {"Locale": "en_US", "TrackingNumber": [tracking_number]},
            headers = {
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Accept-Language": "en-US,en;q=0.5",
                "User-Agent": USER_AGENT,
                "X-XSRF-TOKEN": cls._session.cookies["X-XSRF-TOKEN-ST"]
            }
        ).json()
        if response["statusCode"] != "200":
            raise StatusNotAvailable(response["statusText"])

        data = response["trackDetails"][0]

        # Handle estimated delivery date
        estimated_delivery = None
        if data["packageStatusTime"]:
            delivery = data["scheduledDeliveryDateDetail"]
            month, year = UPS_CMS_MAPPINGS[delivery["monthCMSKey"]], datetime.now().year
            estimated_delivery = [
                datetime.strptime(f"{month} {delivery['dayNum']} {time.replace('.', '')}", "%B %d %I:%M %p").replace(year = year)
                for time in data["packageStatusTime"].split(" - ")
            ]

        # Make up some status names
        latest_scan = data["shipmentProgressActivities"][0]
        status_name = latest_scan["activityScan"]
        match data["packageStatusCode"]:
            case "160":
                status_name = f"Your package has arrived in {latest_scan['location']} and is getting ready for shipping."

        # Bundle together
        return Package(
            estimated_delivery,
            status_name,
            [x for x in data["milestones"] if x["isCurrent"]][-1]["name"],
            [
                Step(
                    cls.__map_milestone_name(step["milestoneName"]["name"]),
                    step["location"].replace("United States", "US").upper() if "," in step["location"] else "",
                    datetime.strptime(f"{step['gmtDate']} {step['gmtTime']}", "%Y%m%d %H:%M:%S").replace(tzinfo = LOCAL_TIMEZONE) +\
                         timedelta(hours = int(step["gmtOffset"].split(":")[0]))
                )
                for step in data["shipmentProgressActivities"]
            ]
        )
