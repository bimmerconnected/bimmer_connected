"""Models the state of a vehicle."""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List

from bimmer_connected.vehicle.models import StrEnum, VehicleDataBase

_LOGGER = logging.getLogger(__name__)


class LidState(StrEnum):
    """Possible states of the hatch, trunk, doors, windows, sun roof."""

    CLOSED = "CLOSED"
    OPEN = "OPEN"
    OPEN_TILT = "OPEN_TILT"
    INTERMEDIATE = "INTERMEDIATE"
    INVALID = "INVALID"
    UNKNOWN = "UNKNOWN"


class LockState(StrEnum):
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
    """Get state of the door locks."""

    convertible_top: LidState = LidState.UNKNOWN
    """Get state of the convertible roof."""

    lids: List[Lid] = field(default_factory=list)
    """All lids (doors+hood+trunk) of the car."""

    windows: List[Window] = field(default_factory=list)
    """All windows (doors+sunroof) of the car."""

    @classmethod
    def _parse_vehicle_data(cls, vehicle_data: Dict) -> Dict:
        """Parse doors and windows."""
        retval: Dict[str, Any] = {}

        if "properties" not in vehicle_data or "doorsAndWindows" not in vehicle_data["status"]:
            _LOGGER.error("Unable to read data from `properties.doorsAndWindows`.")
            return retval

        doors_and_windows = vehicle_data["properties"]["doorsAndWindows"]

        retval["lids"] = [
            Lid(k, v) for k, v in doors_and_windows.items() if k in ["hood", "trunk"] and v != LidState.INVALID
        ] + [Lid(k, v) for k, v in doors_and_windows["doors"].items() if v != LidState.INVALID]

        retval["windows"] = [Window(k, v) for k, v in doors_and_windows["windows"].items() if v != LidState.INVALID]
        if "moonroof" in doors_and_windows:
            retval["windows"].append(Window("moonroof", doors_and_windows["moonroof"]))

        if "convertibleTop" in doors_and_windows:
            retval["convertible_top"] = LidState(doors_and_windows["convertibleTop"])

        retval["door_lock_state"] = LockState(vehicle_data["status"]["doorsGeneralState"].upper())

        return retval

    @property
    def open_lids(self) -> List[Lid]:
        """Get all open lids of the car."""
        return [lid for lid in self.lids if not lid.is_closed]

    @property
    def all_lids_closed(self) -> bool:
        """Check if all lids are closed."""
        return len(self.open_lids) == 0

    @property
    def open_windows(self) -> List[Window]:
        """Get all open windows of the car."""
        return [lid for lid in self.windows if not lid.is_closed]

    @property
    def all_windows_closed(self) -> bool:
        """Check if all windows are closed."""
        return len(self.open_windows) == 0
