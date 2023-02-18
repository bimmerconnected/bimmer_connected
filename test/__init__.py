"""Mock for Connected Drive Backend."""

import json
from pathlib import Path
from typing import Any, Dict, List, Union

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
VIN_G23 = "WBA00000000DEMO02"
VIN_G70 = "WBA00000000DEMO05"
VIN_I01_NOREX = "WBY000000NOREXI01"
VIN_I01_REX = "WBY00000000REXI01"
VIN_I20 = "WBA00000000DEMO01"

ALL_FINGERPRINTS: Dict[str, List[Dict]] = {brand.value: [] for brand in CarBrands}
ALL_STATES: Dict[str, Dict] = {}
ALL_CHARGING_SETTINGS: Dict[str, Dict] = {}


def get_fingerprint_count() -> int:
    """Return number of loaded vehicles."""
    return sum([len(vehicles) for vehicles in ALL_FINGERPRINTS.values()])


def load_response(path: Union[Path, str]) -> Any:
    """Load a stored response."""
    with open(path, "rb") as file:
        if Path(path).suffix == ".json":
            return json.load(file)
        return file.read().decode("UTF-8")


for fingerprint in RESPONSE_DIR.rglob("eadrax-vcs_v4_vehicles.json"):
    for vehicle in load_response(fingerprint):
        brand: str = vehicle["attributes"]["brand"]
        brand = "bmw" if brand == "BMW_I" else brand.lower()
        ALL_FINGERPRINTS[brand].append(vehicle)

for state in RESPONSE_DIR.rglob("eadrax-vcs_v4_vehicles_state_*.json"):
    ALL_STATES[state.stem.split("_")[-1]] = load_response(state)

for charging_setting in RESPONSE_DIR.rglob("eadrax-crccs_v2_vehicles_*.json"):
    ALL_CHARGING_SETTINGS[charging_setting.stem.split("_")[-1]] = load_response(charging_setting)


def get_deprecation_warning_count(caplog):
    """Return all logged DeprecationWarnings."""
    return [r for r in caplog.records if r.levelname == "WARNING" and "DeprecationWarning" in r.message]
