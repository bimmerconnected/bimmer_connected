"""URLs for different services and error code mapping."""
from enum import Enum


class CarBrands(str, Enum):
    """Car brands supported by the MyBMW API."""

    @classmethod
    def _missing_(cls, value):
        value = next(iter(value.split("_")))
        for member in cls:
            if member.value == value.lower():
                return member
        raise ValueError(f"'{value}' is not a valid {cls.__name__}")

    BMW = "bmw"
    MINI = "mini"


class Regions(str, Enum):
    """Regions of the world with separate servers."""

    NORTH_AMERICA = "na"
    CHINA = "cn"
    REST_OF_WORLD = "row"


SERVER_URLS_MYBMW = {
    Regions.NORTH_AMERICA: "cocoapi.bmwgroup.us",
    Regions.REST_OF_WORLD: "cocoapi.bmwgroup.com",
    Regions.CHINA: "myprofile.bmw.com.cn",
}

OCP_APIM_KEYS = {
    Regions.NORTH_AMERICA: "MzFlMTAyZjUtNmY3ZS03ZWYzLTkwNDQtZGRjZTYzODkxMzYy",
    Regions.REST_OF_WORLD: "NGYxYzg1YTMtNzU4Zi1hMzdkLWJiYjYtZjg3MDQ0OTRhY2Zh",
}

APP_VERSIONS = {
    Regions.NORTH_AMERICA: "3.9.0(27760)",
    Regions.REST_OF_WORLD: "3.9.0(27760)",
    Regions.CHINA: "3.6.1(23634)",
}

HTTPX_TIMEOUT = 30.0

USER_AGENTS = {
    Regions.NORTH_AMERICA: "Dart/2.19 (dart:io)",
    Regions.REST_OF_WORLD: "Dart/2.19 (dart:io)",
    Regions.CHINA: "Dart/2.18 (dart:io)",
}
X_USER_AGENT = "android(TQ2A.230405.003.B2);{brand};{app_version};{region}"


AUTH_CHINA_PUBLIC_KEY_URL = "/eadrax-coas/v1/cop/publickey"
AUTH_CHINA_LOGIN_URL = "/eadrax-coas/v2/login/pwd"
AUTH_CHINA_TOKEN_URL = "/eadrax-coas/v2/oauth/token"
AUTH_CHINA_CAPTCHA_URL = "/eadrax-coas/v2/cop/slider-captcha"
AUTH_CHINA_CAPTCHA_CHECK_URL = "/eadrax-coas/v1/cop/check-captcha"

OAUTH_CONFIG_URL = "/eadrax-ucs/v1/presentation/oauth/config"

VEHICLES_URL = "/eadrax-vcs/v4/vehicles"
VEHICLE_STATE_URL = VEHICLES_URL + "/state"

REMOTE_SERVICE_BASE_URL = "/eadrax-vrccs/v3/presentation/remote-commands"
REMOTE_SERVICE_URL = REMOTE_SERVICE_BASE_URL + "/{vin}/{service_type}"
REMOTE_SERVICE_STATUS_URL = REMOTE_SERVICE_BASE_URL + "/eventStatus?eventId={event_id}"
REMOTE_SERVICE_POSITION_URL = REMOTE_SERVICE_BASE_URL + "/eventPosition?eventId={event_id}"

VEHICLE_CHARGING_DETAILS_URL = "/eadrax-crccs/v2/vehicles"
VEHICLE_CHARGING_BASE_URL = "/eadrax-crccs/v1/vehicles/{vin}"
VEHICLE_CHARGING_SETTINGS_SET_URL = VEHICLE_CHARGING_BASE_URL + "/charging-settings"
VEHICLE_CHARGING_PROFILE_SET_URL = VEHICLE_CHARGING_BASE_URL + "/charging-profile"
VEHICLE_CHARGING_START_STOP_URL = VEHICLE_CHARGING_BASE_URL + "/{service_type}"

VEHICLE_IMAGE_URL = "/eadrax-ics/v3/presentation/vehicles/{vin}/images?carView={view}"
VEHICLE_POI_URL = "/eadrax-dcs/v1/send-to-car/send-to-car"

VEHICLE_CHARGING_STATISTICS_URL = "/eadrax-chs/v1/charging-statistics"
VEHICLE_CHARGING_SESSIONS_URL = "/eadrax-chs/v1/charging-sessions"

SERVICE_CHARGING_STATISTICS_URL = "CHARGING_STATISTICS"
SERVICE_CHARGING_SESSIONS_URL = "CHARGING_SESSIONS"
SERVICE_CHARGING_PROFILE = "CHARGING_PROFILE"


ATTR_STATE = "state"
ATTR_CAPABILITIES = "capabilities"
ATTR_ATTRIBUTES = "attributes"
ATTR_CHARGING_SETTINGS = "charging_settings"

DEFAULT_POI_NAME = "Sent with ♥ by bimmer_connected"
