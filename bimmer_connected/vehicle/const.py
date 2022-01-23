"""Constants and Enums regarding a vehicle."""

from .models import StrEnum


class ChargingState(StrEnum):
    """Charging state of electric vehicle."""
    DEFAULT = 'DEFAULT'
    CHARGING = 'CHARGING'
    ERROR = 'ERROR'
    COMPLETE = 'COMPLETE'
    FULLY_CHARGED = 'FULLY_CHARGED'
    FINISHED_FULLY_CHARGED = 'FINISHED_FULLY_CHARGED'
    FINISHED_NOT_FULL = 'FINISHED_NOT_FULL'
    INVALID = 'INVALID'
    NOT_CHARGING = 'NOT_CHARGING'
    PLUGGED_IN = 'PLUGGED_IN'
    WAITING_FOR_CHARGING = 'WAITING_FOR_CHARGING'
