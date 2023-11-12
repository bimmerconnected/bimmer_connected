"""Fixtures for BMW tests."""

import json
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Dict, List, Optional
from unittest import mock
from uuid import uuid4

import httpx
import respx

from bimmer_connected.const import Regions
from bimmer_connected.models import ChargingSettings
from bimmer_connected.vehicle.climate import ClimateActivityState
from bimmer_connected.vehicle.fuel_and_battery import ChargingState
from bimmer_connected.vehicle.remote_services import MAP_CHARGING_MODE_TO_REMOTE_SERVICE

from . import (
    ALL_VEHICLES,
    REMOTE_SERVICE_RESPONSE_DELIVERED,
    REMOTE_SERVICE_RESPONSE_EVENTPOSITION,
    REMOTE_SERVICE_RESPONSE_EXECUTED,
    REMOTE_SERVICE_RESPONSE_INITIATED,
    REMOTE_SERVICE_RESPONSE_PENDING,
    RESPONSE_DIR,
    load_response,
)

POI_DATA = {
    "lat": 37.4028943,
    "lon": -121.9700289,
    "name": "49ers",
    "street": "4949 Marie P DeBartolo Way",
    "city": "Santa Clara",
    "postal_code": "CA 95054",
    "country": "United States",
}

CHARGING_SETTINGS = {"target_soc": 75, "ac_limit": 16}

STATUSREMOTE_SERVICE_RESPONSE_ORDER = [
    REMOTE_SERVICE_RESPONSE_PENDING,
    REMOTE_SERVICE_RESPONSE_DELIVERED,
    REMOTE_SERVICE_RESPONSE_EXECUTED,
]
STATUSREMOTE_SERVICE_RESPONSE_DICT: Dict[str, List[Path]] = defaultdict(
    lambda: deepcopy(STATUSREMOTE_SERVICE_RESPONSE_ORDER)
)

MAP_REMOTE_SERVICE_CHARGING_MODE_TO_STATE = {v: k.value for k, v in MAP_CHARGING_MODE_TO_REMOTE_SERVICE.items()}

LOCAL_STATES: Dict[str, Dict] = {}
LOCAL_CHARGING_SETTINGS: Dict[str, Dict] = {}


class MyBMWMockRouter(respx.MockRouter):
    """Stateful MockRouter for MyBMW APIs."""

    def __init__(
        self,
        vehicles_to_load: Optional[List[str]] = None,
        states: Optional[Dict[str, Dict]] = None,
        charging_settings: Optional[Dict[str, Dict]] = None,
    ) -> None:
        """Initialize the MyBMWMockRouter with clean responses."""
        super().__init__(assert_all_called=False)
        self.vehicles_to_load = vehicles_to_load or []
        self.states = deepcopy(states) if states else {}
        self.charging_settings = deepcopy(charging_settings) if charging_settings else {}

        self.add_login_routes()
        self.add_vehicle_routes()
        self.add_remote_service_routes()

    # # # # # # # # # # # # # # # # # # # # # # # #
    # Routes
    # # # # # # # # # # # # # # # # # # # # # # # #

    def add_login_routes(self) -> None:
        """Add routes for login."""

        # Login to north_america and rest_of_world
        self.get("/eadrax-ucs/v1/presentation/oauth/config").respond(
            200, json=load_response(RESPONSE_DIR / "auth" / "oauth_config.json")
        )
        self.post("/gcdm/oauth/authenticate").mock(side_effect=self.authenticate_sideeffect)
        self.post("/gcdm/oauth/token").respond(200, json=load_response(RESPONSE_DIR / "auth" / "auth_token.json"))

        # Login to china
        self.get("/eadrax-coas/v1/cop/publickey").respond(
            200, json=load_response(RESPONSE_DIR / "auth" / "auth_cn_publickey.json")
        )
        self.post("/eadrax-coas/v2/cop/slider-captcha").respond(
            200, json=load_response(RESPONSE_DIR / "auth" / "auth_slider_captcha.json")
        )

        self.post("/eadrax-coas/v1/cop/check-captcha").respond(
            200, json=load_response(RESPONSE_DIR / "auth" / "auth_slider_captcha_check.json")
        )

        self.post("/eadrax-coas/v2/login/pwd").respond(
            200, json=load_response(RESPONSE_DIR / "auth" / "auth_cn_login_pwd.json")
        )
        self.post("/eadrax-coas/v2/oauth/token").respond(
            200, json=load_response(RESPONSE_DIR / "auth" / "auth_token.json")
        )

    def add_vehicle_routes(self) -> None:
        """Add routes for vehicle requests."""

        self.get("/eadrax-vcs/v4/vehicles").mock(side_effect=self.vehicles_sideeffect)
        self.get("/eadrax-vcs/v4/vehicles/state", name="state").mock(side_effect=self.vehicle_state_sideeffect)
        self.get("/eadrax-crccs/v2/vehicles").mock(side_effect=self.vehicle_charging_settings_sideeffect)

    def add_remote_service_routes(self) -> None:
        """Add routes for remote services."""

        self.post(path__regex=r"/eadrax-vrccs/v3/presentation/remote-commands/(?P<vin>.+)/(?P<service>.+)$").mock(
            side_effect=self.service_trigger_sideeffect
        )
        self.post(path__regex=r"/eadrax-crccs/v1/vehicles/(?P<vin>.+)/(?P<service>(start|stop)-charging)$").mock(
            side_effect=self.service_trigger_sideeffect
        )
        self.post(path__regex=r"/eadrax-crccs/v1/vehicles/(?P<vin>.+)/charging-settings$").mock(
            side_effect=self.charging_settings_sideeffect
        )
        self.post(path__regex=r"/eadrax-crccs/v1/vehicles/(?P<vin>.+)/charging-profile$").mock(
            side_effect=self.charging_profile_sideeffect
        )
        self.post("/eadrax-vrccs/v3/presentation/remote-commands/eventStatus", params={"eventId": mock.ANY}).mock(
            side_effect=self.service_status_sideeffect
        )

        self.post("/eadrax-dcs/v1/send-to-car/send-to-car").mock(side_effect=self.poi_sideeffect)
        self.post("/eadrax-vrccs/v3/presentation/remote-commands/eventPosition", params={"eventId": mock.ANY}).respond(
            200,
            json=load_response(REMOTE_SERVICE_RESPONSE_EVENTPOSITION),
        )

    # # # # # # # # # # # # # # # # # # # # # # # #
    # Authentication sideeffects
    # # # # # # # # # # # # # # # # # # # # # # # #

    @staticmethod
    def authenticate_sideeffect(request: httpx.Request) -> httpx.Response:
        """Return /oauth/authentication response based on request."""
        request_text = request.read().decode("UTF-8")
        if "username" in request_text and "password" in request_text and "grant_type" in request_text:
            return httpx.Response(200, json=load_response(RESPONSE_DIR / "auth" / "authorization_response.json"))
        return httpx.Response(
            302,
            headers={
                "Location": "com.mini.connected://oauth?code=CODE&state=STATE&client_id=CLIENT_ID&nonce=login_nonce",
            },
        )

    # # # # # # # # # # # # # # # # # # # # # # # #
    # Vehicle state sideeffects
    # # # # # # # # # # # # # # # # # # # # # # # #

    def vehicles_sideeffect(self, request: httpx.Request) -> httpx.Response:
        """Return /vehicles response based on x-user-agent."""
        x_user_agent = request.headers.get("x-user-agent", "").split(";")
        if len(x_user_agent) == 4:
            brand = x_user_agent[1]
        else:
            raise ValueError("x-user-agent not configured correctly!")

        # Test if given region is valid
        _ = Regions(x_user_agent[3])

        fingerprints = ALL_VEHICLES.get(brand, [])
        if self.vehicles_to_load:
            fingerprints = [f for f in fingerprints if f["vin"] in self.vehicles_to_load]

        # Ensure order
        fingerprints = sorted(fingerprints, key=lambda v: v["vin"])

        return httpx.Response(200, json=fingerprints)

    def vehicle_state_sideeffect(self, request: httpx.Request) -> httpx.Response:
        """Return /vehicles response based on x-user-agent."""
        x_user_agent = request.headers.get("x-user-agent", "").split(";")
        assert len(x_user_agent) == 4

        try:
            return httpx.Response(200, json=self.states[request.headers["bmw-vin"]])
        except KeyError:
            return httpx.Response(404)

    def vehicle_charging_settings_sideeffect(self, request: httpx.Request) -> httpx.Response:
        """Return /vehicles response based on x-user-agent."""
        x_user_agent = request.headers.get("x-user-agent", "").split(";")
        assert len(x_user_agent) == 4
        assert "fields" in request.url.params
        assert "has_charging_settings_capabilities" in request.url.params

        try:
            return httpx.Response(200, json=self.charging_settings[request.headers["bmw-vin"]])
        except KeyError:
            return httpx.Response(404)

    # # # # # # # # # # # # # # # # # # # # # # # #
    # Remote service sideeffects
    # # # # # # # # # # # # # # # # # # # # # # # #

    def service_trigger_sideeffect(
        self, request: httpx.Request, vin: str, service: Optional[str] = None
    ) -> httpx.Response:
        """Return specific eventId for each remote function."""

        if service in ["door-lock", "door-unlock"]:
            new_state = "LOCKED" if service == "door-lock" else "UNLOCKED"
            self.states[vin]["state"]["doorsState"]["combinedSecurityState"] = new_state

        elif service in ["climate-now"]:
            new_state = (
                ClimateActivityState.COOLING
                if request.url.params["action"] == "START"
                else ClimateActivityState.STANDBY
            )
            self.states[vin]["state"]["climateControlState"]["activity"] = new_state

        elif service in ["start-charging", "stop-charging"]:
            new_state = ChargingState.PLUGGED_IN if "stop" in service else ChargingState.CHARGING
            self.states[vin]["state"]["electricChargingState"]["chargingStatus"] = new_state

        elif service in ["vehicle-finder"]:
            # nothing to do here as this is handled by the
            # return of REMOTE_SERVICE_RESPONSE_EVENTPOSITION
            pass

        json_data = load_response(REMOTE_SERVICE_RESPONSE_INITIATED)
        json_data["eventId"] = str(uuid4())

        return httpx.Response(200, json=json_data)

    def charging_settings_sideeffect(self, request: httpx.Request, vin: str) -> httpx.Response:
        """Check if payload is a valid charging settings payload and return evendId."""
        cs = ChargingSettings(**json.loads(request.content))

        # this endpoint allows fields to be omitted, so we have to check for that
        if cs.chargingTarget:
            self.states[vin]["state"]["electricChargingState"]["chargingTarget"] = cs.chargingTarget
        if cs.acLimitValue:
            self.states[vin]["state"]["chargingProfile"]["chargingSettings"]["acCurrentLimit"] = cs.acLimitValue

        return self.service_trigger_sideeffect(request, vin)

    def charging_profile_sideeffect(self, request: httpx.Request, vin: str) -> httpx.Response:
        """Check if payload is a valid charging settings payload and return evendId."""

        data = json.loads(request.content)

        if {"chargingMode", "departureTimer", "isPreconditionForDepartureActive", "servicePack"} != set(data):
            return httpx.Response(500)
        if (
            data["chargingMode"]["chargingPreference"] == "NO_PRESELECTION"
            and data["chargingMode"]["type"] != "CHARGING_IMMEDIATELY"
        ):
            return httpx.Response(500)
        if (
            data["chargingMode"]["chargingPreference"] == "CHARGING_WINDOW"
            and data["chargingMode"]["type"] != "TIME_SLOT"
        ):
            return httpx.Response(500)

        if not isinstance(data["isPreconditionForDepartureActive"], bool):
            return httpx.Response(500)

        # this endpoint does not allow fields to be omitted, so we can assume that they are always present

        # separate charging profile endpoint
        self.charging_settings[vin]["chargeAndClimateTimerDetail"]["chargingMode"]["chargingPreference"] = data[
            "chargingMode"
        ]["chargingPreference"]
        self.charging_settings[vin]["chargeAndClimateTimerDetail"]["chargingMode"]["type"] = data["chargingMode"][
            "type"
        ]
        self.charging_settings[vin]["chargeAndClimateTimerDetail"]["isPreconditionForDepartureActive"] = data[
            "isPreconditionForDepartureActive"
        ]

        # state endpoint
        self.states[vin]["state"]["chargingProfile"]["chargingPreference"] = data["chargingMode"]["chargingPreference"]
        self.states[vin]["state"]["chargingProfile"]["chargingMode"] = MAP_REMOTE_SERVICE_CHARGING_MODE_TO_STATE[
            data["chargingMode"]["type"]
        ]
        self.states[vin]["state"]["chargingProfile"]["climatisationOn"] = data["isPreconditionForDepartureActive"]

        return self.service_trigger_sideeffect(request, vin)

    @staticmethod
    def service_status_sideeffect(request: httpx.Request) -> httpx.Response:
        """Return all 3 eventStatus responses per function."""
        response_data = STATUSREMOTE_SERVICE_RESPONSE_DICT[request.url.params["eventId"]].pop(0)
        return httpx.Response(200, json=load_response(response_data))

    @staticmethod
    def poi_sideeffect(request: httpx.Request) -> httpx.Response:
        """Check if payload is a valid POI."""
        data = json.loads(request.content)
        tests = all(
            [
                len(data["vin"]) == 17,
                isinstance(data["location"]["coordinates"]["latitude"], float),
                isinstance(data["location"]["coordinates"]["longitude"], float),
                len(data["location"]["name"]) > 0,
            ]
        )
        if not tests:
            return httpx.Response(400)
        return httpx.Response(201)
