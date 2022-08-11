"""Models the state of a vehicle."""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List

from bimmer_connected.const import ATTR_STATE
from bimmer_connected.models import StrEnum, VehicleDataBase
from bimmer_connected.utils import to_camel_case

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
    PARTIALLY_LOCKED = "PARTIALLY_LOCKED"
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

    lids: List[Lid] = field(default_factory=list)
    """All lids (doors+hood+trunk) of the car."""

    windows: List[Window] = field(default_factory=list)
    """All windows (doors+sunroof) of the car."""

    @classmethod
    def _parse_vehicle_data(cls, vehicle_data: Dict) -> Dict:
        """Parse doors and windows."""
        retval: Dict[str, Any] = {}

        if ATTR_STATE in vehicle_data:
            if "doorsState" in vehicle_data[ATTR_STATE]:
                retval["lids"] = [
                    Lid(k, v)
                    for k, v in vehicle_data[ATTR_STATE]["doorsState"].items()
                    if k not in ["combinedState", "combinedSecurityState"] and v != LidState.INVALID
                ]
                retval["door_lock_state"] = LockState(
                    vehicle_data[ATTR_STATE]["doorsState"].get("combinedSecurityState", "UNKNOWN")
                )

            if "windowsState" in vehicle_data[ATTR_STATE]:
                retval["windows"] = [
                    Window(k, v)
                    for k, v in vehicle_data[ATTR_STATE]["windowsState"].items()
                    if k not in ["combinedState"] and v != LidState.INVALID
                ]

            if "roofState" in vehicle_data[ATTR_STATE]:
                retval["lids"].append(
                    Lid(
                        to_camel_case(vehicle_data[ATTR_STATE]["roofState"]["roofStateType"]),
                        vehicle_data[ATTR_STATE]["roofState"]["roofState"],
                    )
                )

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
