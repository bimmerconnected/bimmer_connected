"""Mock for Connected Drive Backend."""

import json
from pathlib import Path
from typing import Any, Dict, List, Union

from bimmer_connected.api.regions import Regions

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

ALL_FINGERPRINTS: Dict[str, List[Dict]] = {}
ALL_STATES: Dict[str, Dict] = {}


def get_fingerprint_count() -> int:
    """Return number of loaded vehicles."""
    return len(*ALL_FINGERPRINTS.values())


def load_response(path: Union[Path, str]) -> Any:
    """Load a stored response."""
    with open(path, "rb") as file:
        if Path(path).suffix == ".json":
            return json.load(file)
        return file.read().decode("UTF-8")


for fingerprint in RESPONSE_DIR.rglob("vehicles_v2_*.json"):
    brand = fingerprint.stem.split("_")[-2]
    if brand not in ALL_FINGERPRINTS:
        ALL_FINGERPRINTS[brand] = []
    ALL_FINGERPRINTS[brand].extend(load_response(fingerprint))

for state in RESPONSE_DIR.rglob("state_*.json"):
    ALL_STATES[state.stem.split("_")[-2]] = load_response(state)


def get_deprecation_warning_count(caplog):
    """Return all logged DeprecationWarnings."""
    return [r for r in caplog.records if r.levelname == "WARNING" and "DeprecationWarning" in r.message]
