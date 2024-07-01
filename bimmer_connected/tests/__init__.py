"""Mock for Connected Drive Backend."""

import json
from pathlib import Path
from typing import Any, Dict, Union

from bimmer_connected.api.regions import Regions
from bimmer_connected.const import CarBrands

RESPONSE_DIR = Path(__file__).parent / "responses"

TEST_USERNAME = "some_user"
TEST_PASSWORD = "my_secret"
TEST_REGION = Regions.REST_OF_WORLD
TEST_REGION_STRING = "rest_of_world"

VIN_F31 = "WBA00000000000F31"
VIN_G01 = "WBA00000000DEMO04"
VIN_G20 = "WBA00000000DEMO03"
VIN_G26 = "WBA00000000DEMO02"
VIN_G70 = "WBA00000000DEMO05"
VIN_I01_NOREX = "WBY000000NOREXI01"
VIN_I01_REX = "WBY00000000REXI01"
VIN_I20 = "WBA00000000DEMO01"
VIN_J29 = "WZ100000000000J29"

ALL_VEHICLES: Dict[str, Dict] = {brand.value: {} for brand in CarBrands}
ALL_PROFILES: Dict[str, Dict] = {}
ALL_STATES: Dict[str, Dict] = {}
ALL_CHARGING_SETTINGS: Dict[str, Dict] = {}

REMOTE_SERVICE_RESPONSE_INITIATED = RESPONSE_DIR / "remote_services" / "eadrax_service_initiated.json"
REMOTE_SERVICE_RESPONSE_PENDING = RESPONSE_DIR / "remote_services" / "eadrax_service_pending.json"
REMOTE_SERVICE_RESPONSE_DELIVERED = RESPONSE_DIR / "remote_services" / "eadrax_service_delivered.json"
REMOTE_SERVICE_RESPONSE_EXECUTED = RESPONSE_DIR / "remote_services" / "eadrax_service_executed.json"
REMOTE_SERVICE_RESPONSE_ERROR = RESPONSE_DIR / "remote_services" / "eadrax_service_error.json"
REMOTE_SERVICE_RESPONSE_EVENTPOSITION = RESPONSE_DIR / "remote_services" / "eadrax_service_eventposition.json"


def get_fingerprint_count(type: str) -> int:
    """Return number of requests/fingerprints for a given type."""

    if type == "vehicles":
        return len(CarBrands)
    if type == "states":
        return len(ALL_STATES)
    if type == "profiles":
        return len(ALL_PROFILES)
    if type == "charging_settings":
        return len(ALL_CHARGING_SETTINGS)
    return 0


def load_response(path: Union[Path, str]) -> Any:
    """Load a stored response."""
    with open(path, "rb") as file:
        if Path(path).suffix == ".json":
            return json.load(file)
        return file.read().decode("UTF-8")


for fingerprint in RESPONSE_DIR.rglob("*-eadrax-vcs_v5_vehicle-list.json"):
    brand = fingerprint.stem.split("-")[0]
    response = load_response(fingerprint)

    if ALL_VEHICLES[brand].get("mappingInfos"):
        ALL_VEHICLES[brand]["mappingInfos"].extend(response["mappingInfos"])
    else:
        ALL_VEHICLES[brand] = response

for profile in RESPONSE_DIR.rglob("*-eadrax-vcs_v5_vehicle-data_profile_*.json"):
    ALL_PROFILES[profile.stem.split("_")[-1]] = load_response(profile)

for state in RESPONSE_DIR.rglob("*-eadrax-vcs_v4_vehicles_state_*.json"):
    ALL_STATES[state.stem.split("_")[-1]] = load_response(state)

for charging_setting in RESPONSE_DIR.rglob("*-eadrax-crccs_v2_vehicles_*.json"):
    ALL_CHARGING_SETTINGS[charging_setting.stem.split("_")[-1]] = load_response(charging_setting)


def get_deprecation_warning_count(caplog):
    """Return all logged DeprecationWarnings."""
    return [r for r in caplog.records if r.levelname == "WARNING" and "DeprecationWarning" in r.message]
