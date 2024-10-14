# Copyright (c) 2024 iiPython

# Modules
from datetime import datetime, timedelta

from requests import Session

from usps.timezones import LOCAL_TIMEZONE
from usps.tracking import USER_AGENT, Package, Step, StatusNotAvailable

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
UPS_MILESTONE_MAPPINGS = {
    "we have your package": "Has Package",
    "departed from facility": "Left Facility",
    "arrived at facility": "At Facility",
    "processing at ups facility": "Processing",
    "out for delivery": "Delivering"
}

# Headers that need to exist for UPS to respond
# I'm not sure why they check *these* headers, but ¯\_(ツ)_/¯
UPS_HEADERS = {
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-US,en;q=0.5",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Sec-GPC": "1",
    "User-Agent": USER_AGENT,
}

# Main class
class UPSTracking:
    _session: Session | None = None
    _failcount: int = 0

    @staticmethod
    def __map_milestone_name(milestone: str) -> str:
        return UPS_MILESTONE_MAPPINGS.get(milestone.lower(), milestone)

    @classmethod
    def track_package(cls, tracking_number: str) -> Package:
        if cls._session is None:
            cls._session = Session()

        try:
            if not cls._session.cookies:
                cls._session.get("https://www.ups.com/track", headers = UPS_HEADERS, timeout = 1)

            response = cls._session.post(
                "https://webapis.ups.com/track/api/Track/GetStatus?loc=en_US",
                json = {"Locale": "en_US", "TrackingNumber": [tracking_number]},
                headers = UPS_HEADERS | {
                    "X-XSRF-TOKEN": cls._session.cookies["X-XSRF-TOKEN-ST"]
                },
                timeout = 1
            ).json()
        
        except Exception:  # Too many types for me to care about right now
            if cls._failcount == 4:
                raise StatusNotAvailable("API request failed")

            cls._failcount += 1
            cls._session = Session()
            return cls.track_package(tracking_number)

        if response["statusCode"] != "200":
            raise StatusNotAvailable(response["statusText"])

        data = response["trackDetails"][0]

        # Handle estimated delivery date
        estimated_delivery = None
        if data["scheduledDeliveryDateDetail"]:
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
            case "010":
                status_name = "Your package is in transit to the destination."

            case "011":
                status_name = None

            case "021":
                status_name = "Your package is out for delivery."

            case "072":
                status_name = "Your package was loaded onto a delivery vehicle and is on the way to the destination."

            case "160":
                status_name = f"Your package has arrived in {latest_scan['location']} and is getting ready for shipping."

        # Bundle together
        return Package(
            estimated_delivery,
            status_name,
            [x for x in data["milestones"] if x["isCurrent"]][-1]["name"],
            [
                Step(
                    cls.__map_milestone_name((step["milestoneName"] or {"name": step["activityScan"]})["name"]),
                    step["location"].replace("United States", "US").upper() if "," in step["location"] else "",
                    datetime.strptime(f"{step['gmtDate']} {step['gmtTime']}", "%Y%m%d %H:%M:%S").replace(tzinfo = LOCAL_TIMEZONE) +\
                         timedelta(hours = int(step["gmtOffset"].split(":")[0]))
                )
                for step in data["shipmentProgressActivities"]
            ],
            data["additionalInformation"]["serviceInformation"]["serviceName"]
        )
