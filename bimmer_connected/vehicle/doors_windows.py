"""Models the state of a vehicle."""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List

from bimmer_connected.vehicle.models import VehicleDataBase

_LOGGER = logging.getLogger(__name__)


class LidState(str, Enum):
    """Possible states of the hatch, trunk, doors, windows, sun roof."""

    CLOSED = "CLOSED"
    OPEN = "OPEN"
    OPEN_TILT = "OPEN_TILT"
    INTERMEDIATE = "INTERMEDIATE"
    INVALID = "INVALID"


class LockState(str, Enum):
    """Possible states of the door locks."""

    LOCKED = "LOCKED"
    SECURED = "SECURED"
    SELECTIVE_LOCKED = "SELECTIVE_LOCKED"
    UNLOCKED = "UNLOCKED"
    UNKNOWN = "UNKNOWN"


class Lid:  # pylint: disable=too-few-public-methods
    """A lid of the vehicle.

    Lids are: Doors + Trunk + Hatch
    """

    def __init__(self, name: str, state: str):
        #: name of the lid
        self.name = name
        self.state = LidState(state)

    @property
    def is_closed(self) -> bool:
        """Check if the lid is closed."""
        return self.state == LidState.CLOSED


class Window(Lid):  # pylint: disable=too-few-public-methods,no-member
    """A window of the vehicle.

    A window can be a normal window of the car or the sun roof.
    """


@dataclass
class DoorsAndWindows(VehicleDataBase):  # pylint:disable=too-many-instance-attributes
    """Provides an accessible version of `properties.doorsAndWindows`."""

    door_lock_state: LockState = LockState.UNKNOWN

    lids: List[Lid] = field(default_factory=list)
    """All lids (doors+hood+trunk) of the car."""

    windows: List[Window] = field(default_factory=list)
    """All windows (doors+sunroof) of the car."""

    @classmethod
    def _parse_vehicle_data(cls, vehicle_data: List[Dict]) -> Dict:
        """Parse doors and windows."""
        if "properties" not in vehicle_data or "doorsAndWindows" not in vehicle_data["status"]:
            _LOGGER.error("Unable to read data from `properties.doorsAndWindows`.")
            return None

        retval = {}
        doors_and_windows = vehicle_data["properties"]["doorsAndWindows"]

        retval["lids"] = [
            Lid(k, v) for k, v in doors_and_windows.items() if k in ["hood", "trunk"] and v != LidState.INVALID
        ] + [Lid(k, v) for k, v in doors_and_windows["doors"].items() if v != LidState.INVALID]

        retval["windows"] = [Window(k, v) for k, v in doors_and_windows["windows"].items() if v != LidState.INVALID]
        if "moonroof" in doors_and_windows:
            retval["windows"].append(Window("moonroof", doors_and_windows["moonroof"]))

        retval["door_lock_state"] = LockState(vehicle_data["status"]["doorsGeneralState"].upper())

        return retval
