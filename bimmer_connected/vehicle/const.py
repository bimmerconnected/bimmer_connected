"""Vehicle-wide constants used by multiple data models."""

from bimmer_connected.models import StrEnum


class DriveTrainType(StrEnum):
    """Different types of drive trains."""

    COMBUSTION = "COMBUSTION"
    PLUGIN_HYBRID = "PLUGIN_HYBRID"  # PHEV
    ELECTRIC = "ELECTRIC"
    ELECTRIC_WITH_RANGE_EXTENDER = "ELECTRIC_WITH_RANGE_EXTENDER"
    HYBRID = "HYBRID"  # mild hybrids (MyBMW API v1)
    MILD_HYBRID = "MILD_HYBRID"  # mild hybrids (MyBMW API v2)
    UNKNOWN = "UNKNOWN"


#: Set of drive trains that have a combustion engine
COMBUSTION_ENGINE_DRIVE_TRAINS = {
    DriveTrainType.COMBUSTION,
    DriveTrainType.ELECTRIC_WITH_RANGE_EXTENDER,
    DriveTrainType.PLUGIN_HYBRID,
    DriveTrainType.HYBRID,
    DriveTrainType.MILD_HYBRID,
}

#: set of drive trains that have a high voltage battery
HV_BATTERY_DRIVE_TRAINS = {
    DriveTrainType.PLUGIN_HYBRID,
    DriveTrainType.ELECTRIC,
    DriveTrainType.ELECTRIC_WITH_RANGE_EXTENDER,
}
