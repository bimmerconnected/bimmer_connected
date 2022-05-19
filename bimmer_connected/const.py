"""URLs for different services and error code mapping."""
from enum import Enum


class CarBrands(str, Enum):
    """Car brands supported by the MyBMW API."""

    @classmethod
    def _missing_(cls, value):
        for member in cls:
            if member.value == value.lower():
                return member
        raise ValueError(f"'{value}' is not a valid {cls.__name__}")

    BMW = "bmw"
    MINI = "mini"


class Regions(Enum):
    """Regions of the world with separate servers."""

    NORTH_AMERICA = 0
    CHINA = 1
    REST_OF_WORLD = 2


SERVER_URLS_MYBMW = {
    Regions.NORTH_AMERICA: "cocoapi.bmwgroup.us",
    Regions.REST_OF_WORLD: "cocoapi.bmwgroup.com",
    Regions.CHINA: "myprofile.bmw.com.cn",
}

OCP_APIM_KEYS = {
    Regions.NORTH_AMERICA: "MzFlMTAyZjUtNmY3ZS03ZWYzLTkwNDQtZGRjZTYzODkxMzYy",
    Regions.REST_OF_WORLD: "NGYxYzg1YTMtNzU4Zi1hMzdkLWJiYjYtZjg3MDQ0OTRhY2Zh",
}

AES_KEYS = {
    Regions.CHINA: {
        "key": "UzJUdzEwdlExWGYySmxLYQ==",
        "iv": "dTFGUDd4ZWRrQWhMR3ozVQ==",
    }
}

HTTPX_TIMEOUT = 30.0

USER_AGENT = "Dart/2.13 (dart:io)"
X_USER_AGENT = "android(v1.07_20200330);{};2.3.0(13603)"


AUTH_CHINA_PUBLIC_KEY_URL = "/eadrax-coas/v1/cop/publickey"
AUTH_CHINA_LOGIN_URL = "/eadrax-coas/v2/login/pwd"
AUTH_CHINA_TOKEN_URL = "/eadrax-coas/v1/oauth/token"

OAUTH_CONFIG_URL = "/eadrax-ucs/v1/presentation/oauth/config"

VEHICLES_URL = "/eadrax-vcs/v1/vehicles"

REMOTE_SERVICE_BASE_URL = "/eadrax-vrccs/v2/presentation/remote-commands"
REMOTE_SERVICE_URL = REMOTE_SERVICE_BASE_URL + "/{vin}/{service_type}"
REMOTE_SERVICE_STATUS_URL = REMOTE_SERVICE_BASE_URL + "/eventStatus?eventId={event_id}"
REMOTE_SERVICE_POSITION_URL = REMOTE_SERVICE_BASE_URL + "/eventPosition?eventId={event_id}"

VEHICLE_IMAGE_URL = "/eadrax-ics/v3/presentation/vehicles/{vin}/images?carView={view}"
VEHICLE_POI_URL = "/eadrax-dcs/v1/send-to-car/send-to-car"

VEHICLE_CHARGING_STATISTICS_URL = "/eadrax-chs/v1/charging-statistics"
VEHICLE_CHARGING_SESSIONS_URL = "/eadrax-chs/v1/charging-sessions"

SERVICE_PROPERTIES = "properties"
SERVICE_STATUS = "status"
SERVICE_CHARGING_STATISTICS_URL = "CHARGING_STATISTICS"
SERVICE_CHARGING_SESSIONS_URL = "CHARGING_SESSIONS"
SERVICE_CHARGING_PROFILE = "CHARGING_PROFILE"
