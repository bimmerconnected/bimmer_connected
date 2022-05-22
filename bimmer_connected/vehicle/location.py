"""Generals models used for bimmer_connected."""

import datetime
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from bimmer_connected.const import Regions
from bimmer_connected.coord_convert import gcj2wgs
from bimmer_connected.utils import parse_datetime
from bimmer_connected.vehicle.models import GPSPosition, VehicleDataBase

_LOGGER = logging.getLogger(__name__)


@dataclass
class VehicleLocation(VehicleDataBase):
    """The current position of a vehicle."""

    location: GPSPosition = GPSPosition(None, None)
    """The last known position of the vehicle."""

    heading: Optional[int] = None
    """The last known heading/direction of the vehicle."""

    vehicle_update_timestamp: Optional[datetime.datetime] = None
    account_region: Optional[Regions] = None
    remote_service_position: Optional[Dict] = None

    # pylint:disable=arguments-differ
    @classmethod
    def from_vehicle_data(cls, vehicle_data: Dict):
        """Creates the class based on vehicle data from API."""
        parsed = cls._parse_vehicle_data(vehicle_data) or {}
        if len(parsed) > 1:  # must be greater than 1 due to timestamp dummy
            return cls(**parsed)
        return None

    @classmethod
    def _parse_vehicle_data(cls, vehicle_data: Dict):
        date_dummy = datetime.datetime(1970, 1, 1)

        retval: Dict[str, Any] = {}
        retval["vehicle_update_timestamp"] = max(
            parse_datetime(vehicle_data.get("properties", {}).get("lastUpdatedAt")) or date_dummy,
            parse_datetime(vehicle_data.get("status", {}).get("lastUpdatedAt")) or date_dummy,
        )
        if "properties" in vehicle_data and "vehicleLocation" in vehicle_data["properties"]:
            location = vehicle_data["properties"]["vehicleLocation"]
            retval["location"] = GPSPosition(location["coordinates"]["latitude"], location["coordinates"]["longitude"])
            retval["heading"] = location["heading"]
        return retval

    def _update_after_parse(self, parsed: Dict) -> Dict:
        """Updates parsed vehicle data with attributes stored in class if needed."""
        retval = parsed
        # Overwrite vehicle data with remote service position if available & newer
        if self.remote_service_position is not None:
            t_remote = self.remote_service_position.get("timestamp", datetime.datetime(1900, 1, 1))
            if t_remote > self.vehicle_update_timestamp:
                retval["location"] = GPSPosition(
                    self.remote_service_position["latitude"], self.remote_service_position["longitude"]
                )
                retval["heading"] = self.remote_service_position["heading"]

        # Convert GCJ02 to WGS84 for positions in China
        if self.account_region == Regions.CHINA and "location" in retval and retval["location"].latitude is not None:
            gcj_lon, gcj_lat = gcj2wgs(gcjLon=retval["location"].longitude, gcjLat=retval["location"].latitude)
            retval["location"] = GPSPosition(gcj_lat, gcj_lon)
        return retval

    def set_remote_service_position(self, remote_service_dict: Dict):
        """Store remote service position returned from vehicle finder service."""
        if remote_service_dict.get("errorDetails"):
            error = remote_service_dict["errorDetails"]
            _LOGGER.error("Error retrieving vehicle position. %s: %s", error["title"], error["description"])
        else:
            pos = remote_service_dict["positionData"]["position"]
            pos["timestamp"] = datetime.datetime.utcnow()

            self.remote_service_position = pos

            self.__dict__.update(self._update_after_parse({}))
